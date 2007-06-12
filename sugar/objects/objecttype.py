# Copyright (C) 2007, Red Hat, Inc.
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

_SERVICE = "org.laptop.ObjectTypeRegistry"
_PATH = "/org/laptop/ObjectTypeRegistry"
_IFACE = "org.laptop.ObjectTypeRegistry"

def _object_type_from_dict(info_dict):
    if info_dict:
        return ObjectType(info_dict['type_id'],
                          info_dict['name'],
                          info_dict['icon'])
    else:
        return None

class ObjectType(object):
    def __init__(self, type_id, name, icon):
        self.type_id = type_id
        self.name = name
        self.icon = icon
        self.mime_types = []

class ObjectTypeRegistry(object):
    def __init__(self):
        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SERVICE, _PATH)
        self._registry = dbus.Interface(bus_object, _IFACE)

    def get_type(self, type_id):
        type_dict = self._registry.GetType(type_id)
        return _object_type_from_dict(type_dict)

    def get_type_for_mime(self, mime_type):
        type_dict = self._registry.GetTypeForMIME(mime_type)
        return _object_type_from_dict(type_dict)

_registry = ObjectTypeRegistry()

def get_registry():
    return _registry
