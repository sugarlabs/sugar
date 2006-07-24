#!/usr/bin/python
import math

import pygtk
pygtk.require('2.0')
import gtk

from sugar.scene.Stage import Stage
from sugar.scene.Group import Group
from sugar.scene.View import View
from sugar.scene.PixbufActor import PixbufActor
from sugar.scene.CircleLayout import CircleLayout
from sugar.scene.Timeline import Timeline

def __next_frame_cb(timeline, frame_num, group):
	angle = math.pi * 2 * frame_num / timeline.get_n_frames()
	group.get_layout().set_angle(angle)
	group.do_layout()

def __completed_cb(timeline, group):
	group.get_layout().set_angle(0)
	group.do_layout()

stage = Stage()

pixbuf = gtk.gdk.pixbuf_new_from_file('background.png')
stage.add(PixbufActor(pixbuf))

icons_group = Group()
icons_group.set_position(100, 100)

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

view = View(stage)
window.add(view)
view.show()

window.show()

timeline = Timeline(stage, 200)
timeline.connect('next-frame', __next_frame_cb, icons_group)
timeline.connect('completed', __completed_cb, icons_group)
timeline.start()

gtk.main()
