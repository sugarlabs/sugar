import dbus
import gtk
import gobject

from sugar.LogWriter import LogWriter
from WindowManager import WindowManager
from ConsoleLogger import ConsoleLogger
from ActivityContainer import ActivityContainer
from ActivityRegistry import ActivityRegistry
from HomeWindow import HomeWindow

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

		self._registry = ActivityRegistry()
		
		root_window = gtk.Window()
		root_window.set_title('Sugar')
		wm = WindowManager(root_window)
		wm.set_type(WindowManager.TYPE_ROOT)
		wm.show()		
		
		home_window = HomeWindow(self)
		home_window.set_transient_for(root_window)
		wm = WindowManager(home_window)
		wm.set_type(WindowManager.TYPE_POPUP)
		wm.set_animation(WindowManager.ANIMATION_SLIDE_IN)
		wm.set_geometry(0.1, 0.1, 0.8, 0.8)
		wm.set_key(gtk.keysyms.F2)
		wm.show()

		session_bus = dbus.SessionBus()
		service = dbus.service.BusName("com.redhat.Sugar.Shell", bus=session_bus)
		activity_container = ActivityContainer(service, session_bus)
		
	def get_registry(self):
		return self._registry

if __name__ == "__main__":
	shell = Shell()
	shell.start()
	try:
		gtk.main()
	except KeyboardInterrupt:
		print 'Ctrl+c pressed, exiting...'
