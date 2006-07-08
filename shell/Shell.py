import dbus
import gobject

from sugar.LogWriter import LogWriter
from WindowManager import WindowManager
from ConsoleLogger import ConsoleLogger
from ActivityContainer import ActivityContainer
from ActivityRegistry import ActivityRegistry

class Shell(gobject.GObject):
	__gsignals__ = {
		'close': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
				 ([])),
	}

	def __init__(self):
		gobject.GObject.__init__(self)

	def start(self):
		console = ConsoleLogger()

		log_writer = LogWriter("Shell", False)
		log_writer.start()

		registry = ActivityRegistry()
		
		session_bus = dbus.SessionBus()
		service = dbus.service.BusName("com.redhat.Sugar.Shell", bus=session_bus)

		activity_container = ActivityContainer(service, session_bus)

if __name__ == "__main__":
	shell = Shell()
	shell.start()
	try:
		gtk.main()
	except KeyboardInterrupt:
		print 'Ctrl+c pressed, exiting...'
