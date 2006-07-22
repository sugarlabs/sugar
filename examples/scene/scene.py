#!/usr/bin/python
import math

import pygtk
pygtk.require('2.0')
import gtk

from sugar.scene.Stage import Stage
from sugar.scene.Group import Group
from sugar.scene.PixbufActor import PixbufActor
from sugar.scene.CircleLayout import CircleLayout
from sugar.scene.Timeline import Timeline

def __drawing_area_expose_cb(widget, event, stage):
	stage.render(widget.window)

def __next_frame_cb(timeline, frame_num, group):
	angle = math.pi * 2 * frame_num / timeline.get_n_frames()
	group.get_layout().set_angle(angle)
	group.do_layout()

	drawing_area.window.invalidate_rect(None, False)

def __completed_cb(timeline, group):
	group.get_layout().set_angle(0)
	group.do_layout()

	drawing_area.window.invalidate_rect(None, False)

stage = Stage()

pixbuf = gtk.gdk.pixbuf_new_from_file('background.png')
stage.add(PixbufActor(pixbuf))

icons_group = Group()

i = 1
while i <= 5:
	pixbuf = gtk.gdk.pixbuf_new_from_file('activity%d.png' % i)
	icons_group.add(PixbufActor(pixbuf))
	i += 1

layout = CircleLayout(100)
icons_group.set_layout(layout)

stage.add(icons_group)

window = gtk.Window()
window.set_default_size(640, 480)

drawing_area = gtk.DrawingArea()
drawing_area.connect('expose_event', __drawing_area_expose_cb, stage)
window.add(drawing_area)
drawing_area.show()

window.show()

timeline = Timeline(stage, 300)
timeline.connect('next-frame', __next_frame_cb, icons_group)
timeline.connect('completed', __completed_cb, icons_group)
timeline.start()

gtk.main()
