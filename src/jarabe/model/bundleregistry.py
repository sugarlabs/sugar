# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 Aleksey Lim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
from threading import Thread, Lock

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gtk
import json

from sugar3.bundle.helpers import bundle_from_dir
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.bundleversion import NormalizedVersion
from sugar3.bundle.bundle import MalformedBundleException, \
    AlreadyInstalledException, RegistrationException
from sugar3 import env

from jarabe.model import desktop
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

_DEFAULT_VIEW = 0
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

        # Queue of bundles to be installed/upgraded
        self._install_queue = _InstallQueue(self)

        # Bundle installation happens in a separate thread, which needs
        # access to _bundles. Protect all _bundles access with a lock.
        self._lock = Lock()
        self._bundles = []

        # hold a reference to the monitors so they don't get disposed
        self._gio_monitors = []

        dirs = [env.get_user_activities_path(), env.get_user_library_path()]

        for data_dir in GLib.get_system_data_dirs():
            dirs.append(os.path.join(data_dir, "sugar", "activities"))

        for activity_dir in dirs:
            self._scan_directory(activity_dir)
            directory = Gio.File.new_for_path(activity_dir)
            monitor = directory.monitor_directory(
                flags=Gio.FileMonitorFlags.NONE, cancellable=None)
            monitor.connect('changed', self.__file_monitor_changed_cb)
            self._gio_monitors.append(monitor)

        self._favorite_bundles = []
        for i in range(desktop.get_number_of_views()):
            self._favorite_bundles.append({})

        settings = Gio.Settings('org.sugarlabs')
        self._protected_activities = settings.get_strv('protected-activities')

        try:
            self._load_favorites()
        except Exception:
            logging.exception('Error while loading favorite_activities.')

        self._hidden_activities = []
        self._load_hidden_activities()

        self._convert_old_favorites()
        self._scan_new_favorites()

        self._desktop_model = desktop.get_model()
        self._desktop_model.connect('desktop-view-icons-changed',
                                    self.__desktop_view_icons_changed_cb)

    def __desktop_view_icons_changed_cb(self, model):
        number_of_views = desktop.get_number_of_views()
        if len(self._favorite_bundles) < number_of_views:
            for i in range(number_of_views - len(self._favorite_bundles)):
                self._favorite_bundles.append({})
        try:
            self._load_favorites()
        except Exception:
            logging.exception('Error while loading favorite_activities.')

    def __file_monitor_changed_cb(self, monitor, one_file, other_file,
                                  event_type):
        if event_type == Gio.FileMonitorEvent.CREATED or \
           event_type == Gio.FileMonitorEvent.ATTRIBUTE_CHANGED:
            self.add_bundle(one_file.get_path(), set_favorite=True)
        elif event_type == Gio.FileMonitorEvent.DELETED:
            self.remove_bundle(one_file.get_path())
            for root in GLib.get_system_data_dirs():
                root = os.path.join(root, 'sugar', 'activities')

                try:
                    os.listdir(root)
                except OSError:
                    logging.debug('Can not find GLib system dir %s', root)
                    continue
                activity_dir = os.path.basename(one_file.get_path())
                try:
                    bundle = bundle_from_dir(os.path.join(root, activity_dir))
                except MalformedBundleException:
                    continue

                if bundle is not None:
                    path = bundle.get_path()
                    if path is not None:
                        self.add_bundle(path)

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
        for i in range(desktop.get_number_of_views()):
            # Special-case 0 for backward compatibility
            if i == 0:
                favorites_path = env.get_profile_path('favorite_activities')
            else:
                favorites_path = env.get_profile_path(
                    'favorite_activities_%d' % (i))
            if os.path.exists(favorites_path):
                favorites_data = json.load(open(favorites_path))

                favorite_bundles = favorites_data['favorites']
                if not isinstance(favorite_bundles, dict):
                    raise ValueError('Invalid format in %s.' % favorites_path)
                if favorite_bundles:
                    first_key = favorite_bundles.keys()[0]
                    if not isinstance(first_key, basestring):
                        raise ValueError('Invalid format in %s.' %
                                         favorites_path)

                    first_value = favorite_bundles.values()[0]
                    if first_value is not None and \
                       not isinstance(first_value, dict):
                        raise ValueError('Invalid format in %s.' %
                                         favorites_path)

                self._favorite_bundles[i] = favorite_bundles

    def _load_hidden_activities(self):
        path = os.environ.get('SUGAR_ACTIVITIES_HIDDEN', None)
        try:
            with open(path) as file:
                for line in file.readlines():
                    bundle_id = line.strip()
                    if bundle_id:
                        self._hidden_activities.append(bundle_id)
        except IOError:
            logging.error('Error when loading hidden activities %s', path)

    def _convert_old_favorites(self):
        for i in range(desktop.get_number_of_views()):
            for key in self._favorite_bundles[i].keys():
                data = self._favorite_bundles[i][key]
                if data is None:
                    data = {}
                if 'favorite' not in data:
                    data['favorite'] = True
                self._favorite_bundles[i][key] = data
            self._write_favorites_file(i)

    def _scan_new_favorites(self):
        for bundle in self:
            bundle_id = bundle.get_bundle_id()
            key = self._get_favorite_key(
                bundle_id, bundle.get_activity_version())
            if key not in self._favorite_bundles[_DEFAULT_VIEW]:
                self._favorite_bundles[_DEFAULT_VIEW][key] = \
                    {'favorite': bundle_id not in self._hidden_activities}
        self._write_favorites_file(_DEFAULT_VIEW)

    def get_bundle(self, bundle_id):
        """Returns an bundle given his service name"""
        with self._lock:
            for bundle in self._bundles:
                if bundle.get_bundle_id() == bundle_id:
                    return bundle
        return None

    def __iter__(self):
        with self._lock:
            copy = list(self._bundles)
        return copy.__iter__()

    def __len__(self):
        with self._lock:
            return len(self._bundles)

    def _scan_directory(self, path):
        if not os.path.isdir(path):
            return

        # Sort by mtime to ensure a stable activity order
        bundles = {}
        for f in os.listdir(path):
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

    def add_bundle(self, bundle_path, set_favorite=False, emit_signals=True,
                   force_downgrade=False):
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

        # None is a valid return value from bundle_from_dir helper.
        if bundle is None:
            logging.error('No bundle in %r', bundle_path)
            return None

        bundle_id = bundle.get_bundle_id()
        logging.debug('STARTUP: Adding bundle %s', bundle_id)
        installed = self.get_bundle(bundle_id)

        if installed is not None:
            if NormalizedVersion(installed.get_activity_version()) == \
                    NormalizedVersion(bundle.get_activity_version()):
                logging.debug("Bundle already known")
                return installed
            if not force_downgrade and \
                    NormalizedVersion(installed.get_activity_version()) >= \
                    NormalizedVersion(bundle.get_activity_version()):
                logging.debug('Skip old version for %s', bundle_id)
                return None
            else:
                logging.debug('Upgrade %s', bundle_id)
                self.remove_bundle(installed.get_path(), emit_signals)

        if set_favorite:
            favorite = not self.is_bundle_hidden(
                bundle.get_bundle_id(), bundle.get_activity_version())
            self._set_bundle_favorite(bundle.get_bundle_id(),
                                      bundle.get_activity_version(),
                                      favorite)

        with self._lock:
            self._bundles.append(bundle)
        if emit_signals:
            self.emit('bundle-added', bundle)
        return bundle

    def remove_bundle(self, bundle_path, emit_signals=True):
        removed = None
        self._lock.acquire()
        for bundle in self._bundles:
            if bundle.get_path() == bundle_path:
                self._bundles.remove(bundle)
                removed = bundle
                break
        self._lock.release()

        if emit_signals and removed is not None:
            self.emit('bundle-removed', removed)
        return removed is not None

    def get_activities_for_type(self, mime_type):
        result = []

        mime = mimeregistry.get_registry()
        default_bundle_id = mime.get_default_activity(mime_type)
        default_bundle = None

        for bundle in self:
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
        with self._lock:
            for bundle in self._bundles:
                if bundle.get_bundle_id() == bundle_id and \
                        bundle.get_activity_version() == version:
                    return bundle
        raise ValueError('No bundle %r with version %r exists.' %
                         (bundle_id, version))

    def set_bundle_favorite(self, bundle_id, version, favorite,
                            favorite_view=0):
        changed = self._set_bundle_favorite(bundle_id, version, favorite,
                                            favorite_view)
        if changed:
            bundle = self._find_bundle(bundle_id, version)
            self.emit('bundle-changed', bundle)

    def _set_bundle_favorite(self, bundle_id, version, favorite,
                             favorite_view=0):
        key = self._get_favorite_key(bundle_id, version)
        if key not in self._favorite_bundles[favorite_view]:
            self._favorite_bundles[favorite_view][key] = {}
        elif favorite == \
                self._favorite_bundles[favorite_view][key]['favorite']:
            return False
        self._favorite_bundles[favorite_view][key]['favorite'] = favorite
        self._write_favorites_file(favorite_view)
        return True

    def is_bundle_favorite(self, bundle_id, version, favorite_view=0):
        key = self._get_favorite_key(bundle_id, version)
        if key not in self._favorite_bundles[favorite_view]:
            return False
        return self._favorite_bundles[favorite_view][key]['favorite']

    def is_bundle_hidden(self, bundle_id, version):
        key = self._get_favorite_key(bundle_id, version)
        if key in self._favorite_bundles[_DEFAULT_VIEW]:
            data = self._favorite_bundles[_DEFAULT_VIEW][key]
            return data['favorite'] is False
        else:
            return bundle_id in self._hidden_activities

    def is_activity_protected(self, bundle_id):
        return bundle_id in self._protected_activities

    def set_bundle_position(self, bundle_id, version, x, y, favorite_view=0):
        key = self._get_favorite_key(bundle_id, version)
        if key not in self._favorite_bundles[favorite_view]:
            raise ValueError('Bundle %s %s not favorite' %
                             (bundle_id, version))

        if 'position' not in self._favorite_bundles[favorite_view][key] or \
                [x, y] != \
                self._favorite_bundles[favorite_view][key]['position']:
            self._favorite_bundles[favorite_view][key]['position'] = [x, y]
        else:
            return

        self._write_favorites_file(favorite_view)
        bundle = self._find_bundle(bundle_id, version)
        self.emit('bundle-changed', bundle)

    def get_bundle_position(self, bundle_id, version, favorite_view=0):
        """Get the coordinates where the user wants the representation of this
        bundle to be displayed. Coordinates are relative to a 1000x1000 area.
        """
        key = self._get_favorite_key(bundle_id, version)
        if key not in self._favorite_bundles[favorite_view] or \
                'position' not in self._favorite_bundles[favorite_view][key]:
            return (-1, -1)
        else:
            return \
                tuple(self._favorite_bundles[favorite_view][key]['position'])

    def _write_favorites_file(self, favorite_view):
        if favorite_view == 0:
            path = env.get_profile_path('favorite_activities')
        else:
            path = env.get_profile_path('favorite_activities_%d' %
                                        (favorite_view))
        favorites_data = {
            'favorites': self._favorite_bundles[favorite_view]}
        json.dump(favorites_data, open(path, 'w'), indent=1)

    def is_installed(self, bundle):
        for installed_bundle in self:
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
        result = [None]
        self.install_async(bundle, self._sync_install_cb, result,
                           force_downgrade)
        while result[0] is None:
            Gtk.main_iteration()

        if isinstance(result[0], Exception):
            raise result[0]
        return result[0]

    def _sync_install_cb(self, bundle, result, user_data):
        # Async callback for install()
        user_data[0] = result

    def install_async(self, bundle, callback, user_data,
                      force_downgrade=False):
        """
        Asynchronous version of install().
        The result of the installation is presented to a user-defined callback
        with the following parameters:
          1. The bundle that passed to this method
          2. The result of the operation (True, False, or an Exception -
             see the install() docs)
          3. The user_data passed to this method

        The callback is always invoked from main-loop context.
        """
        self._install_queue.enqueue(bundle, force_downgrade,
                                    self._bundle_installed_cb,
                                    [callback, user_data])

    def _bundle_installed_cb(self, bundle, result, data):
        """
        Completion handler for the bundle Install thread.
        Called in main loop context. Finishes registration and invokes user
        callback as necessary.
        """
        callback = data[0]
        user_data = data[1]

        # Installation didn't happen, or error?
        if isinstance(result, Exception) or result is False:
            callback(bundle, result, user_data)
            return

        if bundle.get_bundle_id() is not None:
            registered = self.add_bundle(result, set_favorite=True,
                                         force_downgrade=True)
            if registered is None:
                callback(bundle, RegistrationException(), user_data)
                return

        callback(bundle, True, user_data)

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

        alt_bundles = self.get_system_bundles(act.get_bundle_id())
        if alt_bundles:
            alt_bundles.sort(
                key=lambda b: NormalizedVersion(b.get_activity_version()))
            alt_bundles.reverse()
            new_bundle = alt_bundles[0]
            self.add_bundle(new_bundle.get_path())

    def get_system_bundles(self, bundle_id):
        """
        Searches for system bundles (eg. those in /usr/share/sugar/activities)
        with a given bundle id.

        Prams:
            * bundle_id (string):  the bundle id to look for

        Returns a list of ActivityBundle or ContentBundle objects, or an empty
        list if there are none found.
        """
        bundles = []
        for root in GLib.get_system_data_dirs():
            root = os.path.join(root, 'sugar', 'activities')

            try:
                dir_list = os.listdir(root)
            except OSError:
                logging.debug('Can not find GLib system dir %s', root)
                continue

            for activity_dir in dir_list:
                try:
                    bundle = bundle_from_dir(os.path.join(root, activity_dir))
                except MalformedBundleException:
                    continue

                if bundle.get_bundle_id() == bundle_id:
                    bundles.append(bundle)
        return bundles


class _InstallQueue(object):
    """
    A class to represent a queue of bundles to be installed, and to handle
    execution of each task in the queue. Only for internal bundleregistry use.

    The use of a queue means that we serialize all bundle upgrade processing.
    This is necessary to avoid many difficult corner-cases like: what happens
    if two users try to asynchronously and simultaenously install different
    version of the same bundle?

    We maintain at maximum one thread to do the actual bundle install. When
    done, the thread enqueues a callback in the main thread (via the GLib
    main loop).
    """

    def __init__(self, registry):
        self._lock = Lock()
        self._queue = []
        self._thread_running = False
        self._registry = registry

    def enqueue(self, bundle, force_downgrade, callback, user_data):
        task = _InstallTask(bundle, force_downgrade, callback, user_data)
        self._lock.acquire()
        self._queue.append(task)
        if not self._thread_running:
            self._thread_running = True
            Thread(target=self._thread_func).start()
        self._lock.release()

    def _thread_func(self):
        while True:
            self._lock.acquire()
            if len(self._queue) == 0:
                self._thread_running = False
                self._lock.release()
                return

            task = self._queue.pop()
            self._lock.release()

            self._do_work(task)

    def _do_work(self, task):
        bundle = task.bundle
        bundle_id = bundle.get_bundle_id()
        act = self._registry.get_bundle(bundle_id)
        logging.debug("InstallQueue task %s installed %r", bundle_id, act)

        if act:
            # Same version already installed?
            if act.get_activity_version() == bundle.get_activity_version():
                logging.debug('No upgrade needed, same version already '
                              'installed.')
                task.queue_callback(False)
                return

            # Would this new installation be a downgrade?
            if NormalizedVersion(bundle.get_activity_version()) <= \
                    NormalizedVersion(act.get_activity_version()) \
                    and not task.force_downgrade:
                task.queue_callback(AlreadyInstalledException())
                return

            # Uninstall the previous version, if we can
            if act.is_user_activity():
                try:
                    act.uninstall()
                except:
                    logging.exception('Uninstall failed, still trying to '
                                      'install newer bundle')
            else:
                logging.warning('Unable to uninstall system activity, '
                                'installing upgraded version in user '
                                'activities')

        try:
            task.queue_callback(bundle.install())
        except Exception as e:
            logging.debug("InstallThread install failed: %r", e)
            task.queue_callback(e)


class _InstallTask(object):
    """
    Simple class to represent a bundle installation/upgrade task.
    Only for use internal to InstallQueue.
    """

    def __init__(self, bundle, force_downgrade, callback, user_data):
        self.bundle = bundle
        self.callback = callback
        self.force_downgrade = force_downgrade
        self.user_data = user_data

    def queue_callback(self, result):
        GLib.idle_add(self.callback, self.bundle, result, self.user_data)


def get_registry():
    global _instance
    if not _instance:
        _instance = BundleRegistry()
    return _instance
