# Copyright (C) 2006-2007 Owen Williams.
# Copyright (C) 2006-2008 Red Hat, Inc.
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

import logging
import time
import os

import wnck
import gobject
import gtk
import dbus

from sugar import wm
from sugar.activity import get_registry
from sugar.graphics.xocolor import XoColor
from sugar.presence import presenceservice
from sugar import profile

from jarabe import config

_SERVICE_NAME = "org.laptop.Activity"
_SERVICE_PATH = "/org/laptop/Activity"
_SERVICE_INTERFACE = "org.laptop.Activity"

def get_sugar_window_type(wnck_window):
    window = gtk.gdk.window_foreign_new(wnck_window.get_xid())
    prop_info = window.property_get('_SUGAR_WINDOW_TYPE', 'STRING')
    if prop_info is None:
        return None
    else:
        return prop_info[2]

class Activity(gobject.GObject):
    """Activity which appears in the "Home View" of the Sugar shell
    
    This class stores the Sugar Shell's metadata regarding a
    given activity/application in the system.  It interacts with
    the sugar.activity.* modules extensively in order to 
    accomplish its tasks.
    """

    __gtype_name__ = 'SugarHomeActivity'

    __gproperties__ = {
        'launching' : (bool, None, None, False,
                       gobject.PARAM_READWRITE),
    }

    def __init__(self, activity_info, activity_id, window=None):
        """Initialise the HomeActivity
        
        activity_info -- sugar.activity.registry.ActivityInfo instance,
            provides the information required to actually
            create the new instance.  This is, in effect,
            the "type" of activity being created.
        activity_id -- unique identifier for this instance
            of the activity type
        window -- Main WnckWindow of the activity 
        """
        gobject.GObject.__init__(self)

        self._window = None
        self._service = None
        self._activity_id = activity_id
        self._activity_info = activity_info
        self._launch_time = time.time()
        self._launching = False

        if window is not None:
            self.set_window(window)

        self._retrieve_service()

        self._name_owner_changed_handler = None
        if not self._service:
            bus = dbus.SessionBus()
            self._name_owner_changed_handler = bus.add_signal_receiver(
                    self._name_owner_changed_cb,
                    signal_name="NameOwnerChanged",
                    dbus_interface="org.freedesktop.DBus")

    def set_window(self, window):
        """Set the window for the activity

        We allow resetting the window for an activity so that we
        can replace the launcher once we get its real window.
        """
        if not window:
            raise ValueError("window must be valid")
        self._window = window

    def get_service(self):
        """Get the activity service
        
        Note that non-native Sugar applications will not have
        such a service, so the return value will be None in
        those cases.
        """

        return self._service

    def get_title(self):
        """Retrieve the application's root window's suggested title"""
        if self._window:
            return self._window.get_name()
        else:
            return ''

    def get_icon_path(self):
        """Retrieve the activity's icon (file) name"""
        if self.is_journal():
            return os.path.join(config.data_path, 'icons/activity-journal.svg')
        elif self._activity_info:
            return self._activity_info.icon
        else:
            return None
    
    def get_icon_color(self):
        """Retrieve the appropriate icon colour for this activity
        
        Uses activity_id to index into the PresenceService's 
        set of activity colours, if the PresenceService does not
        have an entry (implying that this is not a Sugar-shared application)
        uses the local user's profile.get_color() to determine the
        colour for the icon.
        """
        pservice = presenceservice.get_instance()

        # HACK to suppress warning in logs when activity isn't found
        # (if it's locally launched and not shared yet)
        activity = None
        for act in pservice.get_activities():
            if self._activity_id == act.props.id:
                activity = act
                break

        if activity != None:
            return XoColor(activity.props.color)
        else:
            return profile.get_color()
        
    def get_activity_id(self):
        """Retrieve the "activity_id" passed in to our constructor
        
        This is a "globally likely unique" identifier generated by
        sugar.util.unique_id
        """
        return self._activity_id

    def get_xid(self):
        """Retrieve the X-windows ID of our root window"""
        return self._window.get_xid()

    def get_window(self):
        """Retrieve the X-windows root window of this application
        
        This was stored by the set_window method, which was 
        called by HomeModel._add_activity, which was called 
        via a callback that looks for all 'window-opened'
        events.
        
        HomeModel currently uses a dbus service query on the
        activity to determine to which HomeActivity the newly
        launched window belongs.
        """
        return self._window

    def get_type(self):
        """Retrieve the activity bundle id for future reference"""
        if self._window is None:
            return None
        else:
            return wm.get_bundle_id(self._window)

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
        return self._window.get_pid()

    def equals(self, activity):
        if self._activity_id and activity.get_activity_id():
            return self._activity_id == activity.get_activity_id()
        if self._window.get_xid() and activity.get_xid():
            return self._window.get_xid() == activity.get_xid()
        return False

    def do_set_property(self, pspec, value):
        if pspec.name == 'launching':
            self._launching = value

    def do_get_property(self, pspec):
        if pspec.name == 'launching':
            return self._launching

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
                                   _SERVICE_PATH + "/" + self._activity_id)
            self._service = dbus.Interface(proxy, _SERVICE_INTERFACE)
        except dbus.DBusException:
            self._service = None

    def _name_owner_changed_cb(self, name, old, new):
        if name == self._get_service_name():
            self._retrieve_service()
            self.set_active(True)
            self._name_owner_changed_handler.remove()
            self._name_owner_changed_handler = None

    def set_active(self, state):
        """Propagate the current state to the activity object"""
        if self._service is not None:
            self._service.SetActive(state,
                                    reply_handler=self._set_active_success,
                                    error_handler=self._set_active_error)

    def _set_active_success(self):
        pass
    
    def _set_active_error(self, err):
        logging.error("set_active() failed: %s" % err)

class ShellModel(gobject.GObject):
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
        'activity-added':          (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT])),
        'activity-removed':        (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,
                                   ([gobject.TYPE_PYOBJECT])),
        'active-activity-changed': (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,
                                   ([gobject.TYPE_PYOBJECT])),
        'tabbing-activity-changed': (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,
                                   ([gobject.TYPE_PYOBJECT])),
        'launch-started':          (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT])),
        'launch-completed':        (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT])),
        'launch-failed':           (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT]))
    }

    ZOOM_MESH = 0
    ZOOM_FRIENDS = 1
    ZOOM_HOME = 2
    ZOOM_ACTIVITY = 3

    __gproperties__ = {
        'zoom-level' : (int, None, None,
                        0, 3, ZOOM_HOME,
                        gobject.PARAM_READABLE)
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._current_activity = None
        self._zoom_level = self.ZOOM_HOME
        self._showing_desktop = True
        self._activities = []
        self._active_activity = None
        self._tabbing_activity = None
        self._pservice = presenceservice.get_instance()

        self._screen = wnck.screen_get_default()
        self._screen.connect('window-opened', self._window_opened_cb)
        self._screen.connect('window-closed', self._window_closed_cb)
        self._screen.connect('showing-desktop-changed',
                             self._showing_desktop_changed_cb)
        self._screen.connect('active-window-changed',
                             self._active_window_changed_cb)

    def set_zoom_level(self, level):
        self._zoom_level = level
        self.notify('zoom-level')

    def get_zoom_level(self):
        if self._screen.get_showing_desktop():
            return self._zoom_level
        else:
            return self.ZOOM_ACTIVITY

    def do_get_property(self, pspec):
        if pspec.name == 'zoom-level':
            return self.get_zoom_level()                

    def _showing_desktop_changed_cb(self, screen):
        showing_desktop = self._screen.get_showing_desktop()
        if self._showing_desktop != showing_desktop:
            self._showing_desktop = showing_desktop
            self.notify('zoom-level')

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

    def get_tabbing_activity(self):
        """Returns the activity that is currently highlighted during tabbing"""
        return self._tabbing_activity

    def set_tabbing_activity(self, activity):
        """Sets the activity that is currently highlighted during tabbing"""
        self._tabbing_activity = activity
        self.emit("tabbing-activity-changed", self._tabbing_activity)

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
        if window.get_window_type() == wnck.WINDOW_NORMAL:
            home_activity = None

            activity_id = wm.get_activity_id(window)

            service_name = wm.get_bundle_id(window)
            if service_name:
                registry = get_registry()
                activity_info = registry.get_activity(service_name)
            else:
                activity_info = None

            if activity_id:
                home_activity = self.get_activity_by_id(activity_id)

            if not home_activity:
                home_activity = Activity(activity_info, activity_id, window)
                self._add_activity(home_activity)
            else:
                home_activity.set_window(window)

            if get_sugar_window_type(window) != 'launcher':
                home_activity.props.launching = False
                self.emit('launch-completed', home_activity)

            if self._active_activity is None:
                self._set_active_activity(home_activity)

    def _window_closed_cb(self, screen, window):
        if window.get_window_type() == wnck.WINDOW_NORMAL:
            self._remove_activity_by_xid(window.get_xid())

    def _get_activity_by_xid(self, xid):
        for home_activity in self._activities:
            if home_activity.get_xid() == xid:
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

        if window.get_window_type() != wnck.WINDOW_DIALOG:
            while window.get_transient() is not None:
                window = window.get_transient()

        act = self._get_activity_by_xid(window.get_xid())
        if act is not None:
            self._set_active_activity(act)

    def _add_activity(self, home_activity):
        self._activities.append(home_activity)
        self.emit('activity-added', home_activity)

    def _remove_activity(self, home_activity):
        if home_activity == self._active_activity:
            windows = wnck.screen_get_default().get_windows_stacked()
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

    def _remove_activity_by_xid(self, xid):
        home_activity = self._get_activity_by_xid(xid)
        if home_activity:
            self._remove_activity(home_activity)
        else:
            logging.error('Model for window %d does not exist.' % xid)

    def notify_launch(self, activity_id, service_name):
        registry = get_registry()
        activity_info = registry.get_activity(service_name)
        if not activity_info:
            raise ValueError("Activity service name '%s'" \
                             " was not found in the bundle registry."
                             % service_name)
        home_activity = Activity(activity_info, activity_id)
        home_activity.props.launching = True
        self._add_activity(home_activity)

        self._set_active_activity(home_activity)

        self.emit('launch-started', home_activity)

        # FIXME: better learn about finishing processes by receiving a signal.
        # Now just check whether an activity has a window after ~90sec
        gobject.timeout_add(90000, self._check_activity_launched, activity_id)

    def notify_launch_failed(self, activity_id):
        home_activity = self.get_activity_by_id(activity_id)
        if home_activity:
            logging.debug("Activity %s (%s) launch failed" % \
                          (activity_id, home_activity.get_type()))
            home_activity.props.launching = False
            self._remove_activity(home_activity)
        else:
            logging.error('Model for activity id %s does not exist.'
                          % activity_id)

        self.emit('launch-failed', home_activity)

    def _check_activity_launched(self, activity_id):
        home_activity = self.get_activity_by_id(activity_id)

        if not home_activity:
            logging.debug('Activity %s has been closed already.' % activity_id)
            return False

        if home_activity.props.launching:
            logging.debug('Activity %s still launching, assuming it failed...'
                          % activity_id)
            self.notify_launch_failed(activity_id)
        return False

_model = None

def get_model():
    global _model
    if _model is None:
        _model = ShellModel()
    return _model

