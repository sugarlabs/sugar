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
import gobject
import logging

from sugar.graphics.iconcolor import IconColor
from sugar.presence import PresenceService
from sugar.activity import Activity
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
        self._id = activity_id
        self._type = bundle.get_service_name()
        self._icon_name = bundle.get_icon()

        self._launch_time = time.time()
        self._launched = False
        self._launch_timeout_id = gobject.timeout_add(20000, self._launch_timeout_cb)

        logging.debug("Activity %s (%s) launching..." % (self._id, self._type))

    def __del__(self):
        gobject.source_remove(self._launch_timeout_id)
        self._launch_timeout_id = 0

    def _launch_timeout_cb(self, user_data=None):
        logging.debug("Activity %s (%s) launch timed out" % (self._id, self._type))
        self._launch_timeout_id = 0
        self.emit('launch-timeout')
        return False

    def set_window(self, window):
        """An activity is 'launched' once we get its window."""
        logging.debug("Activity %s (%s) finished launching" % (self._id, self._type))
        self._launched = True
        gobject.source_remove(self._launch_timeout_id)
        self._launch_timeout_id = 0

        if self._window or self._xid:
            raise RuntimeError("Activity is already launched!")
        if not window:
            raise ValueError("window must be valid")

        self._window = window
        self._xid = window.get_xid()
        self._service = Activity.get_service(window.get_xid())

        # verify id and type details
        act_id = self._service.get_id()
        if act_id != self._id:
            raise RuntimeError("Activity's real ID (%s) didn't match expected (%s)." % (act_id, self._id))
        act_type = self._service.get_type()
        if act_type != self._type:
            raise RuntimeError("Activity's real type (%s) didn't match expected (%s)." % (act_type, self._type))

    def get_title(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._window.get_name()

    def get_icon_name(self):
        return self._icon_name
    
    def get_icon_color(self):
        activity = PresenceService.get_instance().get_activity(self._id)
        if activity != None:
            return IconColor(activity.get_color())
        else:
            return profile.get_color()
        
    def get_id(self):
        return self._id

    def get_xid(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._xid

    def get_window(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._window

    def get_type(self):
        return self._type

    def get_shared(self):
        if not self._launched:
            raise RuntimeError("Activity is still launching.")
        return self._service.get_shared()

    def get_launch_time(self):
        return self._launch_time

    def get_launched(self):
        return self._launched
