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

from sugar import mime

import bundleregistry

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

    def get_name(self):
        name = self._name
        if not name:
            name = mime.get_mime_description(self.get_mime_type())
        if not name:
            name = ''
        return name

    def get_icon(self):
        return mime.get_mime_icon(self.get_mime_type())

    def get_preview(self):
        # TODO: should previews really be here?
        #return self._get_type_info().get_preview()
        return ''

    def get_activities(self):
        mime = self.get_mime_type()
        if not mime:
            return ''

        registry = bundleregistry.get_registry()
        activities = registry.get_activities_for_type(self.get_mime_type())
        if activities:
            return [activity.get_bundle_id() for activity in activities]
        else:
            return ''

    def get_percent(self):
        return self._percent

    def set_percent(self, percent):
        self._percent = percent
    
    def add_format(self, format):
        self._formats[format.get_type()] = format
    
    def get_formats(self):
        return self._formats

    def get_mime_type(self):
        if not self._formats:
            return ''

        format = mime.choose_most_significant(self._formats.keys())
        if format == 'text/uri-list':
            data = self._formats['text/uri-list'].get_data()
            uri = urlparse.urlparse(mime.split_uri_list(data)[0], 'file')
            if uri.scheme == 'file':
                if os.path.exists(uri.path):
                    format = mime.get_for_file(uri.path)
                else:
                    format = mime.get_from_file_name(uri.path)                    
                logging.debug('Choosed %r!' % format)

        return format

class Format:

    def __init__(self, type, data, on_disk):
        self.owns_disk_data = False

        self._type = type
        self._data = data
        self._on_disk = on_disk

    def destroy(self):
        if self._on_disk:
            uri = urlparse.urlparse(self._data)
            if os.path.isfile(uri.path):
                os.remove(uri.path)

    def get_type(self):
        return self._type

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data

    def is_on_disk(self):
        return self._on_disk
