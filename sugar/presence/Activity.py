import gobject
import dbus, dbus_bindings

class Activity(gobject.GObject):

	__gsignals__ = {
		'BuddyJoined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'BuddyLeft': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'ServiceAppeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'ServiceDisappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT]))
	}

	_PRESENCE_SERVICE = "org.laptop.Presence"
	_ACTIVITY_DBUS_INTERFACE = "org.laptop.Presence.Activity"

	def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
		gobject.GObject.__init__(self)
		self._object_path = object_path
		self._ps_new_object = new_obj_cb
		self._ps_del_object = del_obj_cb
		bobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
		self._activity = dbus.Interface(bobj, self._ACTIVITY_DBUS_INTERFACE)
		self._activity.connect_to_signal('BuddyJoined', self._buddy_joined_cb)
		self._activity.connect_to_signal('BuddyLeft', self._buddy_left_cb)
		self._activity.connect_to_signal('ServiceAppeared', self._service_appeared_cb)
		self._activity.connect_to_signal('ServiceDisappeared', self._service_disappeared_cb)

	def object_path(self):
		return self._object_path

	def _emit_buddy_joined_signal(self, object_path):
		self.emit('BuddyJoined', self._ps_new_object(object_path))
		return False

	def _buddy_joined_cb(self, object_path):
		gobject.idle_add(self._emit_buddy_joined_signal, object_path)

	def _emit_buddy_left_signal(self, object_path):
		self.emit('BuddyLeft', self._ps_new_object(object_path))
		return False

	def _buddy_left_cb(self, object_path):
		gobject.idle_add(self._emit_buddy_left_signal, object_path)

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

	def getId(self):
		return self._activity.getId()

	def getIcon(self):
		return self._buddy.getIcon()

	def getServiceOfType(self, stype):
		try:
			object_path = self._buddy.getServiceOfType(stype)
		except dbus_bindings.DBusException:
			return None
		return self._ps_new_object(object_path)

	def getServices(self):
		resp = self._activity.getServices()
		servs = []
		for item in resp:
			servs.append(self._ps_new_object(item))
		return servs

	def getServicesOfType(self, stype):
		resp = self._activity.getServicesOfType(stype)
		servs = []
		for item in resp:
			servs.append(self._ps_new_object(item))
		return servs

	def getJoinedBuddies(self):
		resp = self._activity.getJoinedBuddies(stype)
		buddies = []
		for item in resp:
			buddies.append(self._ps_new_object(item))
		return buddies

	def ownerHasJoined(self):
		# FIXME
		return False
