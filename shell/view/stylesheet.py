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

frame_ActivityIcon = {
    'color' : IconColor('white'),
    'size'  : style.standard_icon_size
}

frame_ShutdownIcon = {
    'size' : style.standard_icon_size
}

frame_OverlayIcon = {
    'size' : style.standard_icon_size
}

frame_ZoomIcon = {
    'size' : style.standard_icon_size
}

frame_BuddyIcon = {
    'size' : style.standard_icon_size
}

home_MyIcon = {
    'size' : style.xlarge_icon_size
}

ring_ActivityIcon = {
    'size'  : style.medium_icon_size
}

friends_MyIcon = {
    'size' : style.large_icon_size
}

friends_FriendIcon = {
    'size' : style.large_icon_size
}

friends_ActivityIcon = {
    'size' : style.standard_icon_size
}

clipboard_bubble = {
    'fill-color'    : 0x646464FF,
    'stroke-color'    : 0x646464FF,
    'progress-color': 0x333333FF,
    'spacing'        : style.space_unit,
    'padding'        : style.space_unit * 1.5
}

clipboard_menu_item_title = {
    'xalign': hippo.ALIGNMENT_CENTER,
    'padding-left': 5,
    'color'     : 0xFFFFFFFF,
    'font'     : style.get_font_description('Bold', 1.2)
}

style.register_stylesheet("clipboard.Bubble", clipboard_bubble)
style.register_stylesheet("clipboard.MenuItem.Title", clipboard_menu_item_title)
