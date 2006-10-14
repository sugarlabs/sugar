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

import pygtk
pygtk.require('2.0')

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import gtk

def _show_dialog(window):
	dialog = gtk.Dialog(title='No Unviewed Media', 
						parent=window, flags=gtk.DIALOG_MODAL, 
        	            buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
	label = gtk.Label('There is no unviewed media to download.')
	dialog.vbox.pack_start(label, True, True, 0)
	label.show()
	response = dialog.run()
	dialog.hide()
	del dialog

window = gtk.Window()
window.show()

_show_dialog(window)

gtk.main()
