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

from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.contentbundle import ContentBundle
from sugar3.bundle.bundleversion import NormalizedVersion
from jarabe.journal.journalentrybundle import JournalEntryBundle
from sugar3.bundle.bundle import MalformedBundleException, \
    AlreadyInstalledException, RegistrationException
from sugar3 import env

from jarabe.model import mimeregistry


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
            monitor = directory.monitor_directory( \
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
            self.add_bundle(one_file.get_path(), install_mime_type=True)
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
                self._add_bundle(folder)
            except:
                # pylint: disable=W0702
                logging.exception('Error while processing installed activity'
                                  ' bundle %s:', folder)

    def add_bundle(self, bundle_path, install_mime_type=False):
        bundle = self._add_bundle(bundle_path, install_mime_type)
        if bundle is not None:
            self._set_bundle_favorite(bundle.get_bundle_id(),
                                      bundle.get_activity_version(),
                                      True)
            self.emit('bundle-added', bundle)
            return True
        else:
            return False

    def _add_bundle(self, bundle_path, install_mime_type=False):
        logging.debug('STARTUP: Adding bundle %r', bundle_path)
        try:
            bundle = ActivityBundle(bundle_path)
            if install_mime_type:
                bundle.install_mime_type(bundle_path)
        except MalformedBundleException:
            logging.exception('Error loading bundle %r', bundle_path)
            return None

        bundle_id = bundle.get_bundle_id()
        installed = self.get_bundle(bundle_id)

        if installed is not None:
            if NormalizedVersion(installed.get_activity_version()) >= \
                    NormalizedVersion(bundle.get_activity_version()):
                logging.debug('Skip old version for %s', bundle_id)
                return None
            else:
                logging.debug('Upgrade %s', bundle_id)
                self.remove_bundle(installed.get_path())

        self._bundles.append(bundle)
        return bundle

    def remove_bundle(self, bundle_path):
        for bundle in self._bundles:
            if bundle.get_path() == bundle_path:
                self._bundles.remove(bundle)
                self.emit('bundle-removed', bundle)
                return True
        return False

    def get_activities_for_type(self, mime_type):
        result = []

        mime = mimeregistry.get_registry()
        default_bundle_id = mime.get_default_activity(mime_type)
        default_bundle = None

        for bundle in self._bundles:
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
        raise ValueError('No bundle %r with version %r exists.' % \
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
        # TODO treat ContentBundle in special way
        # needs rethinking while fixing ContentBundle support
        if isinstance(bundle, ContentBundle) or \
                isinstance(bundle, JournalEntryBundle):
            return bundle.is_installed()

        for installed_bundle in self._bundles:
            if bundle.get_bundle_id() == installed_bundle.get_bundle_id() and \
                    NormalizedVersion(bundle.get_activity_version()) == \
                    NormalizedVersion(installed_bundle.get_activity_version()):
                return True
        return False

    def install(self, bundle, uid=None, force_downgrade=False):
        for installed_bundle in self._bundles:
            if bundle.get_bundle_id() == installed_bundle.get_bundle_id() and \
                    NormalizedVersion(bundle.get_activity_version()) <= \
                    NormalizedVersion(installed_bundle.get_activity_version()):
                if not force_downgrade:
                    raise AlreadyInstalledException
                else:
                    self.uninstall(installed_bundle, force=True)
            elif bundle.get_bundle_id() == installed_bundle.get_bundle_id():
                self.uninstall(installed_bundle, force=True)

        install_dir = env.get_user_activities_path()
        if isinstance(bundle, JournalEntryBundle):
            install_path = bundle.install(uid)
        elif isinstance(bundle, ContentBundle):
            install_path = bundle.install()
        else:
            install_path = bundle.install(install_dir)

        # TODO treat ContentBundle in special way
        # needs rethinking while fixing ContentBundle support
        if isinstance(bundle, ContentBundle) or \
                isinstance(bundle, JournalEntryBundle):
            pass
        elif not self.add_bundle(install_path):
            raise RegistrationException

    def uninstall(self, bundle, force=False, delete_profile=False):
        # TODO treat ContentBundle in special way
        # needs rethinking while fixing ContentBundle support
        if isinstance(bundle, ContentBundle) or \
                isinstance(bundle, JournalEntryBundle):
            if bundle.is_installed():
                bundle.uninstall()
            else:
                logging.warning('Not uninstalling, bundle is not installed')
            return

        act = self.get_bundle(bundle.get_bundle_id())
        if not force and \
                act.get_activity_version() != bundle.get_activity_version():
            logging.warning('Not uninstalling, different bundle present')
            return

        if not act.is_user_activity():
            logging.debug('Do not uninstall system activity')
            return

        install_path = act.get_path()

        bundle.uninstall(install_path, force, delete_profile)

        if not self.remove_bundle(install_path):
            raise RegistrationException

    def upgrade(self, bundle):
        act = self.get_bundle(bundle.get_bundle_id())
        if act is None:
            logging.warning('Activity not installed')
        elif act.get_activity_version() == bundle.get_activity_version():
            logging.debug('No upgrade needed, same version already installed.')
            return
        elif act.is_user_activity():
            try:
                self.uninstall(bundle, force=True)
            except Exception:
                logging.exception('Uninstall failed, still trying to install'
                                  ' newer bundle:')
        else:
            logging.warning('Unable to uninstall system activity, '
                            'installing upgraded version in user activities')

        self.install(bundle)


def get_registry():
    global _instance
    if not _instance:
        _instance = BundleRegistry()
    return _instance
