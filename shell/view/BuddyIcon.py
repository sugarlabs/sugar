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

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.palette import Palette
from view.BuddyMenu import BuddyMenu

class BuddyIcon(CanvasIcon):
    def __init__(self, shell, buddy):
        CanvasIcon.__init__(self, icon_name='theme:xo',
                            xo_color=buddy.get_color())

        self._shell = shell
        self._buddy = buddy
        self._buddy.connect('appeared', self._buddy_presence_change_cb)
        self._buddy.connect('disappeared', self._buddy_presence_change_cb)
        self._buddy.connect('color-changed', self._buddy_presence_change_cb)

        palette = BuddyMenu(shell, buddy)
        self.set_palette(palette)

    def _buddy_presence_change_cb(self, buddy, color=None):
        # Update the icon's color when the buddy comes and goes
        self.props.xo_color = buddy.get_color()

