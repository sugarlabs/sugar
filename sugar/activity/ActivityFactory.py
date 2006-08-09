import sys
import logging

import dbus
import dbus.service
import gobject

from sugar.presence.PresenceService import PresenceService

ACTIVITY_SERVICE_NAME = "com.redhat.Sugar.Activity"
ACTIVITY_SERVICE_PATH = "/com/redhat/Sugar/Activity"

def get_path(activity_name):
	"""Returns the activity path"""
	return '/' + activity_name.replace('.', '/')

def _get_factory(activity_name):
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
		factory = _get_factory(name)
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

	factory_name = _get_factory(activity_name)
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
