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

from sugar.graphics.xocolor import XoColor
from sugar.presence import PresenceService
from sugar.activity import bundleregistry
from model.BuddyModel import BuddyModel
from model.accesspointmodel import AccessPointModel
from hardware import hardwaremanager

class ActivityModel:
    def __init__(self, activity, bundle, service):
        self._service = service
        self._activity = activity
        self._bundle = bundle

    def get_id(self):
        return self._activity.get_id()
        
    def get_icon_name(self):
        return self._bundle.get_icon()
    
    def get_color(self):
        return XoColor(self._activity.get_color())

    def get_service(self):
        return self._service

class MeshModel(gobject.GObject):
    __gsignals__ = {
        'activity-added':       (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'activity-removed':     (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'buddy-added':          (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'buddy-moved':          (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE,
                                ([gobject.TYPE_PYOBJECT,
                                  gobject.TYPE_PYOBJECT])),
        'buddy-removed':        (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'access-point-added':   (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'access-point-removed': (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._activities = {}
        self._buddies = {}
        self._access_points = {}
        self._bundle_registry = bundleregistry.get_registry()

        self._pservice = PresenceService.get_instance()
        self._pservice.connect("service-appeared",
                               self._service_appeared_cb)
        self._pservice.connect('activity-disappeared',
                               self._activity_disappeared_cb)
        self._pservice.connect("buddy-appeared",
                               self._buddy_appeared_cb)
        self._pservice.connect("buddy-disappeared",
                               self._buddy_disappeared_cb)

        # Add any buddies the PS knows about already
        for buddy in self._pservice.get_buddies():
            self._buddy_appeared_cb(self._pservice, buddy)

        for service in self._pservice.get_services():
            self._check_service(service)

        network_manager = hardwaremanager.get_network_manager()
        if network_manager:
            for nm_device in network_manager.get_devices():
                self._add_network_device(nm_device)
            network_manager.connect('device-added',
                                    self._nm_device_added_cb)

    def _nm_device_added_cb(self, manager, nm_device):
        self._add_network_device(nm_device)

    def _nm_network_appeared_cb(self, nm_device, nm_network):
        self._add_access_point(nm_device, nm_network)

    def _nm_network_disappeared_cb(self, nm_device, nm_network):
        self._remove_access_point(nm_device, nm_network)

    def _add_network_device(self, nm_device):
        for nm_network in nm_device.get_networks():
            self._add_access_point(nm_device, nm_network)

        nm_device.connect('network-appeared',
                          self._nm_network_appeared_cb)
        nm_device.connect('network-disappeared',
                          self._nm_network_disappeared_cb)

    def _add_access_point(self, nm_device, nm_network):
        model = AccessPointModel(nm_device, nm_network)
        self._access_points[nm_network.get_op()] = model
        self.emit('access-point-added', model)

    def _remove_access_point(self, nm_network):
        self.emit('access-point-removed',
                  self._access_points[nm_network.get_op()])
        del self._access_points[nm_network.get_op()]

    def get_access_points(self):
        return self._access_points.values()

    def get_activities(self):
        return self._activities.values()

    def get_buddies(self):
        return self._buddies.values()

    def _buddy_activity_changed_cb(self, buddy, cur_activity):
        if not self._buddies.has_key(buddy.get_name()):
            return
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
        if self._buddies.has_key(model.get_name()):
            del model
            return

        model.connect('current-activity-changed',
                      self._buddy_activity_changed_cb)
        self._buddies[model.get_name()] = model
        self.emit('buddy-added', model)

        cur_activity = buddy.get_current_activity()
        if cur_activity:
            self._notify_buddy_change(model, cur_activity)

    def _buddy_disappeared_cb(self, pservice, buddy):
        if not self._buddies.has_key(buddy.get_name()):
            return
        self.emit('buddy-removed', buddy)
        del self._buddies[buddy.get_name()]

    def _service_appeared_cb(self, pservice, service):
        self._check_service(service)

    def _check_service(self, service):
        service_type = service.get_type()
        bundle = self._bundle_registry.find_by_default_type(service_type)
        if bundle != None:
            activity_id = service.get_activity_id()
            if not self.has_activity(activity_id):
                activity = self._pservice.get_activity(activity_id)
                if activity != None:
                    self.add_activity(bundle, activity, service)

    def has_activity(self, activity_id):
        return self._activities.has_key(activity_id)

    def get_activity(self, activity_id):
        if self.has_activity(activity_id):
            return self._activities[activity_id]
        else:
            return None

    def add_activity(self, bundle, activity, service):
        model = ActivityModel(activity, bundle, service)
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
