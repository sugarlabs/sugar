import gobject
import gtk
import dbus

class Buddy(gobject.GObject):

	__gsignals__ = {
		'icon-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([])),
		'service-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'service-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'joined-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'left-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'property-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT]))
	}

	_PRESENCE_SERVICE = "org.laptop.Presence"
	_BUDDY_DBUS_INTERFACE = "org.laptop.Presence.Buddy"

	def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
		gobject.GObject.__init__(self)
		self._object_path = object_path
		self._ps_new_object = new_obj_cb
		self._ps_del_object = del_obj_cb
		self._properties = {}
		bobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
		self._buddy = dbus.Interface(bobj, self._BUDDY_DBUS_INTERFACE)
		self._buddy.connect_to_signal('IconChanged', self._icon_changed_cb)
		self._buddy.connect_to_signal('ServiceAppeared', self._service_appeared_cb)
		self._buddy.connect_to_signal('ServiceDisappeared', self._service_disappeared_cb)
		self._buddy.connect_to_signal('JoinedActivity', self._joined_activity_cb)
		self._buddy.connect_to_signal('LeftActivity', self._left_activity_cb)
		self._buddy.connect_to_signal('PropertyChanged', self._property_changed_cb)
		self._properties = self._buddy.getProperties()

	def object_path(self):
		return self._object_path

	def _emit_icon_changed_signal(self):
		self.emit('icon-changed')
		return False

	def _icon_changed_cb(self):
		gobject.idle_add(self._emit_icon_changed_signal)

	def _emit_service_appeared_signal(self, object_path):
		self.emit('service-appeared', self._ps_new_object(object_path))
		return False

	def _service_appeared_cb(self, object_path):
		gobject.idle_add(self._emit_service_appeared_signal, object_path)

	def _emit_service_disappeared_signal(self, object_path):
		self.emit('service-disappeared', self._ps_new_object(object_path))
		return False

	def _service_disappeared_cb(self, object_path):
		gobject.idle_add(self._emit_service_disappeared_signal, object_path)

	def _emit_joined_activity_signal(self, object_path):
		self.emit('joined-activity', self._ps_new_object(object_path))
		return False

	def _joined_activity_cb(self, object_path):
		gobject.idle_add(self._emit_joined_activity_signal, object_path)

	def _emit_left_activity_signal(self, object_path):
		self.emit('left-activity', self._ps_new_object(object_path))
		return False

	def _left_activity_cb(self, object_path):
		gobject.idle_add(self._emit_left_activity_signal, object_path)

	def _handle_property_changed_signal(self, prop_list):
		self._properties = self._buddy.getProperties()
		self.emit('property-changed', prop_list)
		return False

	def _property_changed_cb(self, prop_list):
		gobject.idle_add(self._handle_property_changed_signal, prop_list)

	def get_name(self):
		return self._properties['name']

	def get_ip4_address(self):
		return self._properties['ip4_address']

	def is_owner(self):
		return self._properties['owner']

	def get_color(self):
		return self._properties['color']

	def get_icon(self):
		return self._buddy.getIcon()

	def get_icon_pixbuf(self):
		icon = self._buddy.getIcon()
		if icon and len(icon):
			pbl = gtk.gdk.PixbufLoader()
			icon_data = ""
			for item in icon:
				if item < 0:
					item = item + 128
				icon_data = icon_data + chr(item)
			pbl.write(icon_data)
			pbl.close()
			return pbl.get_pixbuf()
		else:
			return None

	def get_service_of_type(self, stype):
		try:
			object_path = self._buddy.getServiceOfType(stype)
		except dbus.exceptions.DBusException:
			return None
		return self._ps_new_object(object_path)

	def get_joined_activities(self):
		try:
			resp = self._buddy.getJoinedActivities()
		except dbus.exceptions.DBusException:
			return []
		acts = []
		for item in resp:
			acts.append(self._ps_new_object(item))
		return acts
