#!/usr/bin/env python

# Copyright (C) 2007, One Laptop Per Child
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
sys.path.insert(0, '/home/tomeu/sugar-jhbuild/source/sugar')

import gtk
import hippo

from sugar.graphics.toolbar import Toolbar
from sugar.graphics.iconbutton import IconButton
from sugar.graphics.button import Button
from sugar.graphics.entry import Entry

def _button_activated_cb(button):
    print "_button_activated_cb"

import os
theme = gtk.icon_theme_get_default()
theme.prepend_search_path(os.path.join(os.path.dirname(__file__), 'data'))

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = hippo.Canvas()
window.add(canvas)
canvas.show()

vbox = hippo.CanvasBox()
canvas.set_root(vbox)

for i in [1, 2]:
    toolbar = Toolbar()
    toolbar.props.box_width = 400
    vbox.append(toolbar)

    icon_button = IconButton(icon_name='theme:stock-close')
    toolbar.append(icon_button)

    button = Button(text='Click me!', icon_name='theme:stock-close')
    button.connect('activated', _button_activated_cb)
    toolbar.append(button)
    
    entry = Entry(text='mec')
    toolbar.append(entry)

gtk.main()
