#!/usr/bin/python
import random

import pygtk
pygtk.require('2.0')
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

item = goocanvas.Rect(x=0, y=0, width=800, height=600,
                      line_width=0.0, fill_color="#4f4f4f")
root.add_child(item)

icon_names = [ 'stock-buddy', 'activity-groupchat', 'activity-web']

k = 0
while k < 11:
	i = 0
	while i < 15:
		color = IconColor.IconColor()
		icon_name_n = int(random.random() * len(icon_names))
		icon = IconItem(x=i * 50 + 10, y=k * 50 + 10,
						size=46, color=color,
						icon_name=icon_names[icon_name_n])
		root.add_child(icon)
		i += 1
	k += 1

canvas.set_model(canvas_model)

gtk.main()
