# Copyright (C) 2006-2007 Red Hat, Inc.
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

from sugar.graphics.icon import CanvasIcon
from sugar.graphics.palette import Palette
from sugar.graphics import style

from view.BuddyMenu import BuddyMenu

class BuddyIcon(CanvasIcon):
    def __init__(self, shell, buddy, size=style.STANDARD_ICON_SIZE):
        CanvasIcon.__init__(self, icon_name='computer-xo', size=size)

        self._greyed_out = False
        self._shell = shell
        self._buddy = buddy
        self._buddy.connect('appeared', self._buddy_presence_change_cb)
        self._buddy.connect('disappeared', self._buddy_presence_change_cb)
        self._buddy.connect('color-changed', self._buddy_presence_change_cb)

        palette = BuddyMenu(shell, buddy)
        self.set_palette(palette)

        self._update_color()

    def _buddy_presence_change_cb(self, buddy, color=None):
        # Update the icon's color when the buddy comes and goes
        self._update_color()

    def _update_color(self):
        if self._greyed_out:
            self.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()
            self.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
        else:
            self.props.xo_color = self._buddy.get_color()

    def set_filter(self, query):
        self._greyed_out = (self._buddy.get_nick().lower().find(query) == -1) \
                and not self._buddy.is_owner()
        self._update_color()

