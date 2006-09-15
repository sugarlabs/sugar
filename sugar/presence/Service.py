import gobject
import dbus


def __one_dict_differs(dict1, dict2):
	for key, value in dict1.items():
		if not dict2.has_key(key) or dict2[key] != value:
			return True
	return False

def __dicts_differ(dict1, dict2):
	if __one_dict_differs(dict1, dict2):
		return True
	if __one_dict_differs(dict2, dict1):
		return True
	return False

class Service(gobject.GObject):

	_PRESENCE_SERVICE = "org.laptop.Presence"
	_SERVICE_DBUS_INTERFACE = "org.laptop.Presence.Service"

	__gsignals__ = {
		'published-value-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
								   ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
		gobject.GObject.__init__(self)
		self._object_path = object_path
		self._ps_new_object = new_obj_cb
		self._ps_del_object = del_obj_cb
		sobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
		self._service = dbus.Interface(sobj, self._SERVICE_DBUS_INTERFACE)
		self._service.connect_to_signal('PropertyChanged', self.__property_changed_cb)
		self._service.connect_to_signal('PublishedValueChanged',
				self.__published_value_changed_cb)
		self._props = self._service.getProperties()
		self._pubvals = self._service.getPublishedValues()

	def object_path(self):
		return self._object_path

	def __property_changed_cb(self, prop_list):
		self._props = self._service.getProperties()

	def get_published_value(self, key):
		return self._pubvals[key]

	def get_published_values(self):
		self._pubvals = self._service.getPublishedValues()

	def set_published_value(self, key, value):
		if self._pubvals.has_key(key):
			if self._pubvals[key] == value:
				return
		self._pubvals[key] = value
		self._service.setPublishedValue(key, value)

	def set_published_values(self, vals):
		self._service.setPublishedValues(vals)
		self._pubvals = vals

	def __published_value_changed_cb(self, keys):
		oldvals = self._pubvals
		self.get_published_values()
		if __dicts_differ(oldvals, self._pubvals):
			self.emit('published-value-changed', keys)

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
