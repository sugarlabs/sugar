#!/usr/bin/env python

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
from sugar.graphics.spreadbox import SpreadBox
from sugar.graphics.xocolor import XoColor
from sugar.graphics.canvasicon import CanvasIcon

def _create_snowflake(parent, children):
    color = XoColor()
    icon = CanvasIcon(scale=1.0, xo_color=color,
                      icon_name='theme:object-link')
    parent.append(icon, hippo.PACK_FIXED)
    parent.set_root(icon)

    for i in range(0, children):
        color = XoColor()
        icon = CanvasIcon(scale=0.5, xo_color=color,
                          icon_name='theme:stock-buddy')
        parent.append(icon, hippo.PACK_FIXED)

window = gtk.Window()
window.set_default_size(gtk.gdk.screen_width(), gtk.gdk.screen_height())
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = hippo.Canvas()

root_box = SpreadBox(background_color=0xe2e2e2ff)
canvas.set_root(root_box)

box = SnowflakeBox()
snow_flake = _create_snowflake(box, 0)
root_box.set_center_item(box)

box = SnowflakeBox()
snow_flake = _create_snowflake(box, 30)
root_box.add_item(box)

box = SnowflakeBox()
snow_flake = _create_snowflake(box, 15)
root_box.add_item(box)

box = SnowflakeBox()
snow_flake = _create_snowflake(box, 10)
root_box.add_item(box)

box = SnowflakeBox()
snow_flake = _create_snowflake(box, 5)
root_box.add_item(box)

box = SnowflakeBox()
snow_flake = _create_snowflake(box, 2)
root_box.add_item(box)

canvas.show()
window.add(canvas)

gtk.main()
