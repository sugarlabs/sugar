#!/usr/bin/env python

# Copyright (C) 2006, Eduardo Silva (edsiper@gmail.com).
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

# Console interfaces
import memphis
import logviewer
import terminal

window = gtk.Window()
window.set_title('Developer console')
window.connect("delete-event", gtk.main_quit)

width = gtk.gdk.screen_width() * 95 / 100
height = gtk.gdk.screen_height() * 95 / 100

window.set_default_size(width, height)

window.realize()
window.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

# Memphis interface
memphis_widget = memphis.Interface().widget
memphis_widget.show()

# Log viewer interface
logviewer_widget = logviewer.Interface().widget
logviewer_widget.show()

# Terminal interface
terminal_widget    = terminal.Interface().widget
terminal_widget.show()

# Notebook
notebook = gtk.Notebook()
notebook.append_page(memphis_widget, gtk.Label('Memphis'))
notebook.append_page(logviewer_widget, gtk.Label('Log Viewer'))
notebook.append_page(terminal_widget, gtk.Label('Terminal'))

notebook.show()

window.add(notebook)
window.show()
gtk.main()
