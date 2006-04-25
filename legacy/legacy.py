#!/usr/bin/python -t
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk, gobject

import sys
import os
import pwd
import gc
import socket
import types
import select
import string
import time

sys.path.append(os.getcwd())
sys.path.append('../shell/example-activity/')
import activity

XEPHYR_PATH = "/usr/bin/Xephyr"
MATCHBOX_PATH = "/usr/bin/matchbox-window-manager"


class LegacyActivity(activity.Activity):

	def __init__(self, args):
		activity.Activity.__init__(self)
		self._act_name = os.path.basename(args[1])
		self._display = 5
		self._args = args[1:]
		self._act_pid = None
		self._matchbox_pid = None
		self._xephyr_pid = None

	def _xephyr_function(self, pid, condition, data=None):
		print "Xephyr: PID: %d, condition: %s" % (pid, condition)

	def _matchbox_function(self, pid, condition, data=None):
		print "WM: PID: %d, condition: %s" % (pid, condition)

	def _act_function(self, pid, condition, data=None):
		print "ACT: PID: %d, condition: %s" % (pid, condition)
		if condition == 0:
			self._act_pid = None
			gtk.main_quit()

	def __key_press_event_cb(self, widget, event):
		print event

	def _start(self):
		args = string.split("%s :%d -ac -parent %d -host-cursor" % (XEPHYR_PATH, self._display, self._plug.get_id()))
		(self._xephyr_pid, a, b, c) = gobject.spawn_async(args, standard_output=sys.stdout, standard_error=sys.stderr)
		self._xephyr_watch = gobject.child_watch_add(self._xephyr_pid, self._xephyr_function)

		envp = ["DISPLAY=:%d" % self._display]
		envp.append("INPUTRC=/etc/inputrc")
		envp.append("XMODIFIERS=@im=SCIM")
		envp.append("GTK_IM_MODULE=scim")
		try:
			envp.append("LANG=%s" % os.environ['LANG'])
		except:
			envp.append("LANG=en_US.UTF-8")

		args = string.split("%s" % MATCHBOX_PATH)
		(self._matchbox_pid, a, b, c) = gobject.spawn_async(args, envp=envp, standard_output=sys.stdout, standard_error=sys.stderr)
		gobject.child_watch_add(self._matchbox_pid, self._matchbox_function)

		args = [os.path.abspath(self._args[0])]
		for arg in self._args[1:]:
			args.append(arg)
		(self._act_pid, a, b, c) = gobject.spawn_async(args, envp=envp, standard_output=sys.stdout, standard_error=sys.stderr)
		gobject.child_watch_add(self._act_pid, self._act_function)

	def activity_on_connected_to_shell(self):
		print "act %d: in activity_on_connected_to_shell" % self.activity_get_id()
		self.activity_set_tab_text(self._act_name)
		self._plug = self.activity_get_gtk_plug()
		self._plug.add_events(gtk.gdk.ALL_EVENTS_MASK)
		self._plug.connect("key-press-event", self.__key_press_event_cb)
		self._plug.show()
		self._start()
		self._plug.grab_focus()

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
		self._plug.grab_focus()

	def cleanup(self):
		try:
			if self._act_pid:
				os.kill(self._act_pid, 9)
				time.sleep(0.2)
			if self._xephyr_pid:
				os.kill(self._xephyr_pid, 9)
				time.sleep(0.2)
			if self._matchbox_pid:
				os.kill(self._matchbox_pid, 9)
				time.sleep(0.2)
		except OSError, e:
			pass

	def run(self):
		try:
			gtk.main()
		except KeyboardInterrupt:
			pass

def main(args):
	app = LegacyActivity(args)
	app.activity_connect_to_shell()
	app.run()
	app.cleanup()

if __name__ == "__main__":
	main(sys.argv)
