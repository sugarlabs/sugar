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

import gobject
import wnck

from view.home.HomeWindow import HomeWindow
from sugar.presence import PresenceService
from sugar.graphics.popupcontext import PopupContext
from view.ActivityHost import ActivityHost
from sugar.activity import activityfactory
from view.frame.frame import Frame
from view.keyhandler import KeyHandler
from view.hardwaremanager import HardwareManager
from _sugar import AudioManager
import sugar

class Shell(gobject.GObject):
    def __init__(self, model):
        gobject.GObject.__init__(self)

        self._model = model
        self._hosts = {}
        self._screen = wnck.screen_get_default()
        self._current_host = None
        self._screen_rotation = 0

        self._hw_manager = HardwareManager()
        self._audio_manager = AudioManager()

        self._home_window = HomeWindow(self)
        self._home_window.show()
        self.set_zoom_level(sugar.ZOOM_HOME)

        self._key_handler = KeyHandler(self)

        home_model = self._model.get_home()
        home_model.connect('activity-added', self._activity_added_cb)
        home_model.connect('activity-removed', self._activity_removed_cb)
        home_model.connect('active-activity-changed',
                           self._active_activity_changed_cb)

        self._popup_context = PopupContext()

        self._frame = Frame(self)
        self._frame.show_and_hide(3)

        self._pservice = PresenceService.get_instance()

        self.start_activity('org.laptop.JournalActivity')

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

    def get_hardware_manager(self):
        return self._hw_manager

    def get_audio_manager(self):
        return self._audio_manager

    def get_model(self):
        return self._model

    def get_frame(self):
        return self._frame

    def get_popup_context(self):
        return self._popup_context

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

        handler = activityfactory.create(act_type)
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
        handler = activityfactory.create(activity_type)
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
