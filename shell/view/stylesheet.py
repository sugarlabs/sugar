# Copyright (C) 2006, Red Hat, Inc.
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

import gtk
import hippo

from sugar.graphics.iconcolor import IconColor
from sugar.graphics import style
from sugar.graphics.grid import Grid

grid = Grid()

frame_ActivityIcon = {
    'color'      : IconColor('white'),
    'box-width'  : grid.dimension(1)
}

frame_OverlayIcon = {
    'box-width'  : grid.dimension(1),
    'box-height' : grid.dimension(1)
}

frame_ZoomIcon = {
    'box-width'  : grid.dimension(1),
    'box-height' : grid.dimension(1)
}

frame_BuddyIcon = {
    'box-width'  : grid.dimension(1),
    'box-height' : grid.dimension(1)
}

home_MyIcon = {
    'scale' : style.xlarge_icon_scale
}

ring_ActivityIcon = {
    'scale' : style.medium_icon_scale
}

friends_MyIcon = {
    'scale' : style.large_icon_scale
}

friends_FriendIcon = {
    'scale' : style.large_icon_scale
}

friends_ActivityIcon = {
    'scale' : style.standard_icon_scale
}

clipboard_Bubble = {
    'fill-color'     : 0x646464FF,
    'stroke-color'   : 0x646464FF,
    'progress-color' : 0x333333FF,
    'spacing'        : style.space_unit,
    'padding'        : style.space_unit * 1.5
}

clipboard_MenuItem_Title = {
    'xalign'      : hippo.ALIGNMENT_CENTER,
    'padding-left': 5,
    'color'       : 0xFFFFFFFF,
    'font'        : style.get_font_description('Bold', 1.2)
}
