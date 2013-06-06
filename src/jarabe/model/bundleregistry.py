# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 Aleksey Lim
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import logging

from gi.repository import GConf
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio
import json

from sugar3.bundle import bundle_from_dir
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.bundleversion import NormalizedVersion
from sugar3.bundle.bundle import MalformedBundleException, \
    AlreadyInstalledException, RegistrationException
from sugar3 import env

from jarabe.model import mimeregistry

"""
The bundle registry is a database of sorts of the trackable bundles available
on the system. A trackable bundle is one with a fixed bundle ID and predictable
install path. Activity and Content bundles are trackable, Journal Entry bundles
are not.

API is also provided for install/upgrade/erase of all bundle types, trackable
or not. The reasoning for supporting these operations on all bundles (even
ones that we don't track is):
 1. We want to provide generic APIs such as "install my bundle" without
    having to worry what type of bundle it is.
 2. For bundles that are tracked in the registry, the "bundle upgrade"
    operation requires access to the registry in order to uninstall the
    old version which might be kept at a different location on disk.

The bundle registry also monitors certain areas of the filesystem so that
when new activities installed by external processes, they will be picked up
immediately by the shell.
"""

_instance = None


class BundleRegistry(GObject.GObject):
    """Tracks the available activity bundles"""

    __gsignals__ = {
        'bundle-added': (GObject.SignalFlags.RUN_FIRST, None,
                         ([GObject.TYPE_PYOBJECT])),
        'bundle-removed': (GObject.SignalFlags.RUN_FIRST, None,
                           ([GObject.TYPE_PYOBJECT])),
        'bundle-changed': (GObject.SignalFlags.RUN_FIRST, None,
                           ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self):
        logging.debug('STARTUP: Loading the bundle registry')
        GObject.GObject.__init__(self)

        self._mime_defaults = self._load_mime_defaults()

        self._bundles = []
        # hold a reference to the monitors so they don't get disposed
        self._gio_monitors = []

        dirs = [env.get_user_activities_path()]

        for data_dir in GLib.get_system_data_dirs():
            dirs.append(os.path.join(data_dir, "sugar", "activities"))

        for activity_dir in dirs:
            self._scan_directory(activity_dir)
            directory = Gio.File.new_for_path(activity_dir)
            monitor = directory.monitor_directory(
                flags=Gio.FileMonitorFlags.NONE, cancellable=None)
            monitor.connect('changed', self.__file_monitor_changed_cb)
            self._gio_monitors.append(monitor)

        self._last_defaults_mtime = -1
        self._favorite_bundles = {}

        client = GConf.Client.get_default()
        self._protected_activities = []

        # FIXME, gconf_client_get_list not introspectable #681433
        protected_activities = client.get(
            '/desktop/sugar/protected_activities')
        for gval in protected_activities.get_list():
            activity_id = gval.get_string()
            self._protected_activities.append(activity_id)

        if self._protected_activities is None:
            self._protected_activities = []

        try:
            self._load_favorites()
        except Exception:
            logging.exception('Error while loading favorite_activities.')

        self._merge_default_favorites()

    def __file_monitor_changed_cb(self, monitor, one_file, other_file,
                                  event_type):
        if not one_file.get_path().endswith('.activity'):
            return
        if event_type == Gio.FileMonitorEvent.CREATED:
            self.add_bundle(one_file.get_path(), set_favorite=True)
        elif event_type == Gio.FileMonitorEvent.DELETED:
            self.remove_bundle(one_file.get_path())

    def _load_mime_defaults(self):
        defaults = {}

        f = open(os.environ["SUGAR_MIME_DEFAULTS"], 'r')
        for line in f.readlines():
            line = line.strip()
            if line and not line.startswith('#'):
                mime = line[:line.find(' ')]
                handler = line[line.rfind(' ') + 1:]
                defaults[mime] = handler
        f.close()

        return defaults

    def _get_favorite_key(self, bundle_id, version):
        """We use a string as a composite key for the favorites dictionary
        because JSON doesn't support tuples and python won't accept a list
        as a dictionary key.
        """
        if ' ' in bundle_id:
            raise ValueError('bundle_id cannot contain spaces')
        return '%s %s' % (bundle_id, version)

    def _load_favorites(self):
        favorites_path = env.get_profile_path('favorite_activities')
        if os.path.exists(favorites_path):
            favorites_data = json.load(open(favorites_path))

            favorite_bundles = favorites_data['favorites']
            if not isinstance(favorite_bundles, dict):
                raise ValueError('Invalid format in %s.' % favorites_path)
            if favorite_bundles:
                first_key = favorite_bundles.keys()[0]
                if not isinstance(first_key, basestring):
                    raise ValueError('Invalid format in %s.' % favorites_path)

                first_value = favorite_bundles.values()[0]
                if first_value is not None and \
                   not isinstance(first_value, dict):
                    raise ValueError('Invalid format in %s.' % favorites_path)

            self._last_defaults_mtime = float(favorites_data['defaults-mtime'])
            self._favorite_bundles = favorite_bundles

    def _merge_default_favorites(self):
        default_activities = []
        defaults_path = os.environ["SUGAR_ACTIVITIES_DEFAULTS"]
        if os.path.exists(defaults_path):
            file_mtime = os.stat(defaults_path).st_mtime
            if file_mtime > self._last_defaults_mtime:
                f = open(defaults_path, 'r')
                for line in f.readlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        default_activities.append(line)
                f.close()
                self._last_defaults_mtime = file_mtime

        if not default_activities:
            return

        for bundle_id in default_activities:
            max_version = '0'
            for bundle in self._bundles:
                if bundle.get_bundle_id() == bundle_id and \
                        NormalizedVersion(max_version) < \
                        NormalizedVersion(bundle.get_activity_version()):
                    max_version = bundle.get_activity_version()

            key = self._get_favorite_key(bundle_id, max_version)
            if NormalizedVersion(max_version) > NormalizedVersion('0') and \
                    key not in self._favorite_bundles:
                self._favorite_bundles[key] = None

        logging.debug('After merging: %r', self._favorite_bundles)

        self._write_favorites_file()

    def get_bundle(self, bundle_id):
        """Returns an bundle given his service name"""
        for bundle in self._bundles:
            if bundle.get_bundle_id() == bundle_id:
                return bundle
        return None

    def __iter__(self):
        return self._bundles.__iter__()

    def __len__(self):
        return len(self._bundles)

    def _scan_directory(self, path):
        if not os.path.isdir(path):
            return

        # Sort by mtime to ensure a stable activity order
        bundles = {}
        for f in os.listdir(path):
            if not f.endswith('.activity'):
                continue
            try:
                bundle_dir = os.path.join(path, f)
                if os.path.isdir(bundle_dir):
                    bundles[bundle_dir] = os.stat(bundle_dir).st_mtime
            except Exception:
                logging.exception('Error while processing installed activity'
                                  ' bundle %s:', bundle_dir)

        bundle_dirs = bundles.keys()
        bundle_dirs.sort(lambda d1, d2: cmp(bundles[d1], bundles[d2]))
        for folder in bundle_dirs:
            try:
                self.add_bundle(folder, emit_signals=False)
            except:
                # pylint: disable=W0702
                logging.exception('Error while processing installed activity'
                                  ' bundle %s:', folder)

    def add_bundle(self, bundle_path, set_favorite=False, emit_signals=True):
        """
        Add a bundle to the registry.
        If the bundle is a duplicate with one already in the registry,
        the existing one from the registry is returned.
        Otherwise, the newly added bundle is returned on success, or None on
        failure.
        """
        try:
            bundle = bundle_from_dir(bundle_path)
        except MalformedBundleException:
            logging.exception('Error loading bundle %r', bundle_path)
            return None

        bundle_id = bundle.get_bundle_id()
        logging.debug('STARTUP: Adding bundle %s', bundle_id)
        installed = self.get_bundle(bundle_id)

        if installed is not None:
            if NormalizedVersion(installed.get_activity_version()) == \
                    NormalizedVersion(bundle.get_activity_version()):
                logging.debug("Bundle already known")
                return installed
            if NormalizedVersion(installed.get_activity_version()) >= \
                    NormalizedVersion(bundle.get_activity_version()):
                logging.debug('Skip old version for %s', bundle_id)
                return None
            else:
                logging.debug('Upgrade %s', bundle_id)
                self.remove_bundle(installed.get_path(), emit_signals)

        if set_favorite:
            self._set_bundle_favorite(bundle.get_bundle_id(),
                                      bundle.get_activity_version(),
                                      True)

        self._bundles.append(bundle)
        if emit_signals:
            self.emit('bundle-added', bundle)
        return bundle

    def remove_bundle(self, bundle_path, emit_signals=True):
        for bundle in self._bundles:
            if bundle.get_path() == bundle_path:
                self._bundles.remove(bundle)
                if emit_signals:
                    self.emit('bundle-removed', bundle)
                return True
        return False

    def get_activities_for_type(self, mime_type):
        result = []

        mime = mimeregistry.get_registry()
        default_bundle_id = mime.get_default_activity(mime_type)
        default_bundle = None

        for bundle in self._bundles:
            if not isinstance(bundle, ActivityBundle):
                continue
            if mime_type in (bundle.get_mime_types() or []):
                if bundle.get_bundle_id() == default_bundle_id:
                    default_bundle = bundle
                elif self.get_default_for_type(mime_type) == \
                        bundle.get_bundle_id():
                    result.insert(0, bundle)
                else:
                    result.append(bundle)

        if default_bundle is not None:
            result.insert(0, default_bundle)

        return result

    def get_default_for_type(self, mime_type):
        return self._mime_defaults.get(mime_type)

    def _find_bundle(self, bundle_id, version):
        for bundle in self._bundles:
            if bundle.get_bundle_id() == bundle_id and \
                    bundle.get_activity_version() == version:
                return bundle
        raise ValueError('No bundle %r with version %r exists.' %
                        (bundle_id, version))

    def set_bundle_favorite(self, bundle_id, version, favorite):
        changed = self._set_bundle_favorite(bundle_id, version, favorite)
        if changed:
            bundle = self._find_bundle(bundle_id, version)
            self.emit('bundle-changed', bundle)

    def _set_bundle_favorite(self, bundle_id, version, favorite):
        key = self._get_favorite_key(bundle_id, version)
        if favorite and not key in self._favorite_bundles:
            self._favorite_bundles[key] = None
        elif not favorite and key in self._favorite_bundles:
            del self._favorite_bundles[key]
        else:
            return False

        self._write_favorites_file()
        return True

    def is_bundle_favorite(self, bundle_id, version):
        key = self._get_favorite_key(bundle_id, version)
        return key in self._favorite_bundles

    def is_activity_protected(self, bundle_id):
        return bundle_id in self._protected_activities

    def set_bundle_position(self, bundle_id, version, x, y):
        key = self._get_favorite_key(bundle_id, version)
        if key not in self._favorite_bundles:
            raise ValueError('Bundle %s %s not favorite' %
                             (bundle_id, version))

        if self._favorite_bundles[key] is None:
            self._favorite_bundles[key] = {}
        if 'position' not in self._favorite_bundles[key] or \
                [x, y] != self._favorite_bundles[key]['position']:
            self._favorite_bundles[key]['position'] = [x, y]
        else:
            return

        self._write_favorites_file()
        bundle = self._find_bundle(bundle_id, version)
        self.emit('bundle-changed', bundle)

    def get_bundle_position(self, bundle_id, version):
        """Get the coordinates where the user wants the representation of this
        bundle to be displayed. Coordinates are relative to a 1000x1000 area.
        """
        key = self._get_favorite_key(bundle_id, version)
        if key not in self._favorite_bundles or \
                self._favorite_bundles[key] is None or \
                'position' not in self._favorite_bundles[key]:
            return (-1, -1)
        else:
            return tuple(self._favorite_bundles[key]['position'])

    def _write_favorites_file(self):
        path = env.get_profile_path('favorite_activities')
        favorites_data = {'defaults-mtime': self._last_defaults_mtime,
                          'favorites': self._favorite_bundles}
        json.dump(favorites_data, open(path, 'w'), indent=1)

    def is_installed(self, bundle):
        for installed_bundle in self._bundles:
            if bundle.get_bundle_id() == installed_bundle.get_bundle_id() and \
                    NormalizedVersion(bundle.get_activity_version()) == \
                    NormalizedVersion(installed_bundle.get_activity_version()):
                return True
        return False

    def install(self, bundle, force_downgrade=False):
        """
        Install a bundle, upgrading or optionally downgrading any existing
        version.

        If the same version of the bundle is already installed, this function
        returns False without doing anything. If the installation succeeded,
        True is returned.

        By default, downgrades will be refused (AlreadyInstalledException will
        be raised) but the force_downgrade flag can override that behaviour
        and cause the downgrade to happen.

        The bundle is installed in the user activity directory.
        System-installed activities cannot be upgraded/downgraded; in such
        case, the bundle will be installed as a duplicate in the user
        activity directory.

        RegistrationException is raised if the bundle cannot be registered
        after it is installed.
        """
        bundle_id = bundle.get_bundle_id()
        act = self.get_bundle(bundle_id)
        if act:
            # Same version already installed?
            if act.get_activity_version() == bundle.get_activity_version():
                logging.debug('No upgrade needed, same version already '
                              'installed.')
                return False

            # Would this new installation be a downgrade?
            if NormalizedVersion(bundle.get_activity_version()) <= \
                    NormalizedVersion(act.get_activity_version()) \
                    and not force_downgrade:
                raise AlreadyInstalledException

            # Uninstall the previous version, if we can
            if act.is_user_activity():
                try:
                    self.uninstall(act, force=True)
                except Exception:
                    logging.exception('Uninstall failed, still trying to '
                                      'install newer bundle:')
            else:
                logging.warning('Unable to uninstall system activity, '
                                'installing upgraded version in user '
                                'activities')

        install_path = bundle.install()
        if bundle_id is not None:
            if self.add_bundle(install_path, set_favorite=True) is None:
                raise RegistrationException
        return True

    def uninstall(self, bundle, force=False, delete_profile=False):
        """
        Uninstall a bundle.

        If a different version of bundle is found in the activity registry,
        this function does nothing unless force is True.

        If the bundle is not found in the activity registry at all,
        this function simply returns.
        """
        act = self.get_bundle(bundle.get_bundle_id())
        if not act:
            logging.debug("Bundle is not installed")
            return

        if not force and \
                act.get_activity_version() != bundle.get_activity_version():
            logging.warning('Not uninstalling, different bundle present')
            return

        if not act.is_user_activity():
            logging.debug('Do not uninstall system activity')
            return

        install_path = act.get_path()
        bundle.uninstall(force, delete_profile)
        self.remove_bundle(install_path)


def get_registry():
    global _instance
    if not _instance:
        _instance = BundleRegistry()
    return _instance
