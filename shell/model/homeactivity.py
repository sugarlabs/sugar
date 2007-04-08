# Copyright (C) 2006, Owen Williams.
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

import time
import logging

import gobject
import dbus

from sugar.graphics.xocolor import XoColor
from sugar.presence import PresenceService
from sugar import profile

class HomeActivity(gobject.GObject):
    __gsignals__ = {
        'launch-timeout':          (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([])),
    }

    def __init__(self, bundle, activity_id):
        gobject.GObject.__init__(self)
        self._window = None
        self._xid = None
        self._service = None
        self._activity_id = activity_id
        self._bundle = bundle

        self._launch_time = time.time()
        self._launched = False
        self._launch_timeout_id = gobject.timeout_add(
                                    20000, self._launch_timeout_cb)

        logging.debug("Activity %s (%s) launching..." %
                      (self._activity_id, self.get_type))

    def __del__(self):
        gobject.source_remove(self._launch_timeout_id)
        self._launch_timeout_id = 0

    def _launch_timeout_cb(self, user_data=None):
        logging.debug("Activity %s (%s) launch timed out" %
                      (self._activity_id, self.get_type))
        self._launch_timeout_id = 0
        self.emit('launch-timeout')
        return False

    def set_window(self, window):
        """An activity is 'launched' once we get its window."""
        logging.debug("Activity %s (%s) finished launching" %
                      (self._activity_id, self.get_type))
        self._launched = True
        gobject.source_remove(self._launch_timeout_id)
        self._launch_timeout_id = 0

        if self._window or self._xid:
            raise RuntimeError("Activity is already launched!")
        if not window:
            raise ValueError("window must be valid")

        self._window = window
        self._xid = window.get_xid()

    def set_service(self, service):
        self._service = service

    def get_service(self):
        return self._service

    def get_title(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._window.get_name()

    def get_icon_name(self):
        return self._bundle.get_icon()
    
    def get_icon_color(self):
        pservice = PresenceService.get_instance()
        activity = pservice.get_activity(self._activity_id)
        if activity != None:
            return XoColor(activity.get_color())
        else:
            return profile.get_color()
        
    def get_activity_id(self):
        return self._activity_id

    def get_xid(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._xid

    def get_window(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._window

    def get_type(self):
        return self._bundle.get_service_name()

    def get_shared(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._service.get_shared()

    def get_launch_time(self):
        return self._launch_time

    def get_launched(self):
        return self._launched
