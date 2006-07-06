import dbus
import gobject

from sugar.LogWriter import LogWriter
from WindowManager import WindowManager
from ConsoleLogger import ConsoleLogger
from ActivityContainer import ActivityContainer

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

		session_bus = dbus.SessionBus()
		service = dbus.service.BusName("com.redhat.Sugar.Shell", bus=session_bus)

		activity_container = ActivityContainer(service, session_bus)
		activity_container.window.connect('destroy', self.__activity_container_destroy_cb)
		activity_container.show()

		wm = WindowManager(activity_container.window)
		wm.set_width(640, WindowManager.ABSOLUTE)
		wm.set_height(480, WindowManager.ABSOLUTE)
		wm.set_position(WindowManager.CENTER)
		wm.show()
		wm.manage()
		
	def __activity_container_destroy_cb(self, activity_container):
		self.emit('close')

if __name__ == "__main__":
	shell = Shell()
	shell.start()
	try:
		gtk.main()
	except KeyboardInterrupt:
		print 'Ctrl+c pressed, exiting...'
