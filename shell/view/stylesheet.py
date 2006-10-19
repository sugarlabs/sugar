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
