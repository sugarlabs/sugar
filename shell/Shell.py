import dbus
import gtk
import gobject
import wnck

from sugar.LogWriter import LogWriter
from ConsoleLogger import ConsoleLogger
from ActivityRegistry import ActivityRegistry
from HomeWindow import HomeWindow
from sugar import keybindings
from sugar.activity import Activity
from PresenceWindow import PresenceWindow
from sugar.chat.ActivityChat import ActivityChat

class ShellDbusService(dbus.service.Object):
	def __init__(self, shell, bus_name):
		dbus.service.Object.__init__(self, bus_name, '/com/redhat/Sugar/Shell')
		self._shell = shell

	def __toggle_people_idle(self):
		self._shell.toggle_people()		

	@dbus.service.method('com.redhat.Sugar.Shell')
	def toggle_people(self):
		gobject.idle_add(self.__toggle_people_idle)

	@dbus.service.method('com.redhat.Sugar.Shell')
	def toggle_home(self):
		self._shell.toggle_home()	

	@dbus.service.method('com.redhat.Sugar.Shell')
	def toggle_console(self):
		self._shell.toggle_console()	

class Shell(gobject.GObject):
	__gsignals__ = {
		'close': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
				 ([])),
	}

	def __init__(self):
		gobject.GObject.__init__(self)

	def start(self):
		self._console = ConsoleLogger()
		keybindings.setup_global_keys(self._console.get_window(), self)

		log_writer = LogWriter("Shell", False)
		log_writer.start()

		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Shell', bus=session_bus)
		ShellDbusService(self, bus_name)

		self._registry = ActivityRegistry()
		
		self._home_window = HomeWindow(self)
		keybindings.setup_global_keys(self._home_window, self)
		self._home_window.show()

		self._presence_window = PresenceWindow(self)
		self._presence_window.set_skip_taskbar_hint(True)
		keybindings.setup_global_keys(self._presence_window, self)

		self._chat_windows = {}

	def _toggle_window_visibility(self, window):
		if window.get_property('visible'):
			window.hide()
		else:
			window.show()

	def toggle_home(self):
		self._toggle_window_visibility(self._home_window)

	def get_current_activity(self):
		window = wnck.screen_get_default().get_active_window()
		if window and not window.is_skip_tasklist():
			bus = dbus.SessionBus()
			xid = window.get_xid()
			service = Activity.ACTIVITY_SERVICE_NAME + "%s" % xid
			path = Activity.ACTIVITY_SERVICE_PATH + "/%s" % xid
			proxy_obj = bus.get_object(service, path)
			return dbus.Interface(proxy_obj, 'com.redhat.Sugar.Activity')
		else:
			return None

	def toggle_people(self):
		activity = self.get_current_activity()

		if activity:
			activity_id = activity.get_id()

			if not self._chat_windows.has_key(activity_id):
				window = gtk.Window()
				window.set_skip_taskbar_hint(True)
				keybindings.setup_global_keys(window, self)
				chat = ActivityChat(activity)
				window.add(chat)
				chat.show()
				self._chat_windows[activity_id] = window
			self._toggle_window_visibility(self._chat_windows[activity_id])

			self._presence_window.set_activity(activity)
			self._toggle_window_visibility(self._presence_window)
		else:
			self._presence_window.hide()
			for window in self._chat_windows.values():
				window.hide()

	def toggle_console(self):
		self._toggle_window_visibility(self._console.get_window())

	def get_registry(self):
		return self._registry

if __name__ == "__main__":
	shell = Shell()
	shell.start()
	try:
		gtk.main()
	except KeyboardInterrupt:
		print 'Ctrl+c pressed, exiting...'
