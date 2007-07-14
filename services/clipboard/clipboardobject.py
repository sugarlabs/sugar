# Copyright (C) 2007, One Laptop Per Child
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

import os
import logging
import urlparse

from sugar.objects import mime
from sugar import activity
from sugar import util

import objecttypeservice

class ClipboardObject:

    def __init__(self, object_path, name):
        self._id = object_path
        self._name = name
        self._percent = 0
        self._formats = {}

    def destroy(self):
        for type, format in self._formats.iteritems():
            format.destroy()

    def get_id(self):
        return self._id

    def _get_type_info(self):
        logging.debug('_get_type_info')
        type_registry = objecttypeservice.get_instance()
        return type_registry.GetTypeForMIME(self.get_mime_type())
    
    def get_name(self):
        if self._name:
            return self._name
        else:
            type_info = self._get_type_info()
            if type_info:
                return type_info['name']
            else:
                return ''

    def get_icon(self):
        type_info = self._get_type_info()
        if type_info:
            return type_info['icon']
        else:
            return ''

    def get_preview(self):
        # TODO: should previews really be here?
        #return self._get_type_info().get_preview()
        return ''

    def get_activity(self):
        logging.debug('get_activity')
        mapping = {'text/html'        : 'org.laptop.WebActivity',
                   'image/jpeg'       : 'org.laptop.WebActivity',
                   'image/gif'        : 'org.laptop.WebActivity',
                   'image/png'        : 'org.laptop.WebActivity',
                   'text/plain'       : 'org.laptop.AbiWordActivity',
                   'text/rtf'         : 'org.laptop.AbiWordActivity',
                   'text/richtext'    : 'org.laptop.AbiWordActivity',
                   'application/pdf'  : 'org.laptop.sugar.Xbook'}
        mime = self.get_mime_type()
        if not mime:
            return ''
        """
        registry = activity.get_registry()
        activities = registry.get_activities_for_type(self.get_mime_type())
        # TODO: should we return several activities?
        if activities:
            return activities[0]
        else:
            return ''
        """
        if mapping.has_key(mime):
            return mapping[mime]
        else:
            return ''

    def get_percent(self):
        return self._percent

    def set_percent(self, percent):
        self._percent = percent
    
    def add_format(self, format):
        self._formats[format.get_type()] = format
        # We want to get the activity early in order to prevent a DBus lockup.
        activity = self.get_activity()
    
    def get_formats(self):
        return self._formats

    def get_mime_type(self):
        if not self._formats:
            return ''

        format = util.choose_most_significant_mime_type(self._formats.keys())

        if format == 'text/uri-list':
            data = self._formats['text/uri-list'].get_data()
            uris = data.split('\n')
            if len(uris) == 1 or not uris[1]:
                uri = urlparse.urlparse(uris[0], 'file')
                if uri.scheme == 'file':
                    logging.debug('Choosed %r!' % mime.get_for_file(uri.path))
                    format = mime.get_for_file(uri.path)

        return format

class Format:

    def __init__(self, type, data, on_disk):
        self._type = type
        self._data = data
        self._on_disk = on_disk

    def destroy(self):
        if self._on_disk:
            uri = urlparse.urlparse(self._data)
            os.remove(uri.path)

    def get_type(self):
        return self._type

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data

    def is_on_disk(self):
        return self._on_disk
