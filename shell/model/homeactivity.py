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

from sugar.graphics.canvasicon import CanvasIcon

class HomeActivity:
    def __init__(self, activity):
        self._icon_name = activity.get_icon_name()
        self._icon_color = activity.get_icon_color()
        self._id = activity.get_id()
        
    def get_icon_name(self):
        return self._icon_name
    
    def get_icon_color(self):
        return self._icon_color
        
    def get_id(self):
        return self._id
