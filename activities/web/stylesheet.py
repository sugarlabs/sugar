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

_screen_factor = gtk.gdk.screen_width() / 1200.0

links_Bubble = {
	'box-width'   : int(250.0 * _screen_factor)
}

links_Text = {
	'color'  : 0x000000FF,
	'font'   : '14px',
	'padding' : 6
}

links_Box = {
	'background_color' : 0x646464ff,
	'padding'          : 4
}
