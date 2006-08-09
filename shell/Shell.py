import os

import dbus
import dbus.glib
import gtk
import gobject
import wnck

from sugar.LogWriter import LogWriter
from ActivityRegistry import ActivityRegistry
from HomeWindow import HomeWindow
from sugar import env
from ConsoleWindow import ConsoleWindow
from Owner import ShellOwner
from PresenceService import PresenceService
from ActivityHost import ActivityHost
from ChatListener import ChatListener

class ShellDbusService(dbus.service.Object):
	def __init__(self, shell, bus_name):
		dbus.service.Object.__init__(self, bus_name, '/com/redhat/Sugar/Shell')
		self._shell = shell

	def __show_people_idle(self):
		self._shell.show_people()		

	def __show_console_idle(self):
		self._shell.show_console()

	def __log_idle(self, (module_id, message)):
		self._shell.log(module_id, message)

	@dbus.service.method('com.redhat.Sugar.Shell')
	def show_people(self):
		gobject.idle_add(self.__show_people_idle)

	@dbus.service.method('com.redhat.Sugar.Shell')
	def show_console(self):
		gobject.idle_add(self.__show_console_idle)

	@dbus.service.method('com.redhat.Sugar.Shell')
	def log(self, module_id, message):
		gobject.idle_add(self.__log_idle, (module_id, message))

class Shell:
	def __init__(self, registry):
		self._screen = wnck.screen_get_default()
		self._registry = registry

	def start(self):
		log_writer = LogWriter("Shell", False)
		log_writer.start()

		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Shell', bus=session_bus)
		ShellDbusService(self, bus_name)

		self._owner = ShellOwner()
		self._owner.announce()

		chat_listener = ChatListener()
		chat_listener.start()

		self._home_window = HomeWindow(self)
		self._home_window.show()

		self._hosts = {}
		self._console_windows = {}

	def get_current_activity(self):
		window = self._screen.get_active_window()
		if window:
			xid = None

			if window.get_window_type() == wnck.WINDOW_NORMAL:
				xid = window.get_xid()
			elif window.get_window_type() == wnck.WINDOW_DIALOG:
				parent = window.get_transient()
				if not parent is None:
					xid = parent.get_xid()

			if xid != None:
				if self._hosts.has_key(xid):
					return self._hosts[xid]
				else:
					self._hosts[xid] = ActivityHost(self, xid)
					return self._hosts[xid]

		return None

	def show_people(self):
		activity = self.get_current_activity()
		activity.show_people()

	def get_console(self, module_id):
		if not self._console_windows.has_key(module_id):
			dialog = ConsoleWindow()
			self._console_windows[module_id] = dialog
		else:
			dialog = self._console_windows[module_id]
		return dialog

	def show_console(self):
		activity = self.get_current_activity()
		if activity:
			module = self._registry.get_activity(activity.get_default_type())
			console = self.get_console(module.get_id())
			activity.show_dialog(console)
	
	def log(self, module_id, message):
		console = self.get_console(module_id)
		console.log(message)

	def get_registry(self):
		return self._registry
