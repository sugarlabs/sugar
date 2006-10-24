#!/usr/bin/python

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

import sys
import random

import pygtk
pygtk.require('2.0')

import gobject
import gtk
import hippo

from sugar.graphics.snowflakebox import SnowflakeBox
from sugar.graphics.iconcolor import IconColor
from sugar.graphics.canvasicon import CanvasIcon

def _create_snowflake(parent, children):
	color = IconColor()
	icon = CanvasIcon(size=40, color=color,
					  icon_name='activity-groupchat')
	parent.append(icon, hippo.PACK_FIXED)
	parent.set_root(icon)

	for i in range(0, children):
		color = IconColor()
		icon = CanvasIcon(size=60, color=color,
						  icon_name='stock-buddy')
		parent.append(icon, hippo.PACK_FIXED)

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = hippo.Canvas()

root_box = hippo.CanvasBox(background_color=0xe2e2e2ff)
canvas.set_root(root_box)

box1 = SnowflakeBox()
snow_flake = _create_snowflake(box1, 30)
root_box.append(box1, hippo.PACK_FIXED)
root_box.move(box1, 0, 0)

box2 = SnowflakeBox()
snow_flake = _create_snowflake(box2, 10)
root_box.append(box2, hippo.PACK_FIXED)
root_box.move(box2, 400, 0)

canvas.show()
window.add(canvas)

gtk.main()
