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
from view.dconmanager import DCONManager
from _sugar import KeyGrabber
from _sugar import AudioManager
import sugar

class Shell(gobject.GObject):
    def __init__(self, model):
        gobject.GObject.__init__(self)

        self._model = model
        self._hosts = {}
        self._screen = wnck.screen_get_default()
        self._current_host = None

        style.load_stylesheet(view.stylesheet)

        self._dcon_manager = DCONManager()
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
        self._key_grabber.grab('F13')
        self._key_grabber.grab('F14')
        self._key_grabber.grab('F15')
        self._key_grabber.grab('F16')
        self._key_grabber.grab('F17')
        self._key_grabber.grab('F18')
        self._key_grabber.grab('F19')
        self._key_grabber.grab('F20')
        self._key_grabber.grab('0xDC') # Camera key
        self._key_grabber.grab('0xE0') # Overlay key
        self._key_grabber.grab('0x93') # Frame key
        self._key_grabber.grab('0x7C') # Power key
        self._key_grabber.grab('<alt>Tab')

        # For non-OLPC machines
        self._key_grabber.grab('<shft><alt>F9')
        self._key_grabber.grab('<shft><alt>F10')

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
            self._dcon_manager.set_brightness(0)
        elif key == 'F16':
            self._dcon_manager.set_brightness(3)
        elif key == 'F6':
            self._dcon_manager.set_brightness(5)
        elif key == 'F17':
            self._dcon_manager.set_brightness(7)
        elif key == 'F7':
            self._dcon_manager.set_brightness(9)
        elif key == 'F18':
            self._dcon_manager.set_brightness(12)
        elif key == 'F8':
            self._dcon_manager.set_brightness(15)
        elif key == 'F9':
            self._audio_manager.set_volume(0)
        elif key == 'F19':
            self._audio_manager.set_volume(16)
        elif key == 'F10':
            self._audio_manager.set_volume(32)
        elif key == 'F20':
            self._audio_manager.set_volume(48)
        elif key == 'F11':
            self._audio_manager.set_volume(64)
        elif key == 'F21':
            self._audio_manager.set_volume(80)
        elif key == 'F12':
            self._audio_manager.set_volume(100)
        elif key == '<alt>F5':
            self._dcon_manager.set_mode(DCONManager.COLOR_MODE)
        elif key == '<alt>F8':
            self._dcon_manager.set_mode(DCONManager.BLACK_AND_WHITE_MODE)
        elif key == '<shft><alt>F9':
            self._frame.notify_key_press()
        elif key == '<shft><alt>F10':
            self.toggle_chat_visibility()
        elif key == '0xDC': # Camera key
            self._handle_camera_key()
        elif key == '0xE0': # Overlay key
            self.toggle_chat_visibility()
        elif key == '0x93': # Frame key
            self._frame.notify_key_press()
        elif key == '0x7C': # Power key
            self._shutdown()
        elif key == '<alt>Tab':
            self.set_zoom_level(sugar.ZOOM_HOME)
            box = self._home_window.get_home_box()
            box.grab_and_rotate()

    def _shutdown(self):
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

    def join_activity(self, bundle_id, activity_id):
        pservice = PresenceService.get_instance()

        activity = self.get_activity(activity_id)
        if activity:
            activity.present()
        else:
            activity_ps = pservice.get_activity(activity_id)

            if activity_ps:
                # Get the service name for this activity, if
                # we have a bundle on the system capable of handling
                # this activity type
                breg = self._model.get_bundle_registry()
                bundle = breg.find_by_default_type(bundle_id)
                if bundle:
                    serv_name = bundle.get_service_name()
                    try:
                        activity = ActivityFactory.create(serv_name)
                    except DBusException, e:
                        logging.error("Couldn't launch activity %s:\n%s" % (serv_name, e))
                    else:
                        logging.debug("Joining activity type %s id %s" % (serv_name, activity_id))
                        activity.join(activity_ps.object_path())
                else:
                    logging.error("Couldn't find activity for type %s" % bundle_id)
            else:
                logging.error('Cannot start activity.')

    def start_activity(self, activity_type):
        logging.debug('Shell.start_activity')
        activity = ActivityFactory.create(activity_type)
        activity.start()
        return activity

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
