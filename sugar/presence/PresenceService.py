import dbus, dbus.glib, dbus.dbus_bindings, gobject

import Buddy, Service, Activity

class ObjectCache(object):
	def __init__(self):
		self._cache = {}

	def get(self, object_path):
		try:
			return self._cache[object_path]
		except KeyError:
			return None

	def add(self, obj):
		op = obj.object_path()
		if not self._cache.has_key(op):
			self._cache[op] = obj

	def remove(self, object_path):
		if self._cache.has_key(object_path):
			del self._cache[object_path]

class PresenceService(gobject.GObject):

	__gsignals__ = {
		'BuddyAppeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'BuddyDisappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'ServiceAppeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'ServiceDisappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'ActivityAppeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'ActivityDisappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT]))
	}

	_PRESENCE_SERVICE = "org.laptop.Presence"
	_PRESENCE_DBUS_INTERFACE = "org.laptop.Presence"
	_PRESENCE_OBJECT_PATH = "/org/laptop/Presence"
	_PS_BUDDY_OP = _PRESENCE_OBJECT_PATH + "/Buddies/"
	_PS_SERVICE_OP = _PRESENCE_OBJECT_PATH + "/Services/"
	_PS_ACTIVITY_OP = _PRESENCE_OBJECT_PATH + "/Activities/"
	

	def __init__(self):
		gobject.GObject.__init__(self)
		self._obcache = ObjectCache()
		self._bus = dbus.SessionBus()
		self._ps = dbus.Interface(self._bus.get_object(self._PRESENCE_SERVICE,
				self._PRESENCE_OBJECT_PATH), self._PRESENCE_DBUS_INTERFACE)
		self._ps.connect_to_signal('BuddyAppeared', self._buddy_appeared_cb)
		self._ps.connect_to_signal('BuddyDisappeared', self._buddy_disappeared_cb)

	def _new_object(self, object_path):
		obj = self._objcache.get(object_path)
		if not obj:
			if object_path.startswith(self._PS_SERVICE_OP):
				obj = Service.Service(self._bus, self._new_object,
						self._del_object, object_path)
			elif object_path.startswith(self._PS_BUDDY_OP):
				obj = Buddy.Buddy(self._bus, self._new_object,
						self._del_object, object_path)
			elif object_path.startswith(self._PS_ACTIVITY_OP):
				obj = Activity.Activity(self._bus, self._new_object,
						self._del_object, object_path)
			else:
				raise RuntimeError("Unknown object type")
			self._objcache.add(obj)
		return obj

	def _del_object(self, object_path):
		# FIXME
		pass

	def _emit_buddy_appeared_signal(self, object_path):
		self.emit('BuddyAppeared', self._new_object(object_path))
		return False

	def _buddy_appeared_cb(self, op):
		gobject.idle_add(self._emit_buddy_appeared_signal, op)

	def _emit_buddy_disappeared_signal(self, object_path):
		self.emit('BuddyDisappeared', self._ps_new_object(object_path))
		return False

	def _buddy_disappeared_cb(self, object_path):
		gobject.idle_add(self._emit_buddy_disappeared_signal, object_path)

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

	def _emit_activity_appeared_signal(self, object_path):
		self.emit('ActivityAppeared', self._ps_new_object(object_path))
		return False

	def _activity_appeared_cb(self, object_path):
		gobject.idle_add(self._emit_activity_appeared_signal, object_path)

	def _emit_activity_disappeared_signal(self, object_path):
		self.emit('ActivityDisappeared', self._ps_new_object(object_path))
		return False

	def _activity_disappeared_cb(self, object_path):
		gobject.idle_add(self._emit_activity_disappeared_signal, object_path)

	def getServices(self):
		resp = self._ps.getServices()
		servs = []
		for item in resp:
			servs.append(self._new_object(item))
		return servs

	def getServicesOfType(self, stype):
		resp = self._ps.getServicesOfType(stype)
		servs = []
		for item in resp:
			servs.append(self._new_object(item))
		return servs

	def getActivities(self):
		resp = self._ps.getActivities()
		acts = []
		for item in resp:
			acts.append(self._new_object(item))
		return acts

	def getActivity(self, activity_id):
		try:
			act_op = self._ps.getActivity(activity_id)
		except dbus_bindings.DBusException:
			return None
		return self._new_object(act_op)

	def getBuddies(self):
		resp = self._ps.getBuddies()
		buddies = []
		for item in resp:
			buddies.append(self._new_object(item))
		return buddies

	def getBuddyByName(self, name):
		try:
			buddy_op = self._ps.getBuddyByName(name)
		except dbus_bindings.DBusException:
			return None
		return self._new_object(buddy_op)

	def getBuddyByAddress(self, addr):
		try:
			buddy_op = self._ps.getBuddyByAddress(addr)
		except dbus_bindings.DBusException:
			return None
		return self._new_object(buddy_op)

	def getOwner(self):
		try:
			owner_op = self._ps.getOwner()
		except dbus_bindings.DBusException:
			return None
		return self._new_object(buddy_op)

