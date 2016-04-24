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

from gi.repository import Gio
from gi.repository import Wnck
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GLib
import dbus

from sugar3 import dispatch
from sugar3 import profile
from gi.repository import SugarExt

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
        _windows -- WnckWindows registered for the activity. The lowest
                    one in the stack is the main window.
        """
        GObject.GObject.__init__(self)

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
        if not self._service:
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

    launch_status = GObject.property(getter=get_launch_status)

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
        if self.get_window() is not None:
            self.get_window().close(GLib.get_current_time())

        for w in self._shell_windows:
            w.destroy()

    def remove_window_by_xid(self, xid):
        """Remove a window from the windows stack."""
        for wnd in self._windows:
            if wnd.get_xid() == xid:
                self._windows.remove(wnd)
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
            return self._windows[0].get_name()
        else:
            return None

    def get_icon_path(self):
        """Retrieve the activity's icon (file) name"""
        if self.is_journal():
            icon_theme = Gtk.IconTheme.get_default()
            info = icon_theme.lookup_icon('activity-journal',
                                          Gtk.IconSize.SMALL_TOOLBAR, 0)
            if not info:
                return None
            fname = info.get_filename()
            del info
            return fname
        elif self._activity_info:
            return self._activity_info.get_icon()
        else:
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
        else:
            return self._activity_info.get_bundle_id()

    def get_xid(self):
        """Retrieve the X-windows ID of our root window"""
        if self._windows:
            return self._windows[0].get_xid()
        else:
            return None

    def has_xid(self, xid):
        """Check if an X-window with the given xid is in the windows stack"""
        if self._windows:
            for wnd in self._windows:
                if wnd.get_xid() == xid:
                    return True
        return False

    def get_window(self):
        """Retrieve the X-windows root window of this application

        This was stored by the add_window method, which was
        called by HomeModel._add_activity, which was called
        via a callback that looks for all 'window-opened'
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
        else:
            return SugarExt.wm_get_bundle_id(self._windows[0].get_xid())

    def is_journal(self):
        """Returns boolean if the activity is of type JournalActivity"""
        return self.get_type() == 'org.laptop.JournalActivity'

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
        return self._windows[0].get_pid()

    def get_bundle_path(self):
        """Returns the activity's bundle directory"""
        if self._activity_info is None:
            return None
        else:
            return self._activity_info.get_path()

    def get_activity_name(self):
        """Returns the activity's bundle name"""
        if self._activity_info is None:
            return None
        else:
            return self._activity_info.get_name()

    def equals(self, activity):
        if self._activity_id and activity.get_activity_id():
            return self._activity_id == activity.get_activity_id()
        if self._windows[0].get_xid() and activity.get_xid():
            return self._windows[0].get_xid() == activity.get_xid()
        return False

    def _get_service_name(self):
        if self._activity_id:
            return _SERVICE_NAME + self._activity_id
        else:
            return None

    def _retrieve_service(self):
        if not self._activity_id:
            return

        try:
            bus = dbus.SessionBus()
            proxy = bus.get_object(self._get_service_name(),
                                   _SERVICE_PATH + '/' + self._activity_id)
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
            elif not old and new:
                logging.debug('Activity._name_owner_changed_cb: '
                              'activity %s started up', name)
                self._retrieve_service()
                self.set_active(True)

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

    def _state_changed_cb(self, main_window, changed_mask, new_state):
        if changed_mask & Wnck.WindowState.MINIMIZED:
            if new_state & Wnck.WindowState.MINIMIZED:
                self.emit('pause')
            else:
                self.emit('resume')


class ShellModel(GObject.GObject):
    """Model of the shell (activity management)

    The ShellModel is basically the point of registration
    for all running activities within Sugar.  It traps
    events that tell the system there is a new activity
    being created (generated by the activity factories),
    or removed, as well as those which tell us that the
    currently focussed activity has changed.

    The HomeModel tracks a set of HomeActivity instances,
    which are tracking the window to activity mappings
    the activity factories have set up.
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
    }

    ZOOM_MESH = 0
    ZOOM_GROUP = 1
    ZOOM_HOME = 2
    ZOOM_ACTIVITY = 3

    def __init__(self):
        GObject.GObject.__init__(self)

        self._screen = Wnck.Screen.get_default()
        self._screen.connect('window-opened', self._window_opened_cb)
        self._screen.connect('window-closed', self._window_closed_cb)
        self._screen.connect('active-window-changed',
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

        self._screen.toggle_showing_desktop(True)

        settings = Gio.Settings('org.sugarlabs')
        self._maximum_open_activities = settings.get_int(
            'maximum-number-of-open-activities')

        self._launch_timers = {}

    def get_launcher(self, activity_id):
        return self._launchers.get(str(activity_id))

    def register_launcher(self, activity_id, launcher):
        self._launchers[activity_id] = launcher

    def unregister_launcher(self, activity_id):
        if activity_id in self._launchers:
            del self._launchers[activity_id]

    def _update_zoom_level(self, window):
        if window.get_window_type() == Wnck.WindowType.DIALOG:
            return
        elif window.get_window_type() == Wnck.WindowType.NORMAL:
            new_level = self.ZOOM_ACTIVITY
        else:
            new_level = self._desktop_level

        if self._zoom_level != new_level:
            old_level = self._zoom_level
            self._zoom_level = new_level
            self.zoom_level_changed.send(self, old_level=old_level,
                                         new_level=new_level)

    def set_zoom_level(self, new_level, x_event_time=0):
        old_level = self.zoom_level
        if old_level == new_level:
            return

        self._zoom_level = new_level
        if new_level is not self.ZOOM_ACTIVITY:
            self._desktop_level = new_level

        self.zoom_level_changed.send(self, old_level=old_level,
                                     new_level=new_level)

        show_desktop = new_level is not self.ZOOM_ACTIVITY
        self._screen.toggle_showing_desktop(show_desktop)

        if new_level is self.ZOOM_ACTIVITY:
            # activate the window, in case it was iconified
            # (e.g. during sugar launch, the Journal starts in this state)
            window = self._active_activity.get_window()
            if window:
                window.activate(x_event_time or Gtk.get_current_event_time())

    def _get_zoom_level(self):
        return self._zoom_level

    zoom_level = property(_get_zoom_level)

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
        elif i - 1 >= 0:
            return activities[i - 1]
        else:
            return activities[len(activities) - 1]

    def get_next_activity(self, current=None):
        if not current:
            current = self._active_activity

        activities = self._get_activities_with_window()
        i = activities.index(current)
        if len(activities) == 0:
            return None
        elif i + 1 < len(activities):
            return activities[i + 1]
        else:
            return activities[0]

    def get_active_activity(self):
        """Returns the activity that the user is currently working in"""
        return self._active_activity

    def add_shared_activity(self, activity_id, color):
        self._shared_activities[activity_id] = color

    def remove_shared_activity(self, activity_id):
        del self._shared_activities[activity_id]

    def get_tabbing_activity(self):
        """Returns the activity that is currently highlighted during tabbing"""
        return self._tabbing_activity

    def set_tabbing_activity(self, activity):
        """Sets the activity that is currently highlighted during tabbing"""
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

    def __iter__(self):
        return iter(self._activities)

    def __len__(self):
        return len(self._activities)

    def __getitem__(self, i):
        return self._activities[i]

    def index(self, obj):
        return self._activities.index(obj)

    def _window_opened_cb(self, screen, window):
        """Handle the callback for the 'window opened' event.

           Most activities will register 2 windows during
           their lifetime: the launcher window, and the 'main'
           app window.

           When the main window appears, we send a signal to
           the launcher window to close.

           Some activities (notably non-native apps) open several
           windows during their lifetime, switching from one to
           the next as the 'main' window. We use a stack to track
           them.

         """
        if window.get_window_type() == Wnck.WindowType.NORMAL or \
                window.get_window_type() == Wnck.WindowType.SPLASHSCREEN:
            home_activity = None
            xid = window.get_xid()

            activity_id = SugarExt.wm_get_activity_id(xid)

            service_name = SugarExt.wm_get_bundle_id(xid)
            if service_name:
                registry = get_registry()
                activity_info = registry.get_bundle(service_name)
            else:
                activity_info = None

            if activity_id:
                home_activity = self.get_activity_by_id(activity_id)

                display = Gdk.Display.get_default()
                gdk_window = GdkX11.X11Window.foreign_new_for_display(display,
                                                                      xid)
                gdk_window.set_decorations(0)

                window.maximize()

            def is_main_window(window, home_activity):
                # Check if window is the 'main' app window, not the
                # launcher window.
                return window.get_window_type() != \
                    Wnck.WindowType.SPLASHSCREEN and \
                    home_activity.get_launch_status() == Activity.LAUNCHING

            if home_activity is None and \
                    window.get_window_type() == Wnck.WindowType.NORMAL:
                # This is a special case for the Journal
                # We check if is not a splash screen to avoid #4767
                logging.debug('first window registered for %s', activity_id)
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

            if self._active_activity is None:
                self._set_active_activity(home_activity)

    def _window_closed_cb(self, screen, window):
        if window.get_window_type() == Wnck.WindowType.NORMAL or \
                window.get_window_type() == Wnck.WindowType.SPLASHSCREEN:
            xid = window.get_xid()
            activity = self._get_activity_by_xid(xid)
            if activity is not None:
                activity.remove_window_by_xid(xid)
                if activity.get_window() is None:
                    logging.debug('last window gone - remove activity %s',
                                  activity)
                    activity.close_window()
                    self._remove_activity(activity)

    def _get_activity_by_xid(self, xid):
        for home_activity in self._activities:
            if home_activity.has_xid(xid):
                return home_activity
        return None

    def get_activity_by_id(self, activity_id):
        for home_activity in self._activities:
            if home_activity.get_activity_id() == activity_id:
                return home_activity
        return None

    def _active_window_changed_cb(self, screen, previous_window=None):
        window = screen.get_active_window()
        if window is None:
            return

        if window.get_window_type() != Wnck.WindowType.DIALOG:
            while window.get_transient() is not None:
                window = window.get_transient()

        act = self._get_activity_by_xid(window.get_xid())
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
        else:
            return True

    def _add_activity(self, home_activity):
        self._activities.append(home_activity)
        self.emit('activity-added', home_activity)

    def _remove_activity(self, home_activity):
        if home_activity == self._active_activity:
            windows = Wnck.Screen.get_default().get_windows_stacked()
            windows.reverse()
            for window in windows:
                new_activity = self._get_activity_by_xid(window.get_xid())
                if new_activity is not None:
                    self._set_active_activity(new_activity)
                    break
            else:
                logging.error('No activities are running')
                self._set_active_activity(None)

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

        self.emit('launch-started', home_activity)

        if activity_id in self._launch_timers:
            GObject.source_remove(self._launch_timers[activity_id])
            del self._launch_timers[activity_id]

        timer = GObject.timeout_add_seconds(90, self._check_activity_launched,
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
