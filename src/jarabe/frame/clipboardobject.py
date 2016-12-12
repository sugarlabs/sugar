# Copyright (C) 2007, One Laptop Per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
import urlparse
from gi.repository import Gio
from gi.repository import Gtk

from gettext import gettext as _
from sugar3 import mime
from sugar3.bundle.activitybundle import ActivityBundle


class ClipboardObject(object):

    def __init__(self, object_path, name):
        self._id = object_path
        self._name = name
        self._percent = 0
        self._formats = {}

    def destroy(self):
        for format_ in self._formats.itervalues():
            format_.destroy()

    def get_id(self):
        return self._id

    def get_name(self):
        name = self._name
        if not name:
            mime_type = mime.get_mime_description(self.get_mime_type())

            if not mime_type:
                mime_type = 'Data'
            name = _('%s clipping') % mime_type

        return name

    def get_icon(self):
        mime_type = self.get_mime_type()

        generic_types = mime.get_all_generic_types()
        for generic_type in generic_types:
            if mime_type in generic_type.mime_types:
                return generic_type.icon

        icons = Gio.content_type_get_icon(mime_type)
        icon_name = None
        if icons is not None:
            icon_theme = Gtk.IconTheme.get_default()
            for icon_name in icons.props.names:
                icon_info = (
                    icon_theme.lookup_icon(icon_name,
                                           Gtk.IconSize.LARGE_TOOLBAR, 0))
                if icon_info is not None:
                    del icon_info
                    return icon_name

        return 'application-octet-stream'

    def get_preview(self):
        for mime_type in ['UTF8_STRING']:
            if mime_type in self._formats:
                return self._formats[mime_type].get_data()
        return ''

    def is_bundle(self):
        # A bundle will have only one format.
        if not self._formats:
            return False
        else:
            return self._formats.keys()[0] == ActivityBundle.MIME_TYPE

    def get_percent(self):
        return self._percent

    def set_percent(self, percent):
        self._percent = percent

    def add_format(self, format_):
        self._formats[format_.get_type()] = format_

    def get_formats(self):
        return self._formats

    def get_mime_type(self):
        if not self._formats:
            return ''

        format_ = mime.choose_most_significant(self._formats.keys())
        if format_ == 'text/uri-list':
            uri_data = self._formats[format_].get_data()
            uri = urlparse.urlparse(uri_data, 'file')
            scheme = uri.scheme  # pylint: disable=E1101
            if scheme == 'file':
                path = uri.path  # pylint: disable=E1101
                if os.path.exists(path):
                    format_ = mime.get_for_file(path)
                else:
                    format_ = mime.get_from_file_name(path)
                logging.debug('Chose %r!', format_)

        return format_


class Format(object):

    def __init__(self, mime_type, data, on_disk):
        self.owns_disk_data = False

        self._type = mime_type
        self._data = data
        self._on_disk = on_disk

    def destroy(self):
        if self._on_disk:
            uri = urlparse.urlparse(self._data)
            path = uri.path  # pylint: disable=E1101
            if os.path.isfile(path):
                os.remove(path)

    def get_type(self):
        return self._type

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data

    def is_on_disk(self):
        return self._on_disk
