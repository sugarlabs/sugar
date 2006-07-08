import dbus

class ActivityInfo:
	def __init__(self, name, title):
		self._name = name
		self._title = title
	
	def get_name(self):
		return self._name

	def get_title(self):
		return self._title

class ActivityRegistry(dbus.service.Object):
	"""Dbus service that tracks the available activities"""

	def __init__(self):
		self._activities = []
	
		bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.ActivityRegistry', bus = bus) 
		dbus.service.Object.__init__(self, bus_name, '/com/redhat/Sugar/ActivityRegistry')

	@dbus.service.method("com.redhat.Sugar.ActivityRegistry")
	def add(self, name, title):
		self._activities.append(ActivityInfo(name, title))	

	def list_activities(self):
		return self._activities
