# Copyright (C) 2006, Red Hat, Inc.
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

import logging
import os
import shutil
import urlparse
import tempfile

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3 import mime

from jarabe.frame.clipboardobject import ClipboardObject, Format


_instance = None


class Clipboard(GObject.GObject):

    __gsignals__ = {
        'object-added': (GObject.SignalFlags.RUN_FIRST, None,
                         ([object])),
        'object-deleted': (GObject.SignalFlags.RUN_FIRST, None,
                           ([long])),
        'object-selected': (GObject.SignalFlags.RUN_FIRST, None,
                            ([long])),
        'object-state-changed': (GObject.SignalFlags.RUN_FIRST, None,
                                 ([object])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._objects = {}
        self._next_id = 0

    def _get_next_object_id(self):
        self._next_id += 1
        return self._next_id

    def add_object(self, name, data_hash=None):
        """ Add a object to the clipboard

        Keyword arguments:
        name -- object name
        data_hash -- hash to check if the object is already
                     in the clipboard, generated with hash()
                     over the data to be added

        Return: object_id or None if the object is not added

        """
        logging.debug('Clipboard.add_object: hash %s', data_hash)
        if data_hash is None:
            object_id = self._get_next_object_id()
        else:
            object_id = data_hash
        if object_id in self._objects:
            logging.debug('Clipboard.add_object: object already in clipboard,'
                          ' selecting previous entry instead')
            self.emit('object-selected', object_id)
            return None
        self._objects[object_id] = ClipboardObject(object_id, name)
        self.emit('object-added', self._objects[object_id])
        return object_id

    def add_object_format(self, object_id, format_type, data, on_disk):
        logging.debug('Clipboard.add_object_format')
        cb_object = self._objects[object_id]

        if on_disk and cb_object.get_percent() == 100:
            new_uri = self._copy_file(data)
            cb_object.add_format(Format(format_type, new_uri, on_disk))
            logging.debug('Added format of type ' + format_type +
                          ' with path at ' + new_uri)
        else:
            cb_object.add_format(Format(format_type, data, on_disk))
            logging.debug('Added in-memory format of type %s.', format_type)

        self.emit('object-state-changed', cb_object)

    def delete_object(self, object_id):
        cb_object = self._objects.pop(object_id)
        cb_object.destroy()
        if not self._objects:
            gtk_clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            gtk_clipboard.clear()
        self.emit('object-deleted', object_id)
        logging.debug('Deleted object with object_id %r', object_id)

    def set_object_percent(self, object_id, percent):
        cb_object = self._objects[object_id]
        if percent < 0 or percent > 100:
            raise ValueError('invalid percentage')
        if cb_object.get_percent() > percent:
            raise ValueError('invalid percentage; less than current percent')
        if cb_object.get_percent() == percent:
            # ignore setting same percentage
            return

        cb_object.set_percent(percent)

        if percent == 100:
            self._process_object(cb_object)

        self.emit('object-state-changed', cb_object)

    def _process_object(self, cb_object):
        formats = cb_object.get_formats()
        for format_name, format_ in formats.iteritems():
            if format_.is_on_disk() and not format_.owns_disk_data:
                new_uri = self._copy_file(format_.get_data())
                format_.set_data(new_uri)

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
        format_ = cb_object.get_formats()[format_type]
        return format_

    def _copy_file(self, original_uri):
        uri = urlparse.urlparse(original_uri)
        path = uri.path  # pylint: disable=E1101
        directory_, file_name = os.path.split(path)

        root, ext = os.path.splitext(file_name)
        if not ext or ext == '.':
            mime_type = mime.get_for_file(path)
            ext = '.' + mime.get_primary_extension(mime_type)

        f_, new_file_path = tempfile.mkstemp(ext, root)
        del f_
        shutil.copyfile(path, new_file_path)
        os.chmod(new_file_path, 0o644)

        return 'file://' + new_file_path


def get_instance():
    global _instance
    if not _instance:
        _instance = Clipboard()
    return _instance
