# Copyright (C) 2006-2007, Red Hat, Inc.
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

_SERVICE = "org.laptop.ObjectTypeRegistry"
_PATH = "/org/laptop/ObjectTypeRegistry"
_IFACE = "org.laptop.ObjectTypeRegistry"

def _object_type_from_dict(info_dict):
    if info_dict:
        return ObjectType(info_dict['type_id'],
                          info_dict['name'],
                          info_dict['icon'],
                          info_dict['mime_types'])
    else:
        return None

class ObjectType(object):
    def __init__(self, type_id, name, icon, mime_types):
        self.type_id = type_id
        self.name = name
        self.icon = icon
        self.mime_types = mime_types
        
        self._type_id_to_type = {}
        self._mime_type_to_type = {}

class ObjectTypeRegistry(object):
    def __init__(self):
        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SERVICE, _PATH)
        self._registry = dbus.Interface(bus_object, _IFACE)
        
        # Two caches fo saving some travel across dbus.
        self._type_id_to_type = {}
        self._mime_type_to_type = {}

    def get_type(self, type_id):
        if self._type_id_to_type.has_key(type_id):
            return self._type_id_to_type[type_id]

        type_dict = self._registry.GetType(type_id)
        object_type = _object_type_from_dict(type_dict)

        self._type_id_to_type[type_id] = object_type
        return object_type

    def get_type_for_mime(self, mime_type):
        if self._mime_type_to_type.has_key(mime_type):
            return self._mime_type_to_type[mime_type]

        type_dict = self._registry.GetTypeForMIME(mime_type)
        object_type = _object_type_from_dict(type_dict)

        self._mime_type_to_type[mime_type] = object_type
        return object_type

_registry = None

def get_registry():
    global _registry
    if not _registry:
        _registry = ObjectTypeRegistry()
    return _registry
