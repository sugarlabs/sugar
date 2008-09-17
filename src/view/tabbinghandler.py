# Copyright (C) 2008, Benjamin Berg <benjamin@sipsolutions.net>
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

import view.Shell
from view.frame import frame
from model import shellmodel

_RAISE_DELAY = 250

class TabbingHandler(object):
    def __init__(self, modifier):
        self._tabbing = False
        self._modifier = modifier
        self._timeout = None
        self._frame = frame.get_instance()

    def _start_tabbing(self):
        if not self._tabbing:
            logging.debug('Grabing the input.')

            screen = gtk.gdk.screen_get_default()
            window = screen.get_root_window()     
            keyboard_grab_result = gtk.gdk.keyboard_grab(window)
            pointer_grab_result = gtk.gdk.pointer_grab(window)
            
            self._tabbing = (keyboard_grab_result == gtk.gdk.GRAB_SUCCESS and
                             pointer_grab_result == gtk.gdk.GRAB_SUCCESS)

            # Now test that the modifier is still active to prevent race
            # conditions. We also test if one of the grabs failed.
            mask = window.get_pointer()[2]
            if not self._tabbing or not (mask & self._modifier):
                logging.debug('Releasing grabs again.')

                # ungrab keyboard/pointer if the grab was successfull.
                if keyboard_grab_result == gtk.gdk.GRAB_SUCCESS:
                    gtk.gdk.keyboard_ungrab()
                if pointer_grab_result == gtk.gdk.GRAB_SUCCESS:
                    gtk.gdk.pointer_ungrab()

                self._tabbing = False
            else:
                shell = view.Shell.get_instance()
                
                self._frame.show(self._frame.MODE_NON_INTERACTIVE)

    def __timeout_cb(self):
        self._activate_current()
        self._timeout = None
        return False

    def _start_timeout(self):
        self._cancel_timeout()
        self._timeout = gobject.timeout_add(_RAISE_DELAY, self.__timeout_cb)

    def _cancel_timeout(self):
        if self._timeout:
            gobject.source_remove(self._timeout)
            self._timeout = None

    def _activate_current(self):
        shell_model = shellmodel.get_instance()
        home_model = shell_model.get_home()
        activity = home_model.get_tabbing_activity()
        if activity and activity.get_window():
            activity.get_window().activate(1)

    def next_activity(self):
        if not self._tabbing:
            first_switch = True
            self._start_tabbing()
        else:
            first_switch = False

        if self._tabbing:
            shell_model = shellmodel.get_instance()
            home_model = shell_model.get_home()
            zoom_level = shell_model.get_zoom_level()
            zoom_activity = (zoom_level == shellmodel.ShellModel.ZOOM_ACTIVITY)

            if not zoom_activity and first_switch:
                activity = home_model.get_active_activity()
            else:
                activity = home_model.get_tabbing_activity()
                activity = home_model.get_next_activity(current=activity)

            home_model.set_tabbing_activity(activity)
            self._start_timeout()
        else:
            view.Shell.get_instance().activate_next_activity()

    def previous_activity(self):
        if not self._tabbing:
            first_switch = True
            self._start_tabbing()
        else:
            first_switch = False

        if self._tabbing:
            shell_model = shellmodel.get_instance()
            home_model = shell_model.get_home()
            zoom_level = shell_model.get_zoom_level()
            zoom_activity = (zoom_level == shellmodel.ShellModel.ZOOM_ACTIVITY)

            if not zoom_activity and first_switch:
                activity = home_model.get_active_activity()
            else:
                activity = home_model.get_tabbing_activity()
                activity = home_model.get_previous_activity(current=activity)

            home_model.set_tabbing_activity(activity)
            self._start_timeout()
        else:
            view.Shell.get_instance().activate_next_activity()

    def stop(self):
        gtk.gdk.keyboard_ungrab()
        gtk.gdk.pointer_ungrab()
        self._tabbing = False

        self._frame.hide()

        self._cancel_timeout()
        self._activate_current()

        home_model = shellmodel.get_instance().get_home()
        home_model.set_tabbing_activity(None)

    def is_tabbing(self):
        return self._tabbing

