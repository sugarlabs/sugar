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

	def object_path(self):
		return self._object_path

	def getProperties(self):
		return self._service.getProperties()

	def getPublishedValue(self, key):
		value = self._service.getPublishedValue(key)
