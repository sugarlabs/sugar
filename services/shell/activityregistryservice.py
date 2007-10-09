# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2007 One Laptop Per Child
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

import dbus
import dbus.service

import bundleregistry

_ACTIVITY_REGISTRY_SERVICE_NAME = 'org.laptop.ActivityRegistry'
_ACTIVITY_REGISTRY_IFACE = 'org.laptop.ActivityRegistry'
_ACTIVITY_REGISTRY_PATH = '/org/laptop/ActivityRegistry'

class ActivityRegistry(dbus.service.Object):
    def __init__(self):
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_ACTIVITY_REGISTRY_SERVICE_NAME, bus=bus)
        dbus.service.Object.__init__(self, bus_name, _ACTIVITY_REGISTRY_PATH)

        bundle_registry = bundleregistry.get_registry()
        bundle_registry.connect('bundle-added', self._bundle_added_cb)
        bundle_registry.connect('bundle-removed', self._bundle_removed_cb)

    @dbus.service.method(_ACTIVITY_REGISTRY_IFACE,
                         in_signature='s', out_signature='b')
    def AddBundle(self, bundle_path):
        '''Register the activity bundle with the global registry 
        
        bundle_path -- path to the root directory of the activity bundle,
            that is, the directory with activity/activity.info as a 
            child of the directory.
        
        The bundleregistry.BundleRegistry is responsible for setting 
        up a set of d-bus service mappings for each available activity.
        '''
        registry = bundleregistry.get_registry()
        return registry.add_bundle(bundle_path)

    @dbus.service.method(_ACTIVITY_REGISTRY_IFACE,
                         in_signature='s', out_signature='b')
    def RemoveBundle(self, bundle_path):
        '''Unregister the activity bundle with the global registry 
        
        bundle_path -- path to the activity bundle root directory
        '''
        registry = bundleregistry.get_registry()
        return registry.remove_bundle(bundle_path)

    @dbus.service.method(_ACTIVITY_REGISTRY_IFACE,
                         in_signature='', out_signature='aa{sv}')
    def GetActivities(self):
        result = []
        registry = bundleregistry.get_registry()
        for bundle in registry:
            result.append(self._bundle_to_dict(bundle))
        return result

    @dbus.service.method(_ACTIVITY_REGISTRY_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetActivity(self, bundle_id):
        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(bundle_id)
        if not bundle:
            return {}
        
        return self._bundle_to_dict(bundle)

    @dbus.service.method(_ACTIVITY_REGISTRY_IFACE,
                         in_signature='s', out_signature='aa{sv}')
    def FindActivity(self, name):
        result = []
        key = name.lower()

        for bundle in bundleregistry.get_registry():
            name = bundle.get_name().lower()
            bundle_id = bundle.get_bundle_id().lower()
            if name.find(key) != -1 or bundle_id.find(key) != -1:
                result.append(self._bundle_to_dict(bundle))

        return result

    @dbus.service.method(_ACTIVITY_REGISTRY_IFACE,
                         in_signature='s', out_signature='aa{sv}')
    def GetActivitiesForType(self, mime_type):
        result = []
        registry = bundleregistry.get_registry()
        for bundle in registry.get_activities_for_type(mime_type):
            result.append(self._bundle_to_dict(bundle))
        return result

    @dbus.service.signal(_ACTIVITY_REGISTRY_IFACE, signature='a{sv}')
    def ActivityAdded(self, activity_info):
        pass

    @dbus.service.signal(_ACTIVITY_REGISTRY_IFACE, signature='a{sv}')
    def ActivityRemoved(self, activity_info):
        pass

    def _bundle_to_dict(self, bundle):
        return {'name': bundle.get_name(),
                'icon': bundle.get_icon(),
                'bundle_id': bundle.get_bundle_id(),
                'path': bundle.get_path(),
                'command': bundle.get_command(),
                'show_launcher': bundle.get_show_launcher()}

    def _bundle_added_cb(self, bundle_registry, bundle):
        self.ActivityAdded(self._bundle_to_dict(bundle))

    def _bundle_removed_cb(self, bundle_registry, bundle):
        self.ActivityRemoved(self._bundle_to_dict(bundle))

_instance = None

def get_instance():
    global _instance
    if not _instance:
        _instance = ActivityRegistry()
    return _instance

