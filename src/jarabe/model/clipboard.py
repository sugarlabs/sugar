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

import logging
import os
import shutil
import urlparse
import tempfile

import gobject

from sugar import mime

from jarabe.model.clipboardobject import ClipboardObject, Format

class Clipboard(gobject.GObject):

    __gsignals__ = {
        'object-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([object])),
        'object-deleted': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([int])),
        'object-state-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([object])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._objects = {}
        self._next_id = 0

    def _get_next_object_id(self):
        self._next_id += 1
        return self._next_id

    def add_object(self, name):
        logging.debug('Clipboard.add_object')
        object_id = self._get_next_object_id()
        self._objects[object_id] = ClipboardObject(object_id, name)
        self.emit('object-added', self._objects[object_id])
        return object_id

    def add_object_format(self, object_id, format_type, data, on_disk):
        logging.debug('Clipboard.add_object_format')
        cb_object = self._objects[object_id]

        if format_type == 'XdndDirectSave0':
            format = Format('text/uri-list', data + '\r\n', on_disk)
            format.owns_disk_data = True
            cb_object.add_format(format)
        elif on_disk and cb_object.get_percent() == 100:
            new_uri = self._copy_file(data)
            cb_object.add_format(Format(format_type, new_uri, on_disk))
            logging.debug('Added format of type ' + format_type 
                          + ' with path at ' + new_uri)
        else:
            cb_object.add_format(Format(format_type, data, on_disk))
            logging.debug('Added in-memory format of type ' + format_type + '.')

        self.emit('object-state-changed', cb_object)

    def delete_object(self, object_id):
        cb_object = self._objects.pop(object_id)
        cb_object.destroy()
        self.emit('object-deleted', object_id)
        logging.debug('Deleted object with object_id %r' % object_id)
        
    def set_object_percent(self, object_id, percent):
        cb_object = self._objects[object_id]
        if percent < 0 or percent > 100:
            raise ValueError("invalid percentage")
        if cb_object.get_percent() > percent:
            raise ValueError("invalid percentage; less than current percent")
        if cb_object.get_percent() == percent:
            # ignore setting same percentage
            return

        cb_object.set_percent(percent)

        if percent == 100:
            self._process_object(cb_object)

        self.emit('object-state-changed', cb_object)

    def _process_object(self, cb_object):
        formats = cb_object.get_formats()
        for format_name, format in formats.iteritems():
            if format.is_on_disk() and not format.owns_disk_data:
                new_uri = self._copy_file(format.get_data())
                format.set_data(new_uri)

        # Add a text/plain format to objects that are text but lack it
        if 'text/plain' not in formats.keys():
            if 'UTF8_STRING' in formats.keys():
                self.add_object_format(
                    cb_object.get_id(), 'text/plain',
                    data=formats['UTF8_STRING'].get_data(), on_disk=False)
            elif 'text/unicode' in formats.keys():
                self.add_object_format(
                    cb_object.get_id(), 'text/plain',
                    data=formats['UTF8_STRING'].get_data(), on_disk=False)

    def get_object(self, object_id):
        logging.debug('Clipboard.get_object')
        return self._objects[object_id]

    def get_object_data(self, object_id, format_type):   
        logging.debug('Clipboard.get_object_data')
        cb_object = self._objects[object_id]
        format = cb_object.get_formats()[format_type]
        return format

    def _copy_file(self, original_uri):
        uri = urlparse.urlparse(original_uri)
        path_, file_name = os.path.split(uri.path)

        root, ext = os.path.splitext(file_name)
        if not ext or ext == '.':
            mime_type = mime.get_for_file(uri.path)
            ext = '.' + mime.get_primary_extension(mime_type)

        f_, new_file_path = tempfile.mkstemp(ext, root)
        del f_
        shutil.copyfile(uri.path, new_file_path)
        os.chmod(new_file_path, 0644)

        return 'file://' + new_file_path

_instance = None

def get_instance():
    global _instance
    if not _instance:
        _instance = Clipboard()
    return _instance
