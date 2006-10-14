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

_screen_factor = gtk.gdk.screen_width() / 1200.0

_standard_icon_size = int(75.0 * _screen_factor)
_small_icon_size = _standard_icon_size * 0.5
_medium_icon_size = _standard_icon_size * 1.5
_large_icon_size = _standard_icon_size * 2.0
_xlarge_icon_size = _standard_icon_size * 3.0

_space_unit = 9 * _screen_factor
_separator_thickness = 3 * _screen_factor

def _font_description(style, relative_size):
	base_size = 18 * _screen_factor
	return '%s %dpx' % (style, int(base_size * relative_size))

frame_ActivityIcon = {
	'color' : IconColor('white'),
	'size'  : _standard_icon_size
}

frame_ZoomIcon = {
	'size' : _standard_icon_size
}

frame_BuddyIcon = {
	'size' : _standard_icon_size
}

menu = {
	'background_color' : 0x000000FF,
	'spacing'		   : _space_unit,
	'padding'		   : _space_unit
}

menu_Title = {
	'color'	: 0xFFFFFFFF,
	'font'	: _font_description('Bold', 1.2)
}

menu_Separator = {
	'background_color' : 0xFFFFFFFF,
	'box_height'       : _separator_thickness
}

menu_ActionIcon = {
	'size' : _standard_icon_size
}

home_MyIcon = {
	'size' : _xlarge_icon_size
}

ring_ActivityIcon = {
	'size'  : _medium_icon_size
}

friends_MyIcon = {
	'size' : _large_icon_size
}

friends_FriendIcon = {
	'size' : _large_icon_size
}

friends_ActivityIcon = {
	'size' : _standard_icon_size
}
