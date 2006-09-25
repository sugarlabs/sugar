#!/usr/bin/python
import pygtk
pygtk.require('2.0')
import gobject

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import sys
import random

import gtk
import goocanvas

from sugar.canvas.SnowflakeLayout import SnowflakeLayout
from sugar.canvas import IconColor
from sugar.canvas.IconItem import IconItem
from sugar.canvas.CanvasView import CanvasView
from sugar.canvas.Grid import Grid

def _create_snowflake(group, children):
	color = IconColor.IconColor()
	icon = IconItem(size=60, color=color,
					icon_name='activity-groupchat')
	group.add_child(icon)
	layout.set_root(icon)

	for i in range(0, children):
		color = IconColor.IconColor()
		icon = IconItem(size=60, color=color,
						icon_name='stock-buddy')
		group.add_child(icon)
		layout.add_child(icon)

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = CanvasView()
canvas.show()
window.add(canvas)

canvas_model = goocanvas.CanvasModelSimple()
root = canvas_model.get_root_item()

item = goocanvas.Rect(x=0, y=0, width=1200, height=900,
                      line_width=0.0, fill_color='#e2e2e2')
root.add_child(item)

layout = SnowflakeLayout()
group = goocanvas.Group()
snow_flake = _create_snowflake(group, 30)
root.add_child(group)

layout = SnowflakeLayout()
group = goocanvas.Group()
group.translate(500, 500)
_create_snowflake(group, 8)
root.add_child(group)


canvas.set_model(canvas_model)

gtk.main()
