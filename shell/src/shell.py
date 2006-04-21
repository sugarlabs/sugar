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

class ActivityHost(dbus.service.Object):

    def __init__(self, activity_container, activity_name):
	global activity_counter

	self.activity_name = activity_name

	self.activity_container = activity_container

	self.activity_id = activity_counter
	activity_counter += 1

	self.dbus_object_name = "/com/redhat/Sugar/Shell/Activities/%d"%self.activity_id
	print "object name = %s"%self.dbus_object_name

	dbus.service.Object.__init__(self, activity_container.service, self.dbus_object_name)
	self.socket = gtk.Socket()
	self.socket.set_data("sugar-activity", self)
	self.socket.show()

	hbox = gtk.HBox();
	self.tab_activity_image = gtk.Image()
	self.tab_activity_image.set_from_stock(gtk.STOCK_CONVERT, gtk.ICON_SIZE_MENU)
	self.tab_activity_image.show()

	self.tab_label = gtk.Label(self.activity_name)
	self.tab_label.show()

	self.tab_close_button = gtk.Button()
	settings = self.tab_close_button.get_settings()
        [w, h] = gtk.icon_size_lookup_for_settings(settings, gtk.ICON_SIZE_MENU)
	self.tab_close_button.set_size_request(w + 2, h + 2)
	close_image = gtk.Image()
	close_image.set_from_stock (gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
	close_image.show()
	self.tab_close_button.add(close_image)
	self.tab_close_button.set_relief(gtk.RELIEF_NONE)
	self.tab_close_button.set_focus_on_click(gtk.FALSE)
	self.tab_close_button.show()
	self.tab_close_button.connect("clicked", self.tab_close_button_clicked)

	hbox.set_spacing(4)
	hbox.pack_start(self.tab_activity_image)
	hbox.pack_start(self.tab_label)
	hbox.pack_start(self.tab_close_button)
	hbox.show()
	
	notebook = self.activity_container.notebook
	index = notebook.append_page(self.socket, hbox)
	#notebook.set_current_page(index)

    def tab_close_button_clicked(self, button):
	self.peer_service.close_from_user()

    @dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="", \
			 out_signature="t")
    def get_host_xembed_id(self):
	window_id = self.socket.get_id()
	print "window_id = %d"%window_id
	return window_id

    @dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="ss", \
			 out_signature="")
    def set_peer_service_name(self, peer_service_name, peer_object_name):
	print "peer_service_name = %s, peer_object_name = %s"%(peer_service_name, peer_object_name)
	self.__peer_service_name = peer_service_name
	self.__peer_object_name = peer_object_name
	self.peer_service = dbus.Interface(self.activity_container.bus.get_object( \
		self.__peer_service_name, self.__peer_object_name), \
					   "com.redhat.Sugar.Activity")

    @dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="s", \
			 out_signature="")
    def set_tab_text(self, text):
	self.tab_label.set_text(text)

    def get_host_activity_id(self):
	return self.activity_id

    def get_object_path(self):
	return self.dbus_object_name


class ActivityContainer(dbus.service.Object):

    def __init__(self, service, bus):

	self.activities = []

	self.bus = bus
	self.service = service

        dbus.service.Object.__init__(self, self.service, "/com/redhat/Sugar/Shell/ActivityContainer")
	bus.add_signal_receiver(self.name_owner_changed, dbus_interface = "org.freedesktop.DBus", signal_name = "NameOwnerChanged")

	self.window = gtk.Window()
	self.window.set_title("OLPC Sugar")
	self.window.resize(640, 480)
	self.notebook = gtk.Notebook()
	tab_label = gtk.Label("My Laptop")
	empty_label = gtk.Label("This activity could launch other activities / be a help page")
	empty_label.show()
	self.notebook.append_page(empty_label, tab_label)
	self.notebook.show()
	self.notebook.connect("switch-page", self.notebook_tab_changed)
	self.window.add(self.notebook)

	self.window.connect("destroy", lambda w: gtk.main_quit())
	self.window.show()

	self.current_activity = None


    def notebook_tab_changed(self, notebook, page, page_number):
	print "in notebook_tab_changed"
	new_activity = notebook.get_nth_page(page_number).get_data("sugar-activity")
	print " Current activity: ", self.current_activity
	print " New activity:     ", new_activity

	if self.current_activity != None:
	    self.current_activity.peer_service.lost_focus()

	self.current_activity = new_activity

	if self.current_activity != None:
	    self.current_activity.peer_service.got_focus()


    def name_owner_changed(self, service_name, old_service_name, new_service_name):
        print "in name_owner_changed: svc=%s oldsvc=%s newsvc=%s"%(service_name, old_service_name, new_service_name)
	for owner, activity in self.activities[:]:
	    if owner == old_service_name:
		self.activities.remove((owner, activity))
	self.__print_activities()


    @dbus.service.method("com.redhat.Sugar.Shell.ActivityContainer", \
			 in_signature="s", \
			 out_signature="i", \
			 sender_keyword="sender")
    def add_activity(self, activity_name, sender):
	print "hello world, activity_name = '%s', sender = '%s'"%(activity_name, sender)
	activity = ActivityHost(self, activity_name)
	self.activities.append((sender, activity))

	self.__print_activities()
	return activity.get_host_activity_id()

    def __print_activities(self):
	print "__print_activities: %d activities registered"%len(self.activities)
	i = 0
	for owner, activity in self.activities:
	    print "  %d: owner=%s activity_object_name=%s"%(i, owner, activity.dbus_object_name)
	    i += 1



session_bus = dbus.SessionBus()
service = dbus.service.BusName("com.redhat.Sugar.Shell", bus=session_bus)

activityContainer = ActivityContainer(service, session_bus)

gtk.main()
