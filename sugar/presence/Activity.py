# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gobject
import dbus

class Activity(gobject.GObject):

	__gsignals__ = {
		'buddy-joined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'buddy-left': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'service-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'service-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
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
		
		self._id = None
		self._color = None

	def object_path(self):
		return self._object_path

	def _emit_buddy_joined_signal(self, object_path):
		self.emit('buddy-joined', self._ps_new_object(object_path))
		return False

	def _buddy_joined_cb(self, object_path):
		gobject.idle_add(self._emit_buddy_joined_signal, object_path)

	def _emit_buddy_left_signal(self, object_path):
		self.emit('buddy-left', self._ps_new_object(object_path))
		return False

	def _buddy_left_cb(self, object_path):
		gobject.idle_add(self._emit_buddy_left_signal, object_path)

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

	def get_id(self):
		# Cache activity ID, which should never change anyway
		if not self._id:
			self._id = self._activity.getId()
		return self._id

	def get_color(self):
		if not self._color:
			self._color = self._activity.getColor()
		return self._color

	def get_services(self):
		resp = self._activity.getServices()
		servs = []
		for item in resp:
			servs.append(self._ps_new_object(item))
		return servs

	def get_services_of_type(self, stype):
		resp = self._activity.getServicesOfType(stype)
		servs = []
		for item in resp:
			servs.append(self._ps_new_object(item))
		return servs

	def get_joined_buddies(self):
		resp = self._activity.getJoinedBuddies()
		buddies = []
		for item in resp:
			buddies.append(self._ps_new_object(item))
		return buddies

	def owner_has_joined(self):
		# FIXME
		return False
