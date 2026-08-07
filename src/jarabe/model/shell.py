# Copyright (C) 2006-2007 Owen Williams.
# Copyright (C) 2006-2008 Red Hat, Inc.
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

import logging
import time

import gi
gi.require_version("Casilda", "1.0")

from gi.repository import Casilda
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
import dbus

from sugar4 import dispatch
from sugar4 import profile

from jarabe.model.bundleregistry import get_registry

_SERVICE_NAME = 'org.laptop.Activity'
_SERVICE_PATH = '/org/laptop/Activity'
_SERVICE_INTERFACE = 'org.laptop.Activity'

_model = None


class Activity(GObject.GObject):
    """Activity which appears in the "Home View" of the Sugar shell

    This class stores the Sugar Shell's metadata regarding a
    given activity/application in the system.  It interacts with
    the sugar3.activity.* modules extensively in order to
    accomplish its tasks.
    """

    __gtype_name__ = 'SugarHomeActivity'

    __gsignals__ = {
        'pause': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'resume': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'stop': (GObject.SignalFlags.RUN_LAST, GObject.TYPE_BOOLEAN, ([])),
    }

    LAUNCHING = 0
    LAUNCH_FAILED = 1
    LAUNCHED = 2

    def __init__(self, activity_info, activity_id, color, window=None):
        """Initialise the HomeActivity

        activity_info -- sugar3.activity.registry.ActivityInfo instance,
            provides the information required to actually
            create the new instance.  This is, in effect,
            the "type" of activity being created.
        activity_id -- unique identifier for this instance
            of the activity type
        _windows -- GtkWindows registered for the activity. The lowest
                    one in the stack is the main window.
        """
        super().__init__()

        self._windows = []
        self._service = None
        self._shell_windows = []
        self._activity_id = activity_id
        self._activity_info = activity_info
        self._launch_time = time.time()
        self._launch_status = Activity.LAUNCHING

        if color is not None:
            self._color = color
        else:
            self._color = profile.get_color()

        if window is not None:
            self.add_window(window)

        self._retrieve_service()

        self._name_owner_changed_handler = None
        bus = dbus.SessionBus()
        self._name_owner_changed_handler = bus.add_signal_receiver(
            self._name_owner_changed_cb,
            signal_name='NameOwnerChanged',
            dbus_interface='org.freedesktop.DBus')

        self._launch_completed_hid = \
            get_model().connect('launch-completed',
                                self.__launch_completed_cb)
        self._launch_failed_hid = get_model().connect('launch-failed',
                                                      self.__launch_failed_cb)

    def get_launch_status(self):
        return self._launch_status

    launch_status = GObject.Property(getter=get_launch_status)

    def add_window(self, window, is_main_window=False):
        """Add a window to the windows stack."""
        if not window:
            raise ValueError('window must be valid')
        self._windows.append(window)

        if is_main_window:
            window.connect('state-changed', self._state_changed_cb)

    def push_shell_window(self, window):
        """Attach a shell run window (eg. view source) to the activity."""
        self._shell_windows.append(window)

    def pop_shell_window(self, window):
        """
        Detach a shell run window (eg. view source) to the activity.
        Only call this on **user initiated** deletion (loop issue).
        """
        self._shell_windows.remove(window)

    def has_shell_window(self):
        return bool(self._shell_windows)

    def stop(self):
        # For web activities the Apisocket will connect to the 'stop'
        # signal, thus preventing the window close.  Then, on the
        # 'activity.close' method, it will call close_window()
        # directly.
        close_window = not self.emit('stop')
        if close_window:
            self.close_window()

    def close_window(self):
        window = self.get_window()
        if window is not None:
            window.close()

        for w in self._shell_windows:
            w.close()

    def remove_window(self, window):
        """Remove a window from the windows stack."""
        if window in self._windows:
            self._windows.remove(window)
            return True
        return False

    def get_service(self):
        """Get the activity service

        Note that non-native Sugar applications will not have
        such a service, so the return value will be None in
        those cases.
        """

        return self._service

    def get_title(self):
        """Retrieve the application's root window's suggested title"""
        if self._windows:
            return self._windows[0].get_title()
        return None

    def get_icon_path(self):
        """Retrieve the activity's icon (file) name"""
        if self.is_journal():
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            paintable = icon_theme.lookup_icon('activity-journal', None, 24, 1, Gtk.TextDirection.LTR, 0)
            if not paintable or not paintable.get_file():
                return None
            return paintable.get_file().get_path()
        if self._activity_info:
            return self._activity_info.get_icon()
        return None

    def get_icon_color(self):
        """Retrieve the appropriate icon colour for this activity

        Uses activity_id to index into the PresenceService's
        set of activity colours, if the PresenceService does not
        have an entry (implying that this is not a Sugar-shared application)
        uses the local user's profile colour for the icon.
        """
        return self._color

    def get_activity_id(self):
        """Retrieve the "activity_id" passed in to our constructor

        This is a "globally likely unique" identifier generated by
        sugar3.util.unique_id
        """
        return self._activity_id

    def get_bundle_id(self):
        """ Returns the activity's bundle id"""
        if self._activity_info is None:
            return None
        return self._activity_info.get_bundle_id()

    def has_bundle_id(self, bundle_id):
        """Check if a window with the given bundle id is in the windows stack"""
        if self._windows:
            for wnd in self._windows:
                data = wnd
                wid = getattr(data, 'bundle_id', None)
                if wid == bundle_id:
                    return True
        return False

    def get_window(self):
        """Retrieve the root window of this application

        This was stored by the add_window method, which was
        called by HomeModel._add_activity, which was called
        via a callback that looks for all 'window-added'
        events.

        We keep a stack of the windows. The lowest window in the
        stack that is still valid we consider the main one.

        HomeModel currently uses a dbus service query on the
        activity to determine to which HomeActivity the newly
        launched window belongs.
        """
        if self._windows:
            return self._windows[0]
        return None

    def get_type(self):
        """Retrieve the activity bundle id for future reference"""
        if not self._windows:
            return None
        data = self._windows[0]
        return getattr(data, 'bundle_id', None)

    def is_journal(self):
        """Returns boolean if the activity is of type JournalActivity"""
        if self.get_bundle_id() == 'org.laptop.JournalActivity':
            return True
        from jarabe.journal.journalactivity import JournalActivity
        if self._windows and isinstance(self._windows[0], JournalActivity):
            return True
        return False

    def get_launch_time(self):
        """Return the time at which the activity was first launched

        Format is floating-point time.time() value
        (seconds since the epoch)
        """
        return self._launch_time

    def get_pid(self):
        """Returns the activity's PID"""
        if not self._windows:
            return None
        if hasattr(self._windows[0], 'get_pid'):
            return self._windows[0].get_pid()
        return None

    def get_bundle_path(self):
        """Returns the activity's bundle directory"""
        if self._activity_info is None:
            return None
        return self._activity_info.get_path()

    def get_activity_name(self):
        """Returns the activity's bundle name"""
        if self._activity_info is None:
            return None
        return self._activity_info.get_name()

    def equals(self, activity):
        if self._activity_id and activity.get_activity_id():
            return self._activity_id == activity.get_activity_id()
        data = self._windows[0]
        bundle_id = getattr(data, 'bundle_id', None)
        if bundle_id and activity.get_bundle_id():
            return bundle_id == activity.get_bundle_id()
        return False

    def _get_service_name(self):
        if self._activity_id:
            return _SERVICE_NAME + self._activity_id
        return None

    def _retrieve_service(self):
        if not self._activity_id:
            return

        try:
            bus = dbus.SessionBus()
            proxy = bus.get_object(self._get_service_name(),
                                   _SERVICE_PATH + '/' + self._activity_id,
                                   introspect=False)
            self._service = dbus.Interface(proxy, _SERVICE_INTERFACE)
        except dbus.DBusException:
            self._service = None

    def _name_owner_changed_cb(self, name, old, new):
        if name == self._get_service_name():
            if old and not new:
                logging.debug('Activity._name_owner_changed_cb: '
                              'activity %s went away', name)
                self._name_owner_changed_handler.remove()
                self._name_owner_changed_handler = None
                self._service = None
                get_model()._remove_activity(self)
            elif not old and new:
                logging.debug('Activity._name_owner_changed_cb: '
                              'activity %s started up', name)
                self._retrieve_service()
                self.set_active(True)
                get_model().emit('launch-completed', self)

    def set_active(self, state):
        """Propagate the current state to the activity object"""
        if self._service is not None:
            self._service.SetActive(state,
                                    reply_handler=self._set_active_success,
                                    error_handler=self._set_active_error)

    def _set_active_success(self):
        pass

    def _set_active_error(self, err):
        logging.error('set_active() failed: %s', err)

    def _set_launch_status(self, value):
        get_model().disconnect(self._launch_completed_hid)
        get_model().disconnect(self._launch_failed_hid)
        self._launch_completed_hid = None
        self._launch_failed_hid = None
        self._launch_status = value
        self.notify('launch_status')

    def __launch_completed_cb(self, model, home_activity):
        if home_activity is self:
            self._set_launch_status(Activity.LAUNCHED)

    def __launch_failed_cb(self, model, home_activity):
        if home_activity is self:
            self._set_launch_status(Activity.LAUNCH_FAILED)

    def _state_changed_cb(self, main_window, *args):
        # Track minimized state
        surface = main_window.get_surface()
        if surface is not None:
            state = surface.get_state()
            if state & Gdk.ToplevelState.MINIMIZED:
                self.emit('pause')
            else:
                self.emit('resume')


class ShellModel(Gtk.Application):
    """Model of the Shell, the point of registration for all running activities.

    Traps 'window-added' / 'window-removed' events from Gtk.Application to
    track which activity windows are alive, and emits signals consumed by the
    home view and tray.  A Casilda Wayland compositor (self.compositor) is
    embedded as a child widget so activity processes render into the shell
    rather than as independent top-level windows.
    """
    __gsignals__ = {
        'activity-added': (GObject.SignalFlags.RUN_FIRST, None,
                           ([GObject.TYPE_PYOBJECT])),
        'activity-removed': (GObject.SignalFlags.RUN_FIRST, None,
                             ([GObject.TYPE_PYOBJECT])),
        'active-activity-changed': (GObject.SignalFlags.RUN_FIRST,
                                    None,
                                    ([GObject.TYPE_PYOBJECT])),
        'tabbing-activity-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     ([GObject.TYPE_PYOBJECT])),
        'launch-started': (GObject.SignalFlags.RUN_FIRST, None,
                           ([GObject.TYPE_PYOBJECT])),
        'launch-completed': (GObject.SignalFlags.RUN_FIRST, None,
                             ([GObject.TYPE_PYOBJECT])),
        'launch-failed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([GObject.TYPE_PYOBJECT])),
        'active-window-changed': (GObject.SignalFlags.RUN_LAST, None,
                          ([GObject.TYPE_PYOBJECT])),
    }

    ZOOM_MESH = 0
    ZOOM_GROUP = 1
    ZOOM_HOME = 2
    ZOOM_ACTIVITY = 3

    def __init__(self, application_id="org.laptop.Shell"):
        super().__init__(
            application_id=application_id,
            flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.set_default()

        self.stack = Gtk.Stack()
        self.stack.add_css_class('sugar-shell-stack')
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._main_window = None

        self.compositor = Casilda.Compositor(socket="wayland-sugar")

        self.connect('window-added', self._window_added_cb)
        self.connect('window-removed', self._window_removed_cb)
        self.connect('active-window-changed',
                     self._active_window_changed_cb)

        self.zoom_level_changed = dispatch.Signal()

        self._desktop_level = self.ZOOM_HOME
        self._zoom_level = self.ZOOM_HOME
        self._current_activity = None
        self._activities = []
        self._shared_activities = {}
        self._active_activity = None
        self._tabbing_activity = None
        self._launchers = {}
        self._modal_dialogs_counter = 0

        settings = Gio.Settings.new('org.sugarlabs')
        self._maximum_open_activities = settings.get_int(
            'maximum-number-of-open-activities')

        self._launch_timers = {}

        self.zoom_level_changed.connect(self._zoom_level_changed_cb)
        self.connect('active-activity-changed', self._active_activity_changed_cb)

    def add_window(self, window):
        super().add_window(window)

    def get_launcher(self, activity_id):
        return self._launchers.get(str(activity_id))

    def register_launcher(self, activity_id, launcher):
        self._launchers[activity_id] = launcher

    def unregister_launcher(self, activity_id):
        if activity_id in self._launchers:
            del self._launchers[activity_id]

    def _update_zoom_level(self, window):
        if isinstance(window, Gtk.Dialog):
            return
            
        if window == self._main_window:
            new_level = self._desktop_level
        else:
            new_level = self.ZOOM_ACTIVITY

        if self._zoom_level != new_level:
            old_level = self._zoom_level
            self._zoom_level = new_level
            self.zoom_level_changed.send(self, old_level=old_level,
                                         new_level=new_level)

    def set_zoom_level(self, new_level, x_event_time=0):
        old_level = self.zoom_level
        if old_level == new_level:
            return

        if new_level == self.ZOOM_ACTIVITY and self._active_activity is None:
            return

        self._zoom_level = new_level
        if new_level is not self.ZOOM_ACTIVITY:
            self._desktop_level = new_level

        self.zoom_level_changed.send(self, old_level=old_level,
                                     new_level=new_level)

        if new_level is self.ZOOM_ACTIVITY:
            if self._active_activity:
                window = self._active_activity.get_window()
                if window:
                    window.present()

    def _get_zoom_level(self):
        return self._zoom_level

    zoom_level = property(_get_zoom_level)

    def _zoom_level_changed_cb(self, signal=None, sender=None, **kwargs):
        new_level = kwargs.get('new_level')
        if new_level == self.ZOOM_ACTIVITY:
            active_activity = self.get_active_activity()
            if active_activity and active_activity.is_journal():
                self.stack.set_visible_child_name("journal")
            else:
                self.stack.set_visible_child_name("activity")
        else:
            self.stack.set_visible_child_name("home")

    def _active_activity_changed_cb(self, shell_model, activity):
        if self.zoom_level == self.ZOOM_ACTIVITY:
            if activity and activity.is_journal():
                self.stack.set_visible_child_name("journal")
            else:
                self.stack.set_visible_child_name("activity")

    def _get_activities_with_window(self):
        ret = []
        for i in self._activities:
            if i.get_window() is not None:
                ret.append(i)
        return ret

    def get_previous_activity(self, current=None):
        if not current:
            current = self._active_activity

        activities = self._get_activities_with_window()
        i = activities.index(current)
        if len(activities) == 0:
            return None
        if i - 1 >= 0:
            return activities[i - 1]
        return activities[len(activities) - 1]

    def get_next_activity(self, current=None):
        if not current:
            current = self._active_activity

        activities = self._get_activities_with_window()
        i = activities.index(current)
        if len(activities) == 0:
            return None
        if i + 1 < len(activities):
            return activities[i + 1]
        return activities[0]

    def get_active_activity(self):
        """Returns the activity that the user is currently working in"""
        return self._active_activity

    def add_shared_activity(self, activity_id, color):
        self._shared_activities[activity_id] = color

    def remove_shared_activity(self, activity_id):
        del self._shared_activities[activity_id]

    def get_tabbing_activity(self):
        return self._tabbing_activity

    def set_tabbing_activity(self, activity):
        self._tabbing_activity = activity
        self.emit('tabbing-activity-changed', self._tabbing_activity)

    def _set_active_activity(self, home_activity):
        if self._active_activity == home_activity:
            return

        if home_activity:
            home_activity.set_active(True)

        if self._active_activity:
            self._active_activity.set_active(False)

        self._active_activity = home_activity
        self.emit('active-activity-changed', self._active_activity)

    def activate_activity(self, activity):
        if activity is None:
            return

        self._set_active_activity(activity)
        self.set_zoom_level(self.ZOOM_ACTIVITY)

        window = activity.get_window()
        if window is not None:
            if hasattr(window, 'present'):
                window.present()
            elif hasattr(window, 'activate'):
                window.activate(0)

    def __iter__(self):
        return iter(self._activities)

    def __len__(self):
        return len(self._activities)

    def __getitem__(self, i):
        return self._activities[i]

    def index(self, obj):
        return self._activities.index(obj)

    def _window_added_cb(self, application, window):
        if not isinstance(window, Gtk.Dialog):
            if type(window).__name__ in ('IntroWindow', 'HomeWindow', 'LaunchWindow'):
                return


            if isinstance(window, Gtk.ApplicationWindow) and \
                    not getattr(window, 'activity_id', None):
                logging.debug('_window_added_cb: ignoring non-activity '
                              'ApplicationWindow %r', window)
                return

            home_activity = None

            activity_id = getattr(window, 'activity_id', None)
            service_name = getattr(window, 'bundle_id', None)

            if not service_name:
                if hasattr(window, 'get_app_id'):
                    service_name = window.get_app_id()
                elif hasattr(window, 'app_id'):
                    service_name = getattr(window, 'app_id')

            if not activity_id and service_name:
                for a_id in list(self._launchers.keys()):
                    home_act = self.get_activity_by_id(a_id)
                    if home_act and home_act.get_bundle_id() == service_name:
                        if home_act.get_launch_status() == Activity.LAUNCHING:
                            activity_id = a_id
                            break

            if service_name:
                registry = get_registry()
                activity_info = registry.get_bundle(service_name)
            else:
                activity_info = None

            if activity_id:
                home_activity = self.get_activity_by_id(activity_id)

                window.set_decorated(False)
                window.maximize()

            def is_main_window(window, home_activity):
                return home_activity.get_launch_status() == Activity.LAUNCHING

            if home_activity is None and not isinstance(window, Gtk.Dialog):
                color = self._shared_activities.get(activity_id, None)
                home_activity = Activity(activity_info, activity_id,
                                         color, window)
                self._add_activity(home_activity)
            else:
                logging.debug('window registered for %s', activity_id)
                home_activity.add_window(window, is_main_window(window,
                                                                home_activity))

            if is_main_window(window, home_activity):
                self.emit('launch-completed', home_activity)
                startup_time = time.time() - home_activity.get_launch_time()
                logging.debug('%s launched in %f seconds.',
                              activity_id, startup_time)
                self.emit('active-window-changed', window)

            if self._active_activity is None:
                self._set_active_activity(home_activity)

    def _window_removed_cb(self, application, window):
        activity_id = getattr(window, 'activity_id', None)
        if not activity_id:
            service_name = getattr(window, 'bundle_id', None)
            if not service_name:
                if hasattr(window, 'get_app_id'):
                    service_name = window.get_app_id()
                elif hasattr(window, 'app_id'):
                    service_name = getattr(window, 'app_id')

            if service_name:
                for home_act in self._activities:
                    if home_act.get_bundle_id() == service_name and home_act.get_window() == window:
                        activity_id = home_act.get_activity_id()
                        break

        if activity_id:
            activity = self.get_activity_by_id(activity_id)
            if activity is not None:
                activity.remove_window(window)
                if activity.get_window() is None:
                    logging.debug('last window gone - remove activity %s',
                                  activity)
                    activity.close_window()
                    self._remove_activity(activity)

    def _get_activity_by_bundle_id(self, bundle_id):
        for home_activity in self._activities:
            if home_activity.has_bundle_id(bundle_id):
                return home_activity
        return None

    def get_activity_by_id(self, activity_id):
        for home_activity in self._activities:
            if home_activity.get_activity_id() == activity_id:
                return home_activity
        return None

    def _active_window_changed_cb(self, application, window):
        if window is None:
            return

        if not isinstance(window, Gtk.Dialog):
            while window.get_transient_for() is not None:
                window = window.get_transient_for()

        data = window
        bundle_id = getattr(data, 'bundle_id', None)
        if not bundle_id:
            return
        act = self._get_activity_by_bundle_id(bundle_id)
        if act is not None:
            self._set_active_activity(act)

        self._update_zoom_level(window)

    def get_name_from_bundle_id(self, bundle_id):
        for activity in self._get_activities_with_window():
            if activity.get_bundle_id() == bundle_id:
                return activity.get_activity_name()
        return ''

    def can_launch_activity_instance(self, bundle):
        if bundle.get_single_instance():
            bundle_id = bundle.get_bundle_id()
            for activity in self._get_activities_with_window():
                if activity.get_bundle_id() == bundle_id:
                    return False
        return True

    def can_launch_activity(self):
        activities = self._get_activities_with_window()
        if self._maximum_open_activities > 0 and \
                   len(activities) > self._maximum_open_activities:
            return False
        return True

    def _add_activity(self, home_activity):
        self._activities.append(home_activity)
        self.emit('activity-added', home_activity)

    def _remove_activity(self, home_activity):
        if home_activity == self._active_activity:
            windows = self.get_windows()
            windows.reverse()
            for window in windows:
                data = window
                bundle_id = getattr(data, 'bundle_id', None)
                if not bundle_id:
                    continue
                new_activity = self._get_activity_by_bundle_id(bundle_id)
                if new_activity is not None:
                    self._set_active_activity(new_activity)
                    break
            else:
                self._set_active_activity(None)
                self.set_zoom_level(self._desktop_level)

        self.emit('activity-removed', home_activity)
        self._activities.remove(home_activity)

    def notify_launch(self, activity_id, service_name):
        registry = get_registry()
        activity_info = registry.get_bundle(service_name)
        if not activity_info:
            raise ValueError("Activity service name '%s'"
                             " was not found in the bundle registry."
                             % service_name)
        color = self._shared_activities.get(activity_id, None)
        home_activity = Activity(activity_info, activity_id, color)
        self._add_activity(home_activity)

        self._set_active_activity(home_activity)

        self.set_zoom_level(self.ZOOM_ACTIVITY)
        self.emit('launch-started', home_activity)

        if activity_id in self._launch_timers:
            GLib.source_remove(self._launch_timers[activity_id])
            del self._launch_timers[activity_id]

        timer = GLib.timeout_add_seconds(90, self._check_activity_launched,
                                         activity_id)
        self._launch_timers[activity_id] = timer

    def notify_launch_failed(self, activity_id):
        home_activity = self.get_activity_by_id(activity_id)
        if home_activity:
            logging.debug('Activity %s (%s) launch failed', activity_id,
                          home_activity.get_type())
            if self.get_launcher(activity_id) is not None:
                self.emit('launch-failed', home_activity)
            else:
                # activity sent failure notification after closing launcher
                self._remove_activity(home_activity)
        else:
            logging.error('Model for activity id %s does not exist.',
                          activity_id)

    def _check_activity_launched(self, activity_id):
        del self._launch_timers[activity_id]
        home_activity = self.get_activity_by_id(activity_id)

        if not home_activity:
            logging.debug('Activity %s has been closed already.', activity_id)
            return False

        if self.get_launcher(activity_id) is not None:
            logging.debug('Activity %s still launching, assuming it failed.',
                          activity_id)
            self.notify_launch_failed(activity_id)
        return False

    def push_modal(self):
        self._modal_dialogs_counter += 1

    def pop_modal(self):
        self._modal_dialogs_counter -= 1

    def has_modal(self):
        return self._modal_dialogs_counter > 0


def get_model():
    global _model
    if _model is None:
        _model = ShellModel()
    return _model
