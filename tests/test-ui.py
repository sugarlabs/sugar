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

import gtk
import hippo

from sugar.graphics2.window import Window

class TextToolbar(gtk.Toolbar):
    def __init__(self):
        gtk.Toolbar.__init__(self)

        button = gtk.ToolButton()
        button.set_icon_name('text-format-bold')
        self.insert(button, -1)
        button.show()

window = Window()
window.connect("destroy", lambda w: gtk.main_quit())

text_toolbar = TextToolbar()
window.toolbox.add_toolbar('Text', text_toolbar)
text_toolbar.show()

window.canvas.set_root(hippo.CanvasBox(background_color=0))

window.show()

gtk.main()
