# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gobject

import conf
from sugar.graphics.iconcolor import IconColor
from sugar.presence import PresenceService
from model.BuddyModel import BuddyModel

class ActivityModel:
	def __init__(self, activity, service):
		self._service = service
		self._activity = activity

	def get_id(self):
		return self._activity.get_id()
		
	def get_icon_name(self):
		registry = conf.get_activity_registry()
		info = registry.get_activity_from_type(self._service.get_type())

		return info.get_icon()
	
	def get_color(self):
		return IconColor(self._activity.get_color())

	def get_service(self):
		return self._service

class MeshModel(gobject.GObject):
	__gsignals__ = {
		'activity-added':   (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-removed': (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'buddy-added':      (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'buddy-moved':      (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT,
												  gobject.TYPE_PYOBJECT])),
		'buddy-removed':    (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gobject.GObject.__init__(self)

		self._activities = {}
		self._buddies = {}

		self._pservice = PresenceService.get_instance()
		self._pservice.connect("service-appeared",
							   self._service_appeared_cb)
		self._pservice.connect('activity-disappeared',
							   self._activity_disappeared_cb)
		self._pservice.connect("buddy-appeared",
							   self._buddy_appeared_cb)
		self._pservice.connect("buddy-disappeared",
							   self._buddy_disappeared_cb)

		for service in self._pservice.get_services():
			self._check_service(service)

	def get_activities(self):
		return self._activities

	def get_buddies(self):
		return self._buddies

	def _buddy_activity_changed_cb(self, buddy, cur_activity):
		buddy_model = self._buddies[buddy.get_name()]

		if cur_activity == None:
			self.emit('buddy-moved', buddy_model, None)
		else:
			self._notify_buddy_change(buddy_model, cur_activity)

	def _notify_buddy_change(self, buddy_model, cur_activity):
		if self._activities.has_key(cur_activity.get_id()):
			activity_model = self._activities[cur_activity.get_id()]
			self.emit('buddy-moved', buddy_model, activity_model)

	def _buddy_appeared_cb(self, pservice, buddy):
		model = BuddyModel(buddy=buddy)
		model.connect('current-activity-changed',
					  self._buddy_activity_changed_cb)
		self._buddies[model.get_name()] = model
		self.emit('buddy-added', model)

		cur_activity = buddy.get_current_activity()
		if cur_activity:
			self._notify_buddy_change(model, cur_activity)

	def _buddy_disappeared_cb(self, pservice, buddy):
		self.emit('buddy-removed', buddy)
		del self._buddies[buddy.get_name()]

	def _service_appeared_cb(self, pservice, service):
		self._check_service(service)

	def _check_service(self, service):
		registry = conf.get_activity_registry()
		if registry.get_activity_from_type(service.get_type()) != None:
			activity_id = service.get_activity_id()
			if not self.has_activity(activity_id):
				activity = self._pservice.get_activity(activity_id)
				if activity != None:
					self.add_activity(activity, service)

	def has_activity(self, activity_id):
		return self._activities.has_key(activity_id)

	def add_activity(self, activity, service):
		model = ActivityModel(activity, service)
		self._activities[model.get_id()] = model
		self.emit('activity-added', model)

		for buddy in self._pservice.get_buddies():
			cur_activity = buddy.get_current_activity()
			name = buddy.get_name()
			if cur_activity == activity and self._buddies.has_key(name):
				buddy_model = self._buddies[name]
				self.emit('buddy-moved', buddy_model, model)

	def _activity_disappeared_cb(self, pservice, activity):
		if self._activities.has_key(activity.get_id()):
			activity_model = self._activities[activity.get_id()]
			self.emit('activity-removed', activity_model)
			del self._activities[activity.get_id()]
