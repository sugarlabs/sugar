import os

import dbus
import gtk
import wnck
import gobject

from sugar.LogWriter import LogWriter
from ConsoleLogger import ConsoleLogger
from ActivityRegistry import ActivityRegistry
from HomeWindow import HomeWindow
from sugar import keybindings
from sugar import env
from sugar.activity import Activity
from PeopleWindow import PeopleWindow
from Owner import ShellOwner
from PresenceService import PresenceService

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

class Shell:
	def __init__(self):
		self._screen = wnck.screen_get_default()

	def start(self):
		self._console = ConsoleLogger()
		keybindings.setup_global_keys(self._console.get_window(), self)

		log_writer = LogWriter("Shell", False)
		log_writer.start()

		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Shell', bus=session_bus)
		ShellDbusService(self, bus_name)

		self._ps = PresenceService.PresenceService()
		self._owner = ShellOwner()

		self._registry = ActivityRegistry()
		self._registry.scan_directory(env.get_activities_dir())
		self._registry.scan_directory(os.path.join(env.get_user_dir(), 'activities'))

		self._home_window = HomeWindow(self)
		keybindings.setup_global_keys(self._home_window, self)
		self._home_window.show()

		self._people_windows = {}

	def _toggle_window_visibility(self, window):
		if window.get_property('visible'):
			window.hide()
		else:
			window.show()

	def toggle_home(self):
		self._toggle_window_visibility(self._home_window)

	def get_activity_from_xid(self, xid):
		bus = dbus.SessionBus()
		service = Activity.ACTIVITY_SERVICE_NAME + "%s" % xid
		path = Activity.ACTIVITY_SERVICE_PATH + "/%s" % xid
		proxy_obj = bus.get_object(service, path)

		return dbus.Interface(proxy_obj, 'com.redhat.Sugar.Activity')

	def get_current_activity(self):
		window = self._screen.get_active_window()

		if window and window.is_skip_tasklist():
			window = self._screen.get_previously_active_window()

		if window and not window.is_skip_tasklist():
			return self.get_activity_from_xid(window.get_xid())
		else:
			return None

	def toggle_people(self):
		activity = self.get_current_activity()

		if activity:
			activity_id = activity.get_id()

			if not self._people_windows.has_key(activity_id):
				window = PeopleWindow(self, activity)
				keybindings.setup_global_keys(window, self)
				self._people_windows[activity_id] = window
			else:
				window = self._people_windows[activity_id]

			self._toggle_window_visibility(window)

	def toggle_console(self):
		self._toggle_window_visibility(self._console.get_window())

	def get_registry(self):
		return self._registry
