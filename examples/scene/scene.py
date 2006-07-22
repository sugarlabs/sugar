#!/usr/bin/python

import pygtk
pygtk.require('2.0')
import gtk

from sugar.scene.Stage import Stage
from sugar.scene.Group import Group
from sugar.scene.PixbufActor import PixbufActor

def drawing_area_expose_cb(widget, event, stage):
	stage.render(widget.window)

stage = Stage()

pixbuf = gtk.gdk.pixbuf_new_from_file('background.png')
stage.add(PixbufActor(pixbuf))

icons_group = Group()

i = 1
while i <= 5:
	pixbuf = gtk.gdk.pixbuf_new_from_file('activity%d.png' % i)
	icons_group.add(PixbufActor(pixbuf))
	i += 1

stage.add(icons_group)

window = gtk.Window()
window.set_default_size(640, 480)

drawing_area = gtk.DrawingArea()
drawing_area.connect('expose_event', drawing_area_expose_cb, stage)
window.add(drawing_area)
drawing_area.show()

window.show()

gtk.main()
