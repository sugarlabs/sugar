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
import dbus.service

from gettext import gettext as _

_REGISTRY_IFACE = "org.laptop.ObjectTypeRegistry"
_REGISTRY_PATH = "/org/laptop/ObjectTypeRegistry"

class ObjectTypeRegistry(dbus.service.Object):
    def __init__(self):
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_REGISTRY_IFACE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, _REGISTRY_PATH)

        self._types = {}

        self._add_primitive('Text', _('Text'), 'text-x-generic',
                            ['text/plain', 'text/rtf', 'application/pdf',
                              'application/x-pdf', 'text/html',
                              'application/vnd.oasis.opendocument.text',
                              'application/rtf', 'text/rtf'])

        self._add_primitive('Image', _('Image'), 'image-x-generic',
                            ['image/png', 'image/gif', 'image/jpeg'])

        self._add_primitive('Audio', _('Audio'), 'audio-x-generic',
                            ['audio/ogg', 'audio/x-wav', 'audio/wav',
                             'audio/x-vorbis+ogg', 'audio/x-flac+ogg',
                             'audio/x-speex+ogg'])

        self._add_primitive('Video', _('Video'), 'video-x-generic',
                            ['video/ogg', 'application/ogg',
                             'video/x-theora+ogg', 'video/x-ogm+ogg'])

        self._add_primitive('Etoys project', _('Etoys project'),
                            'application-x-squeak-project',
                            ['application/x-squeak-project'])

        self._add_primitive('Link', _('Link'),
                            'text-uri-list',
                            ['text/x-moz-url', 'text/uri-list'])

    def _add_primitive(self, type_id, name, icon, mime_types):
        object_type = {'type_id': type_id, 
                       'name': name,
                       'icon': icon,
                       'mime_types': mime_types}
        self._types[type_id] = object_type

    def _get_type_for_mime(self, mime_type):
        for object_type in self._types.values():
            if mime_type in object_type['mime_types']:
                return object_type
        return None

    @dbus.service.method(_REGISTRY_IFACE,
                         in_signature="s", out_signature="a{sv}")
    def GetType(self, type_id):
        if self._types.has_key(type_id):
            return self._types[type_id]
        else:
            return {}

    @dbus.service.method(_REGISTRY_IFACE,
                         in_signature="s", out_signature="a{sv}")
    def GetTypeForMIME(self, mime_type):
        object_type = self._get_type_for_mime(mime_type)
        if object_type:
            return object_type
        else:
            return {}

_instance = None

def get_instance():
    global _instance
    if not _instance:
        _instance = ObjectTypeRegistry()
    return _instance
