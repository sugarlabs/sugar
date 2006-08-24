import os
import logging

import dbus
import dbus.service
import gtk
import gobject

from sugar.presence.PresenceService import PresenceService
import sugar.util

ACTIVITY_SERVICE_NAME = "org.laptop.Activity"
ACTIVITY_SERVICE_PATH = "/org/laptop/Activity"
ACTIVITY_INTERFACE = "org.laptop.Activity"

def get_service_name(xid):
	return ACTIVITY_SERVICE_NAME + '%d' % xid

def get_object_path(xid):
	return ACTIVITY_SERVICE_PATH + "/%s" % xid 


class ActivityDbusService(dbus.service.Object):
	"""Base dbus service object that each Activity uses to export dbus methods.
	
	The dbus service is separate from the actual Activity object so that we can
	tightly control what stuff passes through the dbus python bindings."""

	def start(self, pservice, activity):
		self._activity = activity
		self._pservice = pservice		

	@dbus.service.method(ACTIVITY_INTERFACE)
	def share(self):
		"""Called by the shell to request the activity to share itself on the network."""
		self._activity.share()

	@dbus.service.method(ACTIVITY_INTERFACE)
	def join(self, activity_ps_path):
		"""Join the activity specified by its presence service path"""
		activity_ps = self._pservice.get(activity_ps_path)
		return self._activity.join(activity_ps)

	@dbus.service.method(ACTIVITY_INTERFACE)
	def get_id(self):
		"""Get the activity identifier"""
		return self._activity.get_id()

	@dbus.service.method(ACTIVITY_INTERFACE)
	def get_default_type(self):
		"""Get the activity default type"""
		return self._activity.get_default_type()

	@dbus.service.method(ACTIVITY_INTERFACE)
	def set_default_type(self, default_type):
		"""Set the activity default type"""
		self._activity.set_default_type(default_type)

	@dbus.service.method(ACTIVITY_INTERFACE)
	def get_shared(self):
		"""Returns True if the activity is shared on the mesh."""
		return self._activity.get_shared()

	@dbus.service.method(ACTIVITY_INTERFACE,
						 in_signature="sas", out_signature="")
	def execute(self, command, args):
		self._activity.execute(command, args)

class Activity(gtk.Window):
	"""Base Activity class that all other Activities derive from."""

	def __init__(self):
		gtk.Window.__init__(self)

		self.connect('destroy', self.__destroy_cb)

		self._shared = False
		self._activity_id = None
		self._default_type = None
		self._service = None
		self._pservice = PresenceService()

		self.present()
	
		group = gtk.Window()
		group.realize()
		self.window.set_group(group.window)

		bus = dbus.SessionBus()
		xid = self.window.xid
		bus_name = dbus.service.BusName(get_service_name(xid), bus=bus)
		self._bus = ActivityDbusService(bus_name, get_object_path(xid))
		self._bus.start(self._pservice, self)

	def set_default_type(self, default_type):
		"""Set the activity default type.

		It's the type of the main network service which tracks presence
		and provides info about the activity, for example the title."""
		self._default_type = default_type

	def get_default_type(self):
		"""Get the activity default type."""
		return self._default_type

	def get_shared(self):
		"""Returns TRUE if the activity is shared on the mesh."""
		return self._shared

	def get_id(self):
		"""Get the unique activity identifier."""
		if self._activity_id == None:
			self._activity_id = sugar.util.unique_id()
		return self._activity_id

	def join(self, activity_ps):
		"""Join an activity shared on the network."""
		self._shared = True
		self._activity_id = activity_ps.get_id()

		# Publish the default service, it's a copy of
		# one of those we found on the network.
		services = activity_ps.get_services_of_type(self._default_type)
		if len(services) > 0:
			service = services[0]
			addr = service.get_address()
			port = service.get_port()
			properties = { 'title' : service.get_published_value('title') }
			self._service = self._pservice.share_activity(self,
								self._default_type, properties, addr, port)
		else:
			logging.error('Cannot join the activity')

	def share(self):
		"""Share the activity on the network."""
		logging.debug('Share activity %s on the network.' % self.get_id())

		properties = { 'title' : self.get_title() }
		self._service = self._pservice.share_activity(self,
										self._default_type, properties)
		self._shared = True

	def execute(self, command, args):
		"""Execute the given command with args"""
		pass

	def __destroy_cb(self, window):
		if self._bus:
			del self._bus
			self._bus = None
		if self._service:
			self._pservice.unregister_service(self._service)
