#!/usr/bin/python
import pygtk
pygtk.require('2.0')

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import sys
import random

import gtk
import goocanvas

from sugar.canvas import IconColor
from sugar.canvas.IconItem import IconItem
from sugar.canvas.CanvasView import CanvasView

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = CanvasView()
canvas.show()
window.add(canvas)

canvas_model = goocanvas.CanvasModelSimple()
root = canvas_model.get_root_item()

item = goocanvas.Rect(x=0, y=0, width=1200, height=900,
                      line_width=0.0, fill_color="#4f4f4f")
root.add_child(item)

icon_names = [ 'stock-buddy', 'activity-groupchat', 'activity-web']

k = 0
while k < 12:
	i = 0
	while i < 16:
		color = IconColor.IconColor()
		icon_name_n = int(random.random() * len(icon_names))
		icon = IconItem(x=i * 75, y=k * 75,
						size=75, color=color,
						icon_name=icon_names[icon_name_n])
		root.add_child(icon)
		i += 1
	k += 1

canvas.set_model(canvas_model)

gtk.main()
