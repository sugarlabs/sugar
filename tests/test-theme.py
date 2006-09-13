#!/usr/bin/python
import pygtk
pygtk.require('2.0')

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import gtk
import goocanvas

from sugar.canvas import IconColor
from sugar.canvas.IconItem import IconItem
from sugar.canvas.CanvasView import CanvasView

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

gtk.main()
