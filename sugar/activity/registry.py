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

import dbus

_SHELL_SERVICE = "org.laptop.Shell"
_SHELL_PATH = "/org/laptop/Shell"
_REGISTRY_IFACE = "org.laptop.Shell.ActivityRegistry"

def _activity_info_from_dict(info_dict):
    if not info_dict:
        return None
    return ActivityInfo(info_dict['name'], info_dict['icon'],
                        info_dict['service_name'], info_dict['path'])

class ActivityInfo(object):
    def __init__(self, name, icon, service_name, path):
        self.name = name
        self.icon = icon
        self.service_name = service_name
        self.path = path

class ActivityRegistry(object):
    def __init__(self):
        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SHELL_SERVICE, _SHELL_PATH)
        self._registry = dbus.Interface(bus_object, _REGISTRY_IFACE)

    def _convert_info_list(self, info_list):
        result = []

        for info_dict in info_list:
            result.append(_activity_info_from_dict(info_dict))

        return result

    def get_activity(self, service_name):
        info_dict = self._registry.GetActivity(service_name)
        return _activity_info_from_dict(info_dict)

    def find_activity(self, name):
        info_list = self._registry.FindActivity(name)
        return self._convert_info_list(info_list)

    def get_activities_for_type(self, mime_type):
        info_list = self._registry.GetActivitiesForType(mime_type)
        return self._convert_info_list(info_list)

_registry = None

def get_registry():
    global _registry
    if not _registry:
        _registry = ActivityRegistry()
    return _registry
