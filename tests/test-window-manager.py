#!/usr/bin/python
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
