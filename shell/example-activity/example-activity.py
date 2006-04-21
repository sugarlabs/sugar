#!/usr/bin/python
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import string

import gc
import dbus
import dbus.service
import dbus.glib
import gobject
import pygtk
pygtk.require('2.0')
import gtk,sys

import activity

def my_exit():
	sys.exit(0)

def deferred_exit():
	gobject.timeout_add(0, my_exit)

################################################################################

class ExampleActivity(activity.Activity):

	def __init__(self, name):
		self.name = name

	def entry_changed(self, entry):
		self.activity_set_tab_text(entry.get_text())
	
	def activity_on_connected_to_shell(self):
		print "act %d: in activity_on_connected_to_shell"%self.activity_get_id()

		self.activity_set_tab_text(self.name)

		plug = self.activity_get_gtk_plug()
		self.entry = gtk.Entry()
		self.entry.set_text(self.name)
		self.entry.connect("changed", self.entry_changed)
		plug.add(self.entry)
		plug.show_all()

	def activity_on_disconnected_from_shell(self):
		print "act %d: in activity_on_disconnected_from_shell"%self.activity_get_id()
		print "act %d: Shell disappeared..."%self.activity_get_id()

		gc.collect()

	def activity_on_close_from_user(self):
		print "act %d: in activity_on_close_from_user"%self.activity_get_id()
		self.activity_shutdown()

	def activity_on_lost_focus(self):
		print "act %d: in activity_on_lost_focus"%self.activity_get_id()

	def activity_on_got_focus(self):
		print "act %d: in activity_on_got_focus"%self.activity_get_id()

	def __del__(self):
		print "in __del__ for ExampleActivity"


if len(sys.argv) != 2:
	print "usage: example-activity.py <name_of_activity>"
	sys.exit(1)

gc.set_debug(gc.DEBUG_LEAK)

example_activity = ExampleActivity(sys.argv[1])
example_activity.activity_connect_to_shell()
example_activity = None

gtk.main()


