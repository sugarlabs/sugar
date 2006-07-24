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
		'buddy-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'buddy-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'service-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'service-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'activity-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'activity-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
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
		self._objcache = ObjectCache()
		self._bus = dbus.SessionBus()
		self._ps = dbus.Interface(self._bus.get_object(self._PRESENCE_SERVICE,
				self._PRESENCE_OBJECT_PATH), self._PRESENCE_DBUS_INTERFACE)
		self._ps.connect_to_signal('BuddyAppeared', self._buddy_appeared_cb)
		self._ps.connect_to_signal('BuddyDisappeared', self._buddy_disappeared_cb)
		self._ps.connect_to_signal('ServiceAppeared', self._service_appeared_cb)
		self._ps.connect_to_signal('ServiceDisappeared', self._service_disappeared_cb)
		self._ps.connect_to_signal('ActivityAppeared', self._activity_appeared_cb)
		self._ps.connect_to_signal('ActivityDisappeared', self._activity_disappeared_cb)

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
		self.emit('buddy-appeared', self._new_object(object_path))
		return False

	def _buddy_appeared_cb(self, op):
		gobject.idle_add(self._emit_buddy_appeared_signal, op)

	def _emit_buddy_disappeared_signal(self, object_path):
		self.emit('buddy-disappeared', self._new_object(object_path))
		return False

	def _buddy_disappeared_cb(self, object_path):
		gobject.idle_add(self._emit_buddy_disappeared_signal, object_path)

	def _emit_service_appeared_signal(self, object_path):
		self.emit('service-appeared', self._new_object(object_path))
		return False

	def _service_appeared_cb(self, object_path):
		gobject.idle_add(self._emit_service_appeared_signal, object_path)

	def _emit_service_disappeared_signal(self, object_path):
		self.emit('service-disappeared', self._new_object(object_path))
		return False

	def _service_disappeared_cb(self, object_path):
		gobject.idle_add(self._emit_service_disappeared_signal, object_path)

	def _emit_activity_appeared_signal(self, object_path):
		self.emit('activity-appeared', self._new_object(object_path))
		return False

	def _activity_appeared_cb(self, object_path):
		gobject.idle_add(self._emit_activity_appeared_signal, object_path)

	def _emit_activity_disappeared_signal(self, object_path):
		self.emit('activity-disappeared', self._new_object(object_path))
		return False

	def _activity_disappeared_cb(self, object_path):
		gobject.idle_add(self._emit_activity_disappeared_signal, object_path)

	def get_services(self):
		resp = self._ps.getServices()
		servs = []
		for item in resp:
			servs.append(self._new_object(item))
		return servs

	def get_services_of_type(self, stype):
		resp = self._ps.getServicesOfType(stype)
		servs = []
		for item in resp:
			servs.append(self._new_object(item))
		return servs

	def get_activities(self):
		resp = self._ps.getActivities()
		acts = []
		for item in resp:
			acts.append(self._new_object(item))
		return acts

	def get_activity(self, activity_id):
		try:
			act_op = self._ps.getActivity(activity_id)
		except dbus.dbus_bindings.DBusException:
			return None
		return self._new_object(act_op)

	def get_buddies(self):
		resp = self._ps.getBuddies()
		buddies = []
		for item in resp:
			buddies.append(self._new_object(item))
		return buddies

	def get_buddy_by_name(self, name):
		try:
			buddy_op = self._ps.getBuddyByName(name)
		except dbus.dbus_bindings.DBusException:
			return None
		return self._new_object(buddy_op)

	def get_buddy_by_address(self, addr):
		try:
			buddy_op = self._ps.getBuddyByAddress(addr)
		except dbus.dbus_bindings.DBusException:
			return None
		return self._new_object(buddy_op)

	def get_owner(self):
		try:
			owner_op = self._ps.getOwner()
		except dbus.dbus_bindings.DBusException:
			return None
		return self._new_object(owner_op)

	def register_service(self, name, stype, properties={"":""}, address="", port=-1, domain=u"local"):
		serv_op = self._ps.registerService(name, stype, properties, address, port, domain)
		return self._new_object(serv_op)

	def register_service_type(self, stype):
		self._ps.registerServiceType(stype)

	def unregister_service_type(self, stype):
		self._ps.unregisterServiceType(stype)
