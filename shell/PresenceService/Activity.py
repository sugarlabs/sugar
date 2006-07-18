import dbus


class ActivityDBusHelper(dbus.service.Object):
	def __init__(self, parent, bus_name, object_path):
		self._parent = parent
		self._bus_name = bus_name
		self._object_path = object_path
		dbus.service.Object.__init__(self, bus_name, self._object_path)


class Activity(object):
	def __init__(self, bus_name, object_id, activity_id):
		self._activity_id = activity_id

		self._buddies = []
		self._services = {}	# service type -> Service

		self._object_id = object_id
		self._object_path = "/org/laptop/Presence/Activities/%d" % self._object_id
		self._dbus_helper = ActivityDBusHelper(self, bus_name, self._object_path)

	def get_id(self):
		return self._activity_id

	def get_service_of_type(self, stype):
		if self._services.has_key(stype):
			return self._services[stype]
		return None
