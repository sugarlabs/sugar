import gobject
import dbus, dbus_bindings


class Service(gobject.GObject):

	_PRESENCE_SERVICE = "org.laptop.Presence"
	_SERVICE_DBUS_INTERFACE = "org.laptop.Presence.Service"

	def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
		gobject.GObject.__init__(self)
		self._object_path = object_path
		self._ps_new_object = new_obj_cb
		self._ps_del_object = del_obj_cb
		sobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
		self._service = dbus.Interface(sobj, self._SERVICE_DBUS_INTERFACE)
		self._props = self._service.getProperties()

	def object_path(self):
		return self._object_path

	def getProperties(self):
		return self._props

	def getPublishedValue(self, key):
		value = self._service.getPublishedValue(key)

	def get_name(self):
		return self._props['name']

	def get_type(self):
		return self._props['type']

	def get_domain(self):
		return self._props['domain']

	def get_address(self):
		if self._props.has_key('address'):
			return self._props['address']
		return None

	def get_activity_id(self):
		if self._props.has_key('activityId'):
			return self._props['activityId']
		return None

	def get_port(self):
		if self._props.has_key('port'):
			return self._props['port']
		return None

	def get_source_address(self):
		if self._props.has_key('sourceAddress'):
			return self._props['sourceAddress']
		return None
