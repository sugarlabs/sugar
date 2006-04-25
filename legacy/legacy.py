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

sys.path.append(os.getcwd())
sys.path.append('../shell/example-activity/')
import activity

XEPHYR_PATH = "/usr/bin/Xephyr"

	
def getfd(filespec, readOnly = 0):
	if type(filespec) == types.IntType:
		return (filespec, False)
	if filespec == None:
		filespec = "/dev/null"

	flags = os.O_RDWR | os.O_CREAT
	if (readOnly):
		flags = os.O_RDONLY
	fd = os.open(filespec, flags, 0644)
	return (fd, True)

def exec_with_redirect(cmd, argv, display, stdin=0, stdout=1, stderr=2, setpgrp=True):
	cmd = os.path.abspath(cmd)
	if not os.access (cmd, os.X_OK):
		raise RuntimeError(cmd + " can not be run")

	stdout_opened = False
	stderr_opened = False
	(stdin, stdin_opened) = getfd(stdin)
	if stdout == stderr:
		(stdout, stdout_opened) = getfd(stdout)
		stderr = stdout
	else:
		(stdout, stdout_opened) = getfd(stdout)
		(stderr, stderr_opened) = getfd(stderr)

	childpid = os.fork()
	if (not childpid):
		# Become leader of a new process group if requested
		if setpgrp:
			os.setpgrp()

		if stdin != 0:
			os.dup2(stdin, 0)
			os.close(stdin)
		if stdout != 1:
			os.dup2(stdout, 1)
			if stdout != stderr:
				os.close(stdout)
		if stderr != 2:
			os.dup2(stderr, 2)
			os.close(stderr)

		try:
			if display:
				os.environ['DISPLAY'] = "0:%d" % display
			os.execv(cmd, argv)
		except OSError, e:
			print "Could not execute command '%s'.  Reason: %s" % (cmd, e)
		sys.exit(1)

	# Close any files we may have opened
	if stdin_opened:
		os.close(stdin)
	if stdout_opened:
		os.close(stdout)
	if stderr != stdout and stderr_opened:
		os.close(stderr)

	return childpid

class LegacyActivity(activity.Activity):

	def __init__(self, args):
		activity.Activity.__init__(self)
		self._act_name = os.path.basename(args[1])
		self._display = 5
		self._args = args[1:]

	def _xephyr_function(self, pid, condition, data=None):
		print "Xephyr: PID: %d, condition: %s" % (pid, condition)

	def _act_function(self, pid, condition, data=None):
		print "ACT: PID: %d, condition: %s" % (pid, condition)

	def _start(self):
		cmd = XEPHYR_PATH
		args = []
		args.append(XEPHYR_PATH)
		args.append(":%d" % self._display)
		args.append("-ac")
		args.append("-parent")
		args.append("%d" % self._plug.get_id())
		args.append("-host-cursor")
		self._xephyr_pid = exec_with_redirect(cmd, args, None, None)
		self._xephyr_watch = gobject.child_watch_add(self._xephyr_pid, self._xephyr_function)

		cmd = os.path.abspath(self._args[0])
		args = [cmd]
		for arg in self._args[1:]:
			args.append(arg)		
		self._act_pid = exec_with_redirect(cmd, args, self._display, None)
		self._act_watch = gobject.child_watch_add(self._act_pid, self._act_function)

	def activity_on_connected_to_shell(self):
		print "act %d: in activity_on_connected_to_shell" % self.activity_get_id()
		self.activity_set_tab_text(self._act_name)
		self._plug = self.activity_get_gtk_plug()
		self._plug.show()
		self._start()

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

	def cleanup(self):
		os.kill(self._xephyr_pid, 9)
		os.kill(self._act_pid, 9)

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
