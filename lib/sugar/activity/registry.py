# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2007 One Laptop Per Child
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

import logging

import dbus
import gobject

_ACTIVITY_REGISTRY_SERVICE_NAME = 'org.laptop.ActivityRegistry'
_ACTIVITY_REGISTRY_IFACE = 'org.laptop.ActivityRegistry'
_ACTIVITY_REGISTRY_PATH = '/org/laptop/ActivityRegistry'

def _activity_info_from_dict(info_dict):
    if not info_dict:
        return None
    return ActivityInfo(info_dict['name'], info_dict['icon'],
                        info_dict['bundle_id'], info_dict['path'],
                        info_dict['show_launcher'], info_dict['command'])

class ActivityInfo(object):
    def __init__(self, name, icon, bundle_id,
                 path, show_launcher, command):
        self.name = name
        self.icon = icon
        self.bundle_id = bundle_id
        self.path = path
        self.command = command
        self.show_launcher = show_launcher

class ActivityRegistry(gobject.GObject):
    __gsignals__ = {
        'activity-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT])),
        'activity-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT]))
    }
    def __init__(self):
        gobject.GObject.__init__(self)

        bus = dbus.SessionBus()

        # NOTE: We need to follow_name_owner_changes here
        #       because we can not connect to a signal unless 
        #       we follow the changes or we start the service
        #       before we connect.  Starting the service here
        #       causes a major bottleneck during startup
        bus_object = bus.get_object(_ACTIVITY_REGISTRY_SERVICE_NAME,
                                    _ACTIVITY_REGISTRY_PATH,
                                    follow_name_owner_changes = True)
        self._registry = dbus.Interface(bus_object, _ACTIVITY_REGISTRY_IFACE)
        self._registry.connect_to_signal('ActivityAdded', self._activity_added_cb)
        self._registry.connect_to_signal('ActivityRemoved', self._activity_removed_cb)

        # Two caches fo saving some travel across dbus.
        self._service_name_to_activity_info = {}
        self._mime_type_to_activities = {}

    def _convert_info_list(self, info_list):
        result = []

        for info_dict in info_list:
            result.append(_activity_info_from_dict(info_dict))

        return result

    def get_activities(self):
        info_list = self._registry.GetActivities()
        return self._convert_info_list(info_list)

    def _get_activities_cb(self, reply_handler, info_list):
        result = []
        i = 0
        for info_dict in info_list:
            result.append(_activity_info_from_dict(info_dict))

        reply_handler(result)

    def _get_activities_error_cb(self, error_handler, e):
        if error_handler:
            error_handler(e)
        else:
            logging.error('Error getting activities async: %s' % str(e))

    def get_activities_async(self, reply_handler=None, error_handler=None):
        if not reply_handler:
            logging.error('Function get_activities_async called without a reply handler. Can not run.') 
            return

        self._registry.GetActivities(
             reply_handler=lambda info_list:self._get_activities_cb(reply_handler, info_list),
             error_handler=lambda e:self._get_activities_error_cb(error_handler, e))

    def get_activity(self, service_name):
        if self._service_name_to_activity_info.has_key(service_name):
            return self._service_name_to_activity_info[service_name]

        info_dict = self._registry.GetActivity(service_name)
        activity_info = _activity_info_from_dict(info_dict)

        self._service_name_to_activity_info[service_name] = activity_info
        return activity_info

    def find_activity(self, name):
        info_list = self._registry.FindActivity(name)
        return self._convert_info_list(info_list)

    def get_activities_for_type(self, mime_type):
        if self._mime_type_to_activities.has_key(mime_type):
            return self._mime_type_to_activities[mime_type]

        info_list = self._registry.GetActivitiesForType(mime_type)
        activities = self._convert_info_list(info_list)

        self._mime_type_to_activities[mime_type] = activities
        return activities

    def add_bundle(self, bundle_path):
        result = self._registry.AddBundle(bundle_path)
        # Need to invalidate here because get_activity could be called after
        # add_bundle and before we receive activity-added, causing a race.
        self._invalidate_cache()
        return result

    def _activity_added_cb(self, info_dict):
        logging.debug('ActivityRegistry._activity_added_cb: invalidating cache')
        self._invalidate_cache()
        self.emit('activity-added', _activity_info_from_dict(info_dict))

    def _invalidate_cache(self):
        self._service_name_to_activity_info.clear()
        self._mime_type_to_activities.clear()

    def remove_bundle(self, bundle_path):
        return self._registry.RemoveBundle(bundle_path)

    def _activity_removed_cb(self, info_dict):
        logging.debug('ActivityRegistry._activity_removed_cb: flushing caches')
        self._service_name_to_activity_info.clear()
        self._mime_type_to_activities.clear()
        self.emit('activity-removed', _activity_info_from_dict(info_dict))

_registry = None

def get_registry():
    global _registry
    if not _registry:
        _registry = ActivityRegistry()
    return _registry
