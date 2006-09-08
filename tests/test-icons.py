#!/usr/bin/python

import pygtk
pygtk.require('2.0')
import gtk

import goocanvas

from sugar.canvas import IconColor
from sugar.canvas.IconItem import IconItem

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.set_default_size(800, 600)
window.show()

canvas = goocanvas.CanvasView()
canvas.set_size_request(800, 600)
canvas.set_bounds(0, 0, 800, 600)
canvas.show()
window.add(canvas)

canvas_model = goocanvas.CanvasModelSimple()
root = canvas_model.get_root_item()

item = goocanvas.Rect(x=0, y=0, width=800, height=600,
                      line_width=0.0, fill_color="#4f4f4f")
root.add_child(item)

k = 0
while k < 11:
	i = 0
	while i < 16:
		color = IconColor.IconColor()
		icon = IconItem(x=i * 50, y=k * 50, size=46, color=color,
						icon_name='stock-buddy')
		root.add_child(icon)
		i += 1
	k += 1

canvas.set_model(canvas_model)

gtk.main()
