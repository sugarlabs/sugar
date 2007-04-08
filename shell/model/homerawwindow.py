# Copyright (C) 2007, Red Hat.
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

from sugar import profile
from sugar import util

class HomeRawWindow(object):
    def __init__(self, window):
        self._activity_id = util.unique_id()
        self._window = window
        self._launch_time = time.time()

    def get_activity_id(self):
        return self._activity_id

    def get_service(self):
        return None

    def get_title(self):
        return self._window.get_name()

    def get_icon_name(self):
        return 'theme:stock-missing'
    
    def get_icon_color(self):
        return profile.get_color()
        
    def get_id(self):
        return None

    def get_xid(self):
        return self._window.get_xid()

    def get_window(self):
        return self._window

    def get_type(self):
        return 'RawXApplication'

    def get_shared(self):
        return False

    def get_launched(self):
        return True

    def get_launch_time(self):
        return self._launch_time
