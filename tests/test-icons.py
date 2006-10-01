#!/usr/bin/python
import pygtk
pygtk.require('2.0')

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import sys
import random

import gtk
import hippo

from sugar.canvas import IconColor
from sugar.canvas.CanvasIcon import CanvasIcon
from sugar.canvas.CanvasView import CanvasView

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = hippo.Canvas()
canvas.show()
window.add(canvas)

box = hippo.CanvasBox(background_color=0x4f4f4fff)
canvas.set_root(box)

icon_names = [ 'stock-buddy', 'activity-groupchat', 'activity-web']

k = 0
while k < 1:
	i = 0
	while i < 10:
		color = IconColor.IconColor()
		icon_name_n = int(random.random() * len(icon_names))
		icon = CanvasIcon(icon_name=icon_names[icon_name_n],
						  size=75, color=color)
		box.append(icon, 0)
		i += 1
	k += 1

gtk.main()
