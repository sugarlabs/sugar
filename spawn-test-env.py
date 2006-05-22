#!/usr/bin/python -t

import sys, os
import gtk, gobject
import pwd
import types

def change_user(user):
	try:
		pwrec = pwd.getpwnam(user)
	except KeyError:
		raise Exception("Username '%s' does not exist." % user)
	uid = pwrec[2]
	os.setuid(uid)
	return pwrec[6]

def shell_watch_cb(pid, condition, user_data=None):
	print "In shell watch callback."
	gtk.main_quit()

def main():
	if len(sys.argv) < 1:
		print "Usage: %s <test user>" % sys.argv[0]
	user = sys.argv[1]

	# Start Xephyr
	DISPLAY = ":10"
	args = "/usr/bin/Xephyr -ac -host-cursor -screen 800x600 %s" % DISPLAY
	args = args.split()
	(xephyr_pid, ign1, ign2, ign3) = gobject.spawn_async(args, flags=gobject.SPAWN_STDERR_TO_DEV_NULL | gobject.SPAWN_STDOUT_TO_DEV_NULL)
	print "Xepyhr pid is %d" % xephyr_pid

	shell = change_user(user)

	args = "/bin/dbus-daemon --session --print-address".split()
	(dbus_pid, ign1, dbus_stdout, ign3) = gobject.spawn_async(args, flags=gobject.SPAWN_STDERR_TO_DEV_NULL, standard_output=True)
	dbus_file = os.fdopen(dbus_stdout)
	addr = dbus_file.readline()
	addr = addr.strip()
	print "dbus-daemon pid is %d, session bus address is %s" % (dbus_pid, addr)	
	dbus_file.close()

	os.environ["DISPLAY"] = DISPLAY
	os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr

	args = "/usr/bin/metacity"
	(metacity_pid, ign1, ign2, ign3) = gobject.spawn_async([args], flags=gobject.SPAWN_STDERR_TO_DEV_NULL | gobject.SPAWN_STDOUT_TO_DEV_NULL)

	print "\n"
	(shell_pid, ign1, ign2, ign3) = gobject.spawn_async([shell], flags=gobject.SPAWN_LEAVE_DESCRIPTORS_OPEN | gobject.SPAWN_CHILD_INHERITS_STDIN | gobject.SPAWN_DO_NOT_REAP_CHILD)
	gobject.child_watch_add(shell_pid, shell_watch_cb)
	try:
		gtk.main()
	except KeyboardInterrupt:
		pass

	try:
		os.kill(dbus_pid, 9)
	except OSError:
		pass
	try:
		os.kill(metacity_pid, 9)
	except OSError:
		pass

if __name__ == "__main__":
	main()
