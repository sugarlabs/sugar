#!/usr/bin/python
import pygtk
pygtk.require('2.0')

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import gtk
import _sugar

# Main window
window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())

_sugar.startup_browser()

browser = _sugar.Browser()
window.add(browser)
browser.show()

browser.load_url('http://www.google.com')

window.show()

gtk.main()
