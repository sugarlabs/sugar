import os
import logging

import dbus
import dbus.glib
import gtk
import gobject
import wnck

from home.HomeWindow import HomeWindow
from Owner import ShellOwner
from sugar.presence import PresenceService
from ActivityHost import ActivityHost
from ChatController import ChatController
from sugar.activity import ActivityFactory
from sugar.activity import Activity
from frame.Frame import Frame
from globalkeys import KeyGrabber
import conf
import sugar

class ShellDbusService(dbus.service.Object):
	def __init__(self, shell, bus_name):
		dbus.service.Object.__init__(self, bus_name, '/com/redhat/Sugar/Shell')
		self._shell = shell

	def __show_console_idle(self):
		self._shell.show_console()

	@dbus.service.method('com.redhat.Sugar.Shell')
	def show_console(self):
		gobject.idle_add(self.__show_console_idle)

class Shell(gobject.GObject):
	__gsignals__ = {
		'activity-opened':  (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-changed': (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-closed':  (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gobject.GObject.__init__(self)

		self._screen = wnck.screen_get_default()
		self._hosts = {}
		self._current_window = None

		self._key_grabber = KeyGrabber()
		self._key_grabber.connect('key-pressed', self.__global_key_pressed_cb)
		self._key_grabber.grab('F1')
		self._key_grabber.grab('F2')
		self._key_grabber.grab('F3')
		self._key_grabber.grab('F4')
		self._key_grabber.grab('F5')
		self._key_grabber.grab('F6')

		self._home_window = HomeWindow(self)
		self._home_window.show()
		self.set_zoom_level(sugar.ZOOM_HOME)

		self._screen.connect('window-opened', self.__window_opened_cb)
		self._screen.connect('window-closed', self.__window_closed_cb)
		self._screen.connect('active-window-changed',
							 self.__active_window_changed_cb)

		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Shell', bus=session_bus)
		ShellDbusService(self, bus_name)

		PresenceService.start()
		self._pservice = PresenceService.get_instance()

		self._owner = ShellOwner()
		self._owner.announce()

		self._home_window.set_owner(self._owner)

		self._chat_controller = ChatController(self)
		self._chat_controller.listen()

		self._frame = Frame(self, self._owner)
		self._frame.show_and_hide(10)

	def get_owner(self):
		return self._owner

	def __global_key_pressed_cb(self, grabber, key):
		if key == 'F1':
			self.set_zoom_level(sugar.ZOOM_ACTIVITY)
		elif key == 'F2':
			self.set_zoom_level(sugar.ZOOM_HOME)
		elif key == 'F3':
			self.set_zoom_level(sugar.ZOOM_FRIENDS)
		elif key == 'F4':
			self.set_zoom_level(sugar.ZOOM_MESH)
		elif key == 'F5':
			self._frame.toggle_visibility()
		elif key == 'F6':
			ActivityFactory.create('org.sugar.Terminal')

	def set_console(self, console):
		self._console = console

	def __window_opened_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			host = ActivityHost(self, window)
			self._hosts[window.get_xid()] = host
			self.emit('activity-opened', host)

	def __active_window_changed_cb(self, screen):
		window = screen.get_active_window()
		if window and window.get_window_type() == wnck.WINDOW_NORMAL:
			if self._current_window != window:
				self._current_window = window
				self.emit('activity-changed', self.get_current_activity())

	def __window_closed_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			xid = window.get_xid()
			if self._hosts.has_key(xid):
				host = self._hosts[xid]
				self.emit('activity-closed', host)

				del self._hosts[xid]

	def get_activity(self, activity_id):
		for host in self._hosts.values():
			if host.get_id() == activity_id:
				return host
		return None

	def get_current_activity(self):
		if self._current_window != None:
			xid = self._current_window.get_xid()
			return self._hosts[xid]
		else:
			return None

	def show_console(self):
		self._console.show()

		activity = self.get_current_activity()
		if activity:
			registry = conf.get_activity_registry()
			module = registry.get_activity(activity.get_type())
			self._console.set_page(module.get_id())

	def join_activity(self, bundle_id, activity_id):
		activity = self.get_activity(activity_id)
		if activity:
			activity.present()
		else:
			activity_ps = self._pservice.get_activity(activity_id)

			if activity_ps:
				activity = ActivityFactory.create(bundle_id)
				activity.join(activity_ps.object_path())
			else:
				logging.error('Cannot start activity.')

	def start_activity(self, activity_type):
		activity = ActivityFactory.create(activity_type)
		activity.execute('test', [])
		return activity

	def get_chat_controller(self):
		return self._chat_controller

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_ACTIVITY:
			self._screen.toggle_showing_desktop(False)
		else:
			self._screen.toggle_showing_desktop(True)
			self._home_window.set_zoom_level(level)
