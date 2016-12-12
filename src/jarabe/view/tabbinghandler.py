# Copyright (C) 2008, Benjamin Berg <benjamin@sipsolutions.net>
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

from gi.repository import GObject
from gi.repository import Gdk

from jarabe.model import shell


_RAISE_DELAY = 250


class TabbingHandler(object):

    def __init__(self, frame, modifier):
        self._frame = frame
        self._tabbing = False
        self._modifier = modifier
        self._timeout = None
        self._keyboard = None
        self._mouse = None

        display = Gdk.Display.get_default()
        device_manager = display.get_device_manager()
        devices = device_manager.list_devices(Gdk.DeviceType.MASTER)
        for device in devices:
            if device.get_source() == Gdk.InputSource.KEYBOARD:
                self._keyboard = device
            if device.get_source() == Gdk.InputSource.MOUSE:
                self._mouse = device

    def _start_tabbing(self, event_time):
        if not self._tabbing:
            logging.debug('Grabing the input.')

            screen = Gdk.Screen.get_default()
            window = screen.get_root_window()

            keyboard_grab_result = self._keyboard.grab(
                window,
                Gdk.GrabOwnership.WINDOW,
                False,
                Gdk.EventMask.KEY_PRESS_MASK |
                Gdk.EventMask.KEY_RELEASE_MASK,
                None,
                event_time)

            mouse_grab_result = self._mouse.grab(
                window,
                Gdk.GrabOwnership.WINDOW,
                False,
                Gdk.EventMask.BUTTON_PRESS_MASK |
                Gdk.EventMask.BUTTON_RELEASE_MASK,
                None,
                event_time)

            self._tabbing = (keyboard_grab_result == Gdk.GrabStatus.SUCCESS and
                             mouse_grab_result == Gdk.GrabStatus.SUCCESS)

            # Now test that the modifier is still active to prevent race
            # conditions. We also test if one of the grabs failed.
            mask = window.get_device_position(self._mouse)[3]
            if not self._tabbing or not (mask & self._modifier):
                logging.debug('Releasing grabs again.')

                # ungrab keyboard/pointer if the grab was successfull.
                if keyboard_grab_result == Gdk.GrabStatus.SUCCESS:
                    self._keyboard.ungrab(event_time)
                if mouse_grab_result == Gdk.GrabStatus.SUCCESS:
                    self._mouse.ungrab(event_time)

                self._tabbing = False
            else:
                self._frame.show()

    def __timeout_cb(self, event_time):
        self._activate_current(event_time)
        self._timeout = None
        return False

    def _start_timeout(self, event_time):
        self._cancel_timeout()
        self._timeout = GObject.timeout_add(
            _RAISE_DELAY,
            lambda: self.__timeout_cb(event_time))

    def _cancel_timeout(self):
        if self._timeout:
            GObject.source_remove(self._timeout)
            self._timeout = None

    def _activate_current(self, event_time):
        home_model = shell.get_model()
        activity = home_model.get_tabbing_activity()
        if activity and activity.get_window():
            activity.get_window().activate(event_time)

    def next_activity(self, event_time):
        if not self._tabbing:
            first_switch = True
            self._start_tabbing(event_time)
        else:
            first_switch = False

        if self._tabbing:
            shell_model = shell.get_model()
            zoom_level = shell_model.zoom_level
            zoom_activity = (zoom_level == shell.ShellModel.ZOOM_ACTIVITY)

            if not zoom_activity and first_switch:
                activity = shell_model.get_active_activity()
            else:
                activity = shell_model.get_tabbing_activity()
                activity = shell_model.get_next_activity(current=activity)

            shell_model.set_tabbing_activity(activity)
            self._start_timeout(event_time)
        else:
            self._activate_next_activity(event_time)

    def previous_activity(self, event_time):
        if not self._tabbing:
            first_switch = True
            self._start_tabbing(event_time)
        else:
            first_switch = False

        if self._tabbing:
            shell_model = shell.get_model()
            zoom_level = shell_model.zoom_level
            zoom_activity = (zoom_level == shell.ShellModel.ZOOM_ACTIVITY)

            if not zoom_activity and first_switch:
                activity = shell_model.get_active_activity()
            else:
                activity = shell_model.get_tabbing_activity()
                activity = shell_model.get_previous_activity(current=activity)

            shell_model.set_tabbing_activity(activity)
            self._start_timeout(event_time)
        else:
            self._activate_next_activity(event_time)

    def _activate_next_activity(self, event_time):
        next_activity = shell.get_model().get_next_activity()
        if next_activity:
            next_activity.get_window().activate(event_time)

    def stop(self, event_time):
        self._keyboard.ungrab(event_time)
        self._mouse.ungrab(event_time)
        self._tabbing = False

        self._frame.hide()

        self._cancel_timeout()
        self._activate_current(event_time)

        home_model = shell.get_model()
        home_model.set_tabbing_activity(None)

    def is_tabbing(self):
        return self._tabbing
