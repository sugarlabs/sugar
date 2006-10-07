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
import hippo

from sugar.graphics.spreadbox import SpreadBox
from sugar.graphics.iconcolor import IconColor
from sugar.graphics.canvasicon import CanvasIcon

def _create_icon():
	color = IconColor()

	icon = CanvasIcon(size=100, color=color,
					  icon_name='stock-buddy')
	box.add(icon)

	return (len(box.get_children()) < 15)

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
window.show()

canvas = hippo.Canvas()

box = SpreadBox(background_color=0xe2e2e2ff)
canvas.set_root(box)

window.add(canvas)
canvas.show()

gobject.timeout_add(500, _create_icon)

gtk.main()
