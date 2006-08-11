import os
import logging

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
from sugar.presence.PresenceService import PresenceService
from ActivityHost import ActivityHost
from ChatController import ChatController
from sugar.activity import ActivityFactory
from sugar.activity import Activity
import sugar.logger

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

class Shell(gobject.GObject):
	__gsignals__ = {
		'activity-closed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([str]))
	}

	def __init__(self, registry):
		gobject.GObject.__init__(self)

		self._screen = wnck.screen_get_default()
		self._registry = registry
		self._hosts = {}
		self._console_windows = {}

	def start(self):
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Shell', bus=session_bus)
		ShellDbusService(self, bus_name)

		sugar.logger.start('Shell', self)

		self._owner = ShellOwner()
		self._owner.announce()

		self._chat_controller = ChatController(self)
		self._chat_controller.listen()

		self._home_window = HomeWindow(self)
		self._home_window.show()

		self._screen.connect('window-opened', self.__window_opened_cb)
		self._screen.connect('window-closed', self.__window_closed_cb)

	def __window_opened_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			self._hosts[window.get_xid()] = ActivityHost(self, window)

	def __window_closed_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			xid = window.get_xid()

			activity = self._hosts[xid]
			self.emit('activity-closed', activity.get_id())

			del self._hosts[xid]

	def get_activity(self, activity_id):
		for host in self._hosts:
			if host.get_id() == activity_id:
				return host
		return None

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
		else:
			console = self.get_console('Shell')
			console.show()

	def join_activity(self, service):
		info = self._registry.get_activity(service.get_type())
		
		activity_id = service.get_activity_id()
		pservice = PresenceService()
		activity_ps = pservice.get_activity(activity_id)

		if activity_ps:
			activity = ActivityFactory.create(info.get_id())
			activity.set_default_type(service.get_type())
			activity.join(activity_ps.object_path())
		else:
			logging.error('Cannot start activity.')

	def start_activity(self, activity_name):
		activity = ActivityFactory.create(activity_name)
		info = self._registry.get_activity_from_id(activity_name)
		if info:
			default_type = info.get_default_type()
			if default_type != None:
				activity.set_default_type(default_type)
				activity.execute('test', [])
			return activity
		else:
			logging.error('No such activity in the directory')
			return None
	
	def log(self, module_id, message):
		console = self.get_console(module_id)
		console.log(message)

	def get_registry(self):
		return self._registry

	def get_chat_controller(self):
		return self._chat_controller
