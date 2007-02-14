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
import gtk
import hippo

from sugar.graphics.toolbar import Toolbar
from sugar.graphics.frame import Frame
from sugar.graphics.button import Button
from sugar.graphics.entry import Entry
from sugar.graphics.style import Color

def _entry_activated_cb(entry):
    print "_entry_activated_cb"

def _entry_button_activated_cb(entry, action_id):
    print "_entry_button_activated_cb: " + str(action_id)
    entry.props.text = ''

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
    vbox.append(toolbar)

    button = Button('theme:stock-close')
    toolbar.append(button)

    BUTTON_DELETE = 1
    entry = Entry()
    entry.props.text = 'mec mac'
    entry.add_button('theme:stock-close', BUTTON_DELETE)
    entry.connect('activated', _entry_activated_cb)
    entry.connect('button-activated', _entry_button_activated_cb)
    toolbar.append(entry, hippo.PACK_EXPAND)

    entry = Entry()
    entry.props.text = 'moc muc'
    toolbar.append(entry, hippo.PACK_EXPAND)

    gtk_entry = gtk.Entry()
    gtk_entry.props.has_frame = False
    #gtk_entry.connect("activate", self._entry_activate_cb)

    gtk_entry_widget = hippo.CanvasWidget()
    gtk_entry_widget.props.widget = gtk_entry
    toolbar.append(gtk_entry_widget, hippo.PACK_EXPAND)

gtk.main()
