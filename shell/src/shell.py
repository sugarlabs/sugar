#!/usr/bin/python

import string

import dbus
import dbus.service
import dbus.glib
import gobject
import pygtk
pygtk.require('2.0')
import gtk


activity_counter = 0

class Activity(dbus.service.Object):

    def __init__(self, activity_container, activity_name):
	global activity_counter

	self.activity_container = activity_container

	self.activity_object_name = "/com/redhat/Sugar/Shell/Activity_%d"%activity_counter
	activity_counter += 1
	print "object name = %s"%self.activity_object_name

	dbus.service.Object.__init__(self, activity_container.service, self.activity_object_name)
	self.socket = gtk.Socket()
	self.socket.show()

	tab_name = gtk.Label(activity_name)
	activity_container.notebook.append_page(self.socket, tab_name)


class ActivityContainer(dbus.service.Object):

    def __init__(self, service):

	self.activities = []

	self.service = service

        dbus.service.Object.__init__(self, service, "/com/redhat/Sugar/Shell/ActivityContainer")

	self.window = gtk.Window()
	self.window.set_title("OLPC Sugar")
	self.window.resize(640, 480)

	self.notebook = gtk.Notebook()

	tab_label = gtk.Label("Some tab")
	empty_label = gtk.Label("This left intentionally blank")
	empty_label.show()
	self.notebook.append_page(empty_label, tab_label)

	self.notebook.show()
	self.window.add(self.notebook)

	self.window.connect("destroy", lambda w: gtk.main_quit())
	self.window.show()


    @dbus.service.method("com.redhat.Sugar.Shell.ActivityContainer", \
			 in_signature="s", \
			 out_signature="t", \
			 sender_keyword="sender")
    def add_activity(self, activity_name, sender):
	print "hello world, activity_name = '%s', sender = '%s'"%(activity_name, sender)
	activity = Activity(self, activity_name)
	self.activities.append(activity)
	window_id = activity.socket.get_id()
	print "window_id = %d"%window_id
	return window_id



session_bus = dbus.SessionBus()
service = dbus.service.BusName("com.redhat.Sugar.Shell", bus=session_bus)

activityContainer = ActivityContainer(service)

gtk.main()
