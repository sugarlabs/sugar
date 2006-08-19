import os
import logging

import dbus
import dbus.glib
import gtk
import gobject
import wnck

from ActivityRegistry import ActivityRegistry
from home.HomeWindow import HomeWindow
from home.HomeModel import HomeModel
from sugar import env
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

	@dbus.service.method('com.redhat.Sugar.Shell')
	def show_people(self):
		gobject.idle_add(self.__show_people_idle)

	@dbus.service.method('com.redhat.Sugar.Shell')
	def show_console(self):
		gobject.idle_add(self.__show_console_idle)

	@dbus.service.method('com.redhat.Sugar.Shell')
	def zoom_in(self):
		self._shell.zoom_in()

	@dbus.service.method('com.redhat.Sugar.Shell')
	def zoom_out(self):
		self._shell.zoom_out()

class Shell(gobject.GObject):
	ZOOM_MESH = 0
	ZOOM_FRIENDS = 1
	ZOOM_HOME = 2
	ZOOM_ACTIVITY = 3

	__gsignals__ = {
		'activity-opened': (gobject.SIGNAL_RUN_FIRST,
							gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-closed': (gobject.SIGNAL_RUN_FIRST,
							gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self, registry):
		gobject.GObject.__init__(self)

		self._screen = wnck.screen_get_default()
		self._registry = registry
		self._hosts = {}
		self._zoom_level = Shell.ZOOM_HOME

	def start(self):
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Shell', bus=session_bus)
		ShellDbusService(self, bus_name)

		self._owner = ShellOwner()
		self._owner.announce()

		self._chat_controller = ChatController(self)
		self._chat_controller.listen()

		home_model = HomeModel(self._registry)
		self._home_window = HomeWindow(self, home_model)
		self._home_window.show()

		self._screen.connect('window-opened', self.__window_opened_cb)
		self._screen.connect('window-closed', self.__window_closed_cb)

	def set_console(self, console):
		self._console = console

	def __window_opened_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			host = ActivityHost(self, window)
			self._hosts[window.get_xid()] = host
			self.emit('activity-opened', host)

	def __window_closed_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			xid = window.get_xid()

			host = self._hosts[xid]
			self.emit('activity-closed', host)

			del self._hosts[xid]

	def get_activity(self, activity_id):
		for host in self._hosts.values():
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

	def show_console(self):
		self._console.show()

		activity = self.get_current_activity()
		if activity:
			module = self._registry.get_activity(activity.get_default_type())
			self._console.set_page(module.get_id())

	def join_activity(self, service):
		info = self._registry.get_activity(service.get_type())
		
		activity_id = service.get_activity_id()

		activity = self.get_activity(activity_id)
		if activity:
			activity.present()
		else:
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

	def get_registry(self):
		return self._registry

	def get_chat_controller(self):
		return self._chat_controller

	def _set_zoom_level(self, level):
		self._zoom_level = level

		if level == Shell.ZOOM_ACTIVITY:
			self._screen.toggle_showing_desktop(False)
		else:
			self._screen.toggle_showing_desktop(True)

		if level == Shell.ZOOM_HOME:
			self._home_window.set_view(HomeWindow.HOME_VIEW)
		elif level == Shell.ZOOM_FRIENDS:
			self._home_window.set_view(HomeWindow.FRIENDS_VIEW)
		elif level == Shell.ZOOM_MESH:
			self._home_window.set_view(HomeWindow.MESH_VIEW)

	def zoom_in(self):
		level = self._zoom_level + 1
		if level <= Shell.ZOOM_ACTIVITY:
			self._set_zoom_level(level)

	def zoom_out(self):
		level = self._zoom_level - 1
		if level >= Shell.ZOOM_MESH:
			self._set_zoom_level(level)
