# Copyright (C) 2006, Red Hat, Inc.
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

import gtk
import gobject
import wnck
import dbus

import view.stylesheet
from sugar.graphics import style
from view.home.HomeWindow import HomeWindow
from sugar.presence import PresenceService
from view.ActivityHost import ActivityHost
from sugar.activity import ActivityFactory
from sugar.activity import Activity
from view.frame.Frame import Frame
from model.ShellModel import ShellModel
from hardwaremanager import HardwareManager
from _sugar import KeyGrabber
from _sugar import AudioManager
from sugar import env
import sugar


_SHELL_SERVICE = "org.laptop.sugar.Shell"
_SHELL_PATH = "/org/laptop/sugar/Shell"
_SHELL_INTERFACE = "org.laptop.sugar.Shell"


_NMC_SERVICE = "org.laptop.sugar.NMClient"
_NMC_PATH = "/org/laptop/sugar/NMClient"
_NMC_INTERFACE = "org.laptop.sugar.NMClient"


class FrameNotifier(dbus.service.Object):
    def __init__(self):
        self._session_bus = dbus.SessionBus()
        self._bus_name = dbus.service.BusName(_SHELL_SERVICE, bus=self._session_bus)        
        dbus.service.Object.__init__(self, self._bus_name, _SHELL_PATH)

    @dbus.service.signal(_SHELL_INTERFACE, signature="")
    def FrameDeactivated(self):
        pass


class Shell(gobject.GObject):
    def __init__(self, model):
        gobject.GObject.__init__(self)

        self._model = model
        self._hosts = {}
        self._screen = wnck.screen_get_default()
        self._current_host = None
        self._screen_rotation = 0

        style.load_stylesheet(view.stylesheet)

        self._hw_manager = HardwareManager()
        self._audio_manager = AudioManager()

        self._key_grabber = KeyGrabber()
        self._key_grabber.connect('key-pressed',
                                  self._key_pressed_cb)
        self._key_grabber.connect('key-released',
                                  self._key_released_cb)
        self._grab_keys()

        self._home_window = HomeWindow(self)
        self._home_window.show()
        self.set_zoom_level(sugar.ZOOM_HOME)

        home_model = self._model.get_home()
        home_model.connect('activity-added', self._activity_added_cb)
        home_model.connect('activity-removed', self._activity_removed_cb)
        home_model.connect('active-activity-changed',
                           self._active_activity_changed_cb)

        self._frame = Frame(self)
        self._frame.show_and_hide(3)
        self._frame.connect('deactivated', self._frame_deactivated_cb)

        self._pservice = PresenceService.get_instance()

        self._dbus_helper = FrameNotifier()

        ses_bus = dbus.SessionBus()
        self._nmc_proxy = ses_bus.get_object(_NMC_SERVICE, _NMC_PATH)
        self._nmc_obj = dbus.Interface(self._nmc_proxy, _NMC_INTERFACE)
        ses_bus.add_signal_receiver(self._nmc_menu_activated_cb,
                                    signal_name="MenuActivated",
                                    dbus_interface=_NMC_INTERFACE)
        ses_bus.add_signal_receiver(self._nmc_menu_deactivated_cb,
                                    signal_name="MenuDeactivated",
                                    dbus_interface=_NMC_INTERFACE)

        #self.start_activity('org.laptop.JournalActivity')

    def _handle_camera_key(self):
        if self._current_host:
            if self._current_host.execute('camera', []):
                return

        self.start_activity('org.laptop.CameraActivity')

    def _grab_keys(self):
        self._key_grabber.grab('F1')
        self._key_grabber.grab('F2')
        self._key_grabber.grab('F3')
        self._key_grabber.grab('F4')
        self._key_grabber.grab('F5')
        self._key_grabber.grab('F6')
        self._key_grabber.grab('F7')
        self._key_grabber.grab('F8')
        self._key_grabber.grab('F9')
        self._key_grabber.grab('F10')
        self._key_grabber.grab('F11')
        self._key_grabber.grab('F12')
        self._key_grabber.grab('<alt>F5')
        self._key_grabber.grab('<alt>F8')
        self._key_grabber.grab('<alt>equal')
        self._key_grabber.grab('<alt>0')

        self._key_grabber.grab('0xDC') # Camera key
        self._key_grabber.grab('0xE0') # Overlay key
        self._key_grabber.grab('0x93') # Frame key
        self._key_grabber.grab('0x7C') # Power key
        self._key_grabber.grab('0xEB') # Rotate key
        self._key_grabber.grab('0xEC') # Keyboard brightness
        self._key_grabber.grab('<alt>Tab')

        # For non-OLPC machines
        self._key_grabber.grab('<alt>f')
        self._key_grabber.grab('<alt>o')
        self._key_grabber.grab('<alt>r')
        self._key_grabber.grab('<alt><shift>s')

    def _key_pressed_cb(self, grabber, key):
        if key == 'F1':
            self.set_zoom_level(sugar.ZOOM_MESH)
        elif key == 'F2':
            self.set_zoom_level(sugar.ZOOM_FRIENDS)
        elif key == 'F3':
            self.set_zoom_level(sugar.ZOOM_HOME)
        elif key == 'F4':
            self.set_zoom_level(sugar.ZOOM_ACTIVITY)
        elif key == 'F5':
            self._hw_manager.set_display_brightness(0)
        elif key == 'F6':
            self._hw_manager.set_display_brightness(5)
        elif key == 'F7':
            self._hw_manager.set_display_brightness(9)
        elif key == 'F8':
            self._hw_manager.set_display_brightness(15)
        elif key == 'F9':
            self._audio_manager.set_volume(0)
        elif key == 'F10':
            self._audio_manager.set_volume(40)
        elif key == 'F11':
            self._audio_manager.set_volume(75)
        elif key == 'F12':
            self._audio_manager.set_volume(100)
        elif key == '<alt>F5':
            self._hw_manager.set_display_mode(HardwareManager.COLOR_MODE)
        elif key == '<alt>F8':
            self._hw_manager.set_display_mode(HardwareManager.B_AND_W_MODE)
        elif key == '<alt>equal' or key == '<alt>0':
            gobject.idle_add(self._toggle_console_visibility_cb)
        elif key == '<alt>f':
            self._frame.notify_key_press()
        elif key == '<alt>o':
            self.toggle_chat_visibility()
        elif key == '0xDC': # Camera key
            # Disable until key autorepeat is fixed on the olpc
            #self._handle_camera_key()
            pass
        elif key == '0xE0': # Overlay key
            self.toggle_chat_visibility()
        elif key == '0x93': # Frame key
            self._frame.notify_key_press()
        elif key == '0x7C' or key == '<alt><shift>s': # Power key
            self._shutdown()
        elif key == '0xEB' or key == '<alt>r': # Rotate key
            self._rotate_screen()
        elif key == '0xEC': # Keyboard brightness
            self._hw_manager.toggle_keyboard_brightness()
        elif key == '<alt>Tab':
            self.set_zoom_level(sugar.ZOOM_HOME)
            box = self._home_window.get_home_box()
            box.grab_and_rotate()

    def _toggle_console_visibility_cb(self):
        bus = dbus.SessionBus()
        proxy = bus.get_object('org.laptop.sugar.Console',
                               '/org/laptop/sugar/Console')
        console = dbus.Interface(proxy, 'org.laptop.sugar.Console')
        console.toggle_visibility()

    def _rotate_screen(self):
        states = [ 'normal', 'left', 'inverted', 'right']

        self._screen_rotation += 1
        if self._screen_rotation == len(states):
            self._screen_rotation = 0

        gobject.spawn_async(['xrandr', '-o', states[self._screen_rotation]],
                            flags=gobject.SPAWN_SEARCH_PATH)

    def _shutdown(self):
        self._model.props.state = ShellModel.STATE_SHUTDOWN
        if not env.is_emulator():
            self._shutdown_system()

    def _shutdown_system(self):
        bus = dbus.SystemBus()
        proxy = bus.get_object('org.freedesktop.Hal',
                               '/org/freedesktop/Hal/devices/computer')
        mgr = dbus.Interface(proxy, 'org.freedesktop.Hal.Device.SystemPowerManagement')
        mgr.Shutdown()

    def _key_released_cb(self, grabber, key):
        if key == '<shft><alt>F9':
            self._frame.notify_key_release()
        elif key == '0x93':
            self._frame.notify_key_release()

    def _activity_added_cb(self, home_model, home_activity):
        activity_host = ActivityHost(home_activity)
        self._hosts[activity_host.get_xid()] = activity_host

    def _activity_removed_cb(self, home_model, home_activity):
        if not home_activity.get_launched():
            return
        xid = home_activity.get_xid()
        if self._hosts.has_key(xid):
            self._hosts[xid].destroy()
            del self._hosts[xid]

    def _active_activity_changed_cb(self, home_model, home_activity):
        if home_activity:
            host = self._hosts[home_activity.get_xid()]
        else:
            host = None

        if self._current_host:
            self._current_host.set_active(False)

        self._current_host = host

        if self._current_host:
            self._current_host.set_active(True)

    def get_model(self):
        return self._model

    def _join_success_cb(self, handler, activity, activity_ps, activity_id, activity_type):
        logging.debug("Joining activity %s (%s)" % (activity_id, activity_type))
        activity.join(activity_ps.object_path())

    def _join_error_cb(self, handler, err, home_model, activity_id, activity_type):
        logging.error("Couldn't launch activity %s (%s):\n%s" % (activity_id, activity_type, err))
        home_mode.notify_activity_launch_failed(activity_id)

    def join_activity(self, bundle_id, activity_id):
        activity = self.get_activity(activity_id)
        if activity:
            activity.present()
            return

        activity_ps = self._pservice.get_activity(activity_id)
        if not activity_ps:
            logging.error("Couldn't find shared activity for %s" % activity_id)
            return

        # Get the service name for this activity, if
        # we have a bundle on the system capable of handling
        # this activity type
        breg = self._model.get_bundle_registry()
        bundle = breg.find_by_default_type(bundle_id)
        if not bundle:
            logging.error("Couldn't find activity for type %s" % bundle_id)
            return

        act_type = bundle.get_service_name()
        home_model = self._model.get_home()
        home_model.notify_activity_launch(activity_id, act_type)

        handler = ActivityFactory.create(act_type)
        handler.connect('success', self._join_success_cb, activity_ps, activity_id, act_type)
        handler.connect('error', self._join_error_cb, home_model, activity_id, act_type)

    def _find_unique_activity_id(self):
        # create a new unique activity ID
        i = 0
        act_id = None
        while i < 10:
            act_id = sugar.util.unique_id()
            i += 1

            # check through existing activities
            found = False
            for xid, act_host in self._hosts.items():
                if act_host.get_id() == act_id:
                    found = True
                    break
            if found:
                act_id = None
                continue

            # check through network activities
            activities = self._pservice.get_activities()
            for act in activities:
                if act_id == act.get_id():
                    found = True
                    break
            if found:
                act_id = None
                continue

        return act_id

    def _start_success_cb(self, handler, activity, activity_id, activity_type):
        logging.debug("Started activity %s (%s)" % (activity_id, activity_type))
        activity.start(activity_id)

    def _start_error_cb(self, handler, err, home_model, activity_id, activity_type):
        logging.error("Couldn't launch activity %s (%s):\n%s" % (activity_id, activity_type, err))
        home_model.notify_activity_launch_failed(activity_id)

    def start_activity(self, activity_type):
        logging.debug('Shell.start_activity')
        act_id = self._find_unique_activity_id()
        if not act_id:
            logging.error("Couldn't find available activity ID.")
            return None

        home_model = self._model.get_home()
        home_model.notify_activity_launch(act_id, activity_type)

        logging.debug("Shell.start_activity will start %s (%s)" % (act_id, activity_type))
        handler = ActivityFactory.create(activity_type)
        handler.connect('success', self._start_success_cb, act_id, activity_type)
        handler.connect('error', self._start_error_cb, home_model, act_id, activity_type)

        # Zoom to Home for launch feedback
        self.set_zoom_level(sugar.ZOOM_HOME)

    def set_zoom_level(self, level):
        if level == sugar.ZOOM_ACTIVITY:
            self._screen.toggle_showing_desktop(False)
        else:
            self._screen.toggle_showing_desktop(True)
            self._home_window.set_zoom_level(level)

    def get_current_activity(self):
        return self._current_host

    def get_activity(self, activity_id):
        for host in self._hosts.values():
            if host.get_id() == activity_id:
                return host
        return None

    def toggle_chat_visibility(self):
        act = self.get_current_activity()
        if not act:
            return
        is_visible = self._frame.is_visible()
        if act.is_chat_visible():
            frame_was_visible = act.chat_hide()
            if not frame_was_visible:
                self._frame.do_slide_out()
        else:
            if not is_visible:
                self._frame.do_slide_in()
            act.chat_show(is_visible)

    def _frame_deactivated_cb(self, frame):
        self._dbus_helper.FrameDeactivated()

    def _nmc_menu_activated_cb(self):
        self._frame.suppress_frame_slideout(True)

    def _nmc_menu_deactivated_cb(self):
        self._frame.suppress_frame_slideout(False)
