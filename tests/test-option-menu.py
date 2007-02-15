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
from gettext import gettext as _

import gtk
import hippo

from sugar.graphics.toolbar import Toolbar
from sugar.graphics.optionmenu import OptionMenu
from sugar.graphics.button import Button

def _option_menu_changed_cb(option_menu):
    print '_option_menu_activated_cb: %i' % option_menu.props.value

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

toolbar = Toolbar()
vbox.append(toolbar)

button = Button('theme:stock-close')
toolbar.append(button)

OPTION_ANYTHING = 1
OPTION_DRAW = 2
OPTION_WRITE = 3
OPTION_CHAT = 4

option_menu = OptionMenu()
option_menu.add_option(OPTION_ANYTHING, _('Anything'))
option_menu.add_separator()
option_menu.add_option(OPTION_DRAW, _('Draw'), 'theme:stock-close')
option_menu.add_option(OPTION_WRITE, _('Write'))
option_menu.add_option(OPTION_CHAT, _('Chat'))
option_menu.connect('changed', _option_menu_changed_cb)
toolbar.append(option_menu)

gtk.main()
