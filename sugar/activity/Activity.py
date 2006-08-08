import sys
import logging

import dbus
import dbus.service
import dbus.glib
import gtk
import gobject

from sugar.presence.PresenceService import PresenceService

# Work around for dbus mutex locking issue
gtk.gdk.threads_init()
dbus.glib.threads_init()

from sugar.LogWriter import LogWriter
import sugar.util

ACTIVITY_SERVICE_NAME = "com.redhat.Sugar.Activity"
ACTIVITY_SERVICE_PATH = "/com/redhat/Sugar/Activity"

def get_path(activity_name):
	"""Returns the activity path"""
	return '/' + activity_name.replace('.', '/')

def get_factory(activity_name):
	"""Returns the activity factory"""
	return activity_name + '.Factory'

class ActivityFactory(dbus.service.Object):
	"""Dbus service that takes care of creating new instances of an activity"""

	def __init__(self, name, activity_class, default_type):
		self._default_type = default_type

		splitted_module = activity_class.rsplit('.', 1)
		module_name = splitted_module[0]
		class_name = splitted_module[1]

		module = __import__(module_name)		
		for comp in module_name.split('.')[1:]:
			module = getattr(module, comp)
		
		self._class = getattr(module, class_name)
	
		bus = dbus.SessionBus()
		factory = get_factory(name)
		bus_name = dbus.service.BusName(factory, bus = bus) 
		dbus.service.Object.__init__(self, bus_name, get_path(factory))

	@dbus.service.method("com.redhat.Sugar.ActivityFactory",
						 in_signature="o", out_signature="")
	def create_with_service(self, service_path):
		pservice = PresenceService()
		service = pservice.get(service_path)

		activity = self._class()
		activity.set_default_type(self._default_type)
		activity.join(service)

	@dbus.service.method("com.redhat.Sugar.ActivityFactory")
	def create(self):
		activity = self._class()
		activity.set_default_type(self._default_type)
		

def create(activity_name, service = None):
	"""Create a new activity from his name."""
	bus = dbus.SessionBus()

	factory_name = get_factory(activity_name)
	factory_path = get_path(factory_name) 

	proxy_obj = bus.get_object(factory_name, factory_path)
	factory = dbus.Interface(proxy_obj, "com.redhat.Sugar.ActivityFactory")

	if service:
		print service.object_path()
		factory.create_with_service(service.object_path())
	else:
		factory.create()		

def register_factory(name, activity_class, default_type=None):
	"""Register the activity factory."""
	factory = ActivityFactory(name, activity_class, default_type)
	gtk.main()

class ActivityDbusService(dbus.service.Object):
	"""Base dbus service object that each Activity uses to export dbus methods.
	
	The dbus service is separate from the actual Activity object so that we can
	tightly control what stuff passes through the dbus python bindings."""

	def __init__(self, xid, activity):
		self._activity = activity
		
		bus = dbus.SessionBus()
		service_name = ACTIVITY_SERVICE_NAME + "%s" % xid
		object_path = ACTIVITY_SERVICE_PATH + "/%s" % xid
		service = dbus.service.BusName(service_name, bus=bus)
		dbus.service.Object.__init__(self, service, object_path)

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def share(self):
		"""Called by the shell to request the activity to share itself on the network."""
		self._activity.share()

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def get_id(self):
		"""Get the activity identifier"""
		return self._activity.get_id()

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def get_default_type(self):
		"""Get the activity default type"""
		return self._activity.get_default_type()

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def get_shared(self):
		"""Returns True if the activity is shared on the mesh."""
		return self._activity.get_shared()

class Activity(gtk.Window):
	"""Base Activity class that all other Activities derive from."""

	def __init__(self, service = None):
		gtk.Window.__init__(self)

		self._shared = False
		self._activity_id = None
		self._default_type = None
		self._pservice = PresenceService()

		self.present()
	
		group = gtk.Window()
		group.realize()
		self.window.set_group(group.window)

		self._dbus_service = ActivityDbusService(self.window.xid, self)

	def __del__(self):
		if self._dbus_service:
			del self._dbus_service
			self._dbus_service = None

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
		properties = { 'title' : self.get_title() }
		self._service = self._pservice.share_activity(self,
													  self._default_type,
													  properties)
		self._shared = True
