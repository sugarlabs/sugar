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

import gtk
import hippo

from sugar.graphics.xocolor import XoColor
from sugar.graphics.canvasicon import CanvasIcon
from sugar import env

sys.path.append(env.get_shell_path())

from view.home.snowflakelayout import SnowflakeLayout

def add_snowflake(parent, size):
    box = hippo.CanvasBox()
    parent.append(box)

    layout = SnowflakeLayout()
    box.set_layout(layout)

    icon = CanvasIcon(scale=0.8, xo_color=XoColor(),
                      icon_name='theme:xo')
    layout.add_center(icon)

    for k in range(0, size):
        icon = CanvasIcon(scale=0.4, xo_color=XoColor(),
                          icon_name='theme:xo')
        layout.add(icon)

window = gtk.Window()
window.set_default_size(gtk.gdk.screen_width(), gtk.gdk.screen_height())
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = hippo.Canvas()

root = hippo.CanvasBox(background_color=0xe2e2e2ff)
canvas.set_root(root)

add_snowflake(root, 10)
add_snowflake(root, 20)
add_snowflake(root, 15)
add_snowflake(root, 5)

canvas.show()
window.add(canvas)

gtk.main()
