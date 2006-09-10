#!/usr/bin/python
import pygtk
pygtk.require('2.0')

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import gtk
import goocanvas

from sugar.canvas.IconColor import IconColor
from sugar.canvas.IconItem import IconItem
from sugar.canvas.CanvasView import CanvasView
from sugar.canvas.GridBox import GridBox
from sugar.canvas.GridModel import GridModel
from sugar.canvas.GridLayout import GridConstraints

def _new_icon_clicked_cb(icon):
	box.remove_child(icon)

def _icon_clicked_cb(icon):
	icon = IconItem(color=IconColor(), icon_name='activity-groupchat')
	icon.connect('clicked', _new_icon_clicked_cb)
	box.add_child(icon, 0)

model = GridModel('#4f4f4f')
layout = model.get_layout()

box = GridBox(GridBox.HORIZONTAL, 5, 6)
layout.set_constraints(box, GridConstraints(0, 0, 5, 1))
model.add(box)

rect = goocanvas.Rect(fill_color='red')
box.add_child(rect)

icon = IconItem(color=IconColor(), icon_name='activity-web')
icon.connect('clicked', _icon_clicked_cb)
box.add_child(icon)

icon = IconItem(color=IconColor(), icon_name='activity-groupchat')
box.add_child(icon)

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = CanvasView()
canvas.show()
window.add(canvas)
canvas.set_model(model.get())

gtk.main()
