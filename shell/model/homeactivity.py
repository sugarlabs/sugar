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

from sugar.presence import PresenceService
from sugar.activity import Activity
from sugar import profile

class HomeActivity:
    def __init__(self, registry, window):
        self._window = window

        self._service = Activity.get_service(window.get_xid())
        self._id = self._service.get_id()
        self._type = self._service.get_type()

        info = registry.get_bundle(self._type)
        self._icon_name = info.get_icon()

    def get_title(self):
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

    def get_window(self):
        return self._window

    def get_type(self):
        return self._type

    def get_shared(self):
        return self._service.get_shared()
