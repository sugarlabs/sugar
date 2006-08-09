import sys
import logging

import dbus
import dbus.service
import gobject

from sugar.presence.PresenceService import PresenceService
from sugar.activity import Activity

def get_path(activity_name):
	"""Returns the activity path"""
	return '/' + activity_name.replace('.', '/')

def _get_factory(activity_name):
	"""Returns the activity factory"""
	return activity_name + '.Factory'

class ActivityFactory(dbus.service.Object):
	"""Dbus service that takes care of creating new instances of an activity"""

	def __init__(self, name, activity_class):
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

	@dbus.service.method("com.redhat.Sugar.ActivityFactory")
	def create(self):
		activity = self._class()
		return activity.get_object_path()	

def create(activity_name):
	"""Create a new activity from his name."""
	bus = dbus.SessionBus()

	factory_name = _get_factory(activity_name)
	factory_path = get_path(factory_name) 

	proxy_obj = bus.get_object(factory_name, factory_path)
	factory = dbus.Interface(proxy_obj, "com.redhat.Sugar.ActivityFactory")

	activity_path = factory.create()

	bus = dbus.SessionBus()
	proxy_obj = bus.get_object(Activity.ACTIVITY_SERVICE_NAME, activity_path)
	activity = dbus.Interface(proxy_obj, Activity.ACTIVITY_INTERFACE)

	return activity

def register_factory(name, activity_class):
	"""Register the activity factory."""
	factory = ActivityFactory(name, activity_class)
