import sys

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

ON_SHARE_CB = "share"

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
		activity = self._class(service)

	@dbus.service.method("com.redhat.Sugar.ActivityFactory")
	def create(self):
		activity = self._class(None)
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

	_ALLOWED_CALLBACKS = [ON_SHARE_CB]

	def __init__(self, xid, activity):
		self._activity = activity
		self._callbacks = {}
		for cb in self._ALLOWED_CALLBACKS:
			self._callbacks[cb] = None
		
		bus = dbus.SessionBus()
		service_name = ACTIVITY_SERVICE_NAME + "%s" % xid
		object_path = ACTIVITY_SERVICE_PATH + "/%s" % xid
		service = dbus.service.BusName(service_name, bus=bus)
		dbus.service.Object.__init__(self, service, object_path)

	def register_callback(self, name, callback):
		if name not in self._ALLOWED_CALLBACKS:
			print "ActivityDbusService: bad callback registration request for '%s'" % name
			return
		self._callbacks[name] = callback

	def _call_callback_cb(self, func, *args):
		gobject.idle_add(func, *args)
		return False

	def _call_callback(self, name, *args):
		"""Call our activity object back, but from an idle handler
		to minimize the possibility of stupid activities deadlocking
		in dbus callbacks."""
		if name in self._ALLOWED_CALLBACKS and self._callbacks[name]:
			gobject.idle_add(self._call_callback_cb, self._callbacks[name], *args)

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def share(self):
		"""Called by the shell to request the activity to share itself on the network."""
		self._call_callback(ON_SHARE_CB)

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
		"""Get the activity identifier"""
		return self._activity.get_shared()

class Activity(gtk.Window):
	"""Base Activity class that all other Activities derive from."""

	def __init__(self, service = None):
		gtk.Window.__init__(self)

		if service:
			self._activity_id = service.get_id()
			self._shared = True
		else:
			self._activity_id = sugar.util.unique_id()
			self._shared = False

		self._dbus_service = None
		self._initial_service = None
		self._activity_object = None
		self._default_type = None

		self.connect('realize', self.__realize)
		
		self.present()
	
	def __realize(self, window):
		group = gtk.Window()
		group.realize()
		self.window.set_group(group.window)

		if not self._dbus_service:
			self._register_service()
	
	def _register_service(self):
		self._dbus_service = self._get_new_dbus_service()
		self._dbus_service.register_callback(ON_SHARE_CB, self._internal_on_share_cb)

	def _cleanup(self):
		if self._dbus_service:
			del self._dbus_service
			self._dbus_service = None

	def __del__(self):
		self._cleanup()

	def _get_new_dbus_service(self):
		"""Create and return a new dbus service object for this Activity.
		Allows subclasses to use their own dbus service object if they choose."""
		return ActivityDbusService(self.window.xid, self)

	def set_default_type(self, default_type):
		self._default_type = default_type
		print self._default_type

	def get_default_type(self):
		return self._default_type

	def get_shared(self):
		return self._shared

	def has_focus(self):
		"""Return whether or not this Activity is visible to the user."""
		return self._has_focus

	def _internal_on_share_cb(self):
		"""Callback when the dbus service object tells us the user wishes to share our activity."""
		if not self._shared:
			self._shared = True
		self.share()

	def get_id(self):
		return self._activity_id

	#############################################################
	# Pure Virtual methods that subclasses may/may not implement
	#############################################################

	def share(self):
		"""Called to request the activity to share itself on the network."""
		pass
