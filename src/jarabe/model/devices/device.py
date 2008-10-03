#
# Copyright (C) 2007, Red Hat, Inc.
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

import gobject
from jarabe.model import network

from sugar import util

STATE_ACTIVATING = 0
STATE_ACTIVATED  = 1
STATE_INACTIVE   = 2

nm_state_to_state = {
    network.DEVICE_STATE_ACTIVATING : STATE_ACTIVATING,
    network.DEVICE_STATE_ACTIVATED  : STATE_ACTIVATED,
    network.DEVICE_STATE_INACTIVE   : STATE_INACTIVE
}

class Device(gobject.GObject):
    def __init__(self, device_id=None):
        gobject.GObject.__init__(self)
        if device_id:
            self._id = device_id
        else:
            self._id = util.unique_id()

    def get_type(self):
        return 'unknown'        

    def get_id(self):
        return self._id
