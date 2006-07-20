import gobject
import dbus, dbus_bindings

class Buddy(gobject.GObject):

	__gsignals__ = {
		'IconChanged': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([])),
		'ServiceAppeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'ServiceDisappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'JoinedActivity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'LeftActivity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT]))
	}

	_PRESENCE_SERVICE = "org.laptop.Presence"
	_BUDDY_DBUS_INTERFACE = "org.laptop.Presence.Buddy"

	def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
		gobject.GObject.__init__(self)
		self._object_path = object_path
		self._ps_new_object = new_obj_cb
		self._ps_del_object = del_obj_cb
		bobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
		self._buddy = dbus.Interface(bobj, self._BUDDY_DBUS_INTERFACE)
		self._buddy.connect_to_signal('IconChanged', self._icon_changed_cb)
		self._buddy.connect_to_signal('ServiceAppeared', self._service_appeared_cb)
		self._buddy.connect_to_signal('ServiceDisappeared', self._service_disappeared_cb)
		self._buddy.connect_to_signal('JoinedActivity', self._joined_activity_cb)
		self._buddy.connect_to_signal('LeftActivity', self._left_activity_cb)

	def object_path(self):
		return self._object_path

	def _emit_icon_changed_signal(self):
		self.emit('IconChanged')
		return False

	def _icon_changed_cb(self):
		gobject.idle_add(self._emit_icon_changed_signal)

	def _emit_service_appeared_signal(self, object_path):
		self.emit('ServiceAppeared', self._ps_new_object(object_path))
		return False

	def _service_appeared_cb(self, object_path):
		gobject.idle_add(self._emit_service_appeared_signal, object_path)

	def _emit_service_disappeared_signal(self, object_path):
		self.emit('ServiceDisappeared', self._ps_new_object(object_path))
		return False

	def _service_disappeared_cb(self, object_path):
		gobject.idle_add(self._emit_service_disappeared_signal, object_path)

	def _emit_joined_activity_signal(self, object_path):
		self.emit('JoinedActivity', self._ps_new_object(object_path))
		return False

	def _joined_activity_cb(self, object_path):
		gobject.idle_add(self._emit_joined_activity_signal, object_path)

	def _emit_left_activity_signal(self, object_path):
		self.emit('LeftActivity', self._ps_new_object(object_path))
		return False

	def _left_activity_cb(self, object_path):
		gobject.idle_add(self._emit_left_activity_signal, object_path)

	def getProperties(self):
		return self._buddy.getProperties()

	def getIcon(self):
		return self._buddy.getIcon()

	def getServiceOfType(self, stype):
		try:
			object_path = self._buddy.getServiceOfType(stype)
		except dbus_bindings.DBusException:
			return None
		return self._ps_new_object(object_path)

	def getJoinedActivities(self):
		try:
			resp = self._buddy.getJoinedActivities()
		except dbus_bindings.DBusException:
			return []
		acts = []
		for item in resp:
			acts.append(self._ps_new_object(item))
		return acts
