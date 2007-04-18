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
import gobject
import os
import shutil
import dbus
import dbus.service
from sugar import env
from sugar import util
from clipboardobject import ClipboardObject, Format
import typeregistry

NAME_KEY = 'NAME'
PERCENT_KEY = 'PERCENT'
ICON_KEY = 'ICON'
PREVIEW_KEY = 'PREVIEW'
ACTIVITY_KEY = 'ACTIVITY'
FORMATS_KEY = 'FORMATS'

class ClipboardDBusServiceHelper(dbus.service.Object):

    _CLIPBOARD_DBUS_INTERFACE = "org.laptop.Clipboard"
    _CLIPBOARD_OBJECT_PATH = "/org/laptop/Clipboard"
    _CLIPBOARD_OBJECTS_PATH = _CLIPBOARD_OBJECT_PATH + "/Objects/"

    def __init__(self, parent):
        self._parent = parent
        self._objects = {}
        self._next_id = 0

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(self._CLIPBOARD_DBUS_INTERFACE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, self._CLIPBOARD_OBJECT_PATH)

    def _get_next_object_id(self):
        self._next_id += 1
        return self._next_id

    def _handle_file_completed(self, cb_object):
        """If the object is an on-disk file, and it's at 100%, and we care about
        it's file type, copy that file to $HOME and upate the clipboard object's
        data to point to the new location"""
        formats = cb_object.get_formats()
        if not len(formats) or len(formats) > 1:
            return

        format = formats.values()[0]
        if not format.get_on_disk():
            return

        if not len(cb_object.get_activity()):
            # no activity to handle this, don't autosave it
            return

        # copy to homedir
        src = format.get_data()
        if not os.path.exists(src):
            logging.debug("File %s doesn't appear to exist" % src)
            return
        dst = os.path.join(os.path.expanduser("~"), os.path.basename(src))
        try:
            shutil.move(src, dst)
            format._set_data(dst)
        except IOError, e:
            logging.debug("Couldn't move file %s to %s: %s" % (src, dst, e))

    # dbus methods        
    @dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
                         in_signature="s", out_signature="o")
    def add_object(self, name):
        op = self._CLIPBOARD_OBJECTS_PATH + "%d" % self._get_next_object_id()
        self._objects[op] = ClipboardObject(op, name)
        self.object_added(dbus.ObjectPath(op), name)
        logging.debug('Added object ' + op + ' with name ' + name)
        return dbus.ObjectPath(op)

    @dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
                         in_signature="ssayb", out_signature="", byte_arrays=True)
    def add_object_format(self, object_path, format_type, data, on_disk):
        cb_object = self._objects[str(object_path)]
        cb_object.add_format(Format(format_type, data, on_disk))

        if on_disk:
            logging.debug('Added format of type ' + format_type + ' with path at ' + data)
        else:
            logging.debug('Added in-memory format of type ' + format_type + '.')
                        
        self.object_state_changed(object_path, {NAME_KEY: cb_object.get_name(),
                                  PERCENT_KEY: cb_object.get_percent(),
                                  ICON_KEY: cb_object.get_icon(),
                                  PREVIEW_KEY: cb_object.get_preview(),
                                  ACTIVITY_KEY: cb_object.get_activity()})

    @dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
                         in_signature="o", out_signature="")
    def delete_object(self, object_path):
        cb_object = self._objects.pop(str(object_path))
        cb_object.destroy()
        self.object_deleted(object_path)
        logging.debug('Deleted object with object_id ' + object_path)
        
    @dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
                         in_signature="oi", out_signature="")
    def set_object_percent(self, object_path, percent):
        cb_object = self._objects[str(object_path)]
        if percent < 0 or percent > 100:
            raise ValueError("invalid percentage")
        if cb_object.get_percent() > percent:
            raise ValueError("invalid percentage; less than current percent")
        if cb_object.get_percent() == percent:
            # ignore setting same percentage
            return

        cb_object.set_percent(percent)

        if percent == 100:
            self._handle_file_completed(cb_object)

        self.object_state_changed(object_path, {NAME_KEY: cb_object.get_name(),
                                    PERCENT_KEY: percent,
                                    ICON_KEY: cb_object.get_icon(),
                                    PREVIEW_KEY: cb_object.get_preview(),
                                    ACTIVITY_KEY: cb_object.get_activity()})

    @dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
                         in_signature="o", out_signature="a{sv}")
    def get_object(self, object_path):
        cb_object = self._objects[str(object_path)]
        formats = cb_object.get_formats()
        format_types = dbus.Array([], 's')
        
        for type, format in formats.iteritems():
            format_types.append(type)
        
        result_dict = {NAME_KEY: cb_object.get_name(),
                PERCENT_KEY: cb_object.get_percent(),
                ICON_KEY: cb_object.get_icon(),
                PREVIEW_KEY: cb_object.get_preview(),
                ACTIVITY_KEY: cb_object.get_activity(),
                FORMATS_KEY: format_types}
        return dbus.Dictionary(result_dict)

    @dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
                         in_signature="os", out_signature="ay")
    def get_object_data(self, object_path, format_type):       
        cb_object = self._objects[str(object_path)]
        formats = cb_object.get_formats()
        return dbus.ByteArray(formats[format_type].get_data())
    
    # dbus signals
    @dbus.service.signal(_CLIPBOARD_DBUS_INTERFACE, signature="os")
    def object_added(self, object_path, name):
        pass

    @dbus.service.signal(_CLIPBOARD_DBUS_INTERFACE, signature="o")
    def object_deleted(self, object_path):
        pass

    @dbus.service.signal(_CLIPBOARD_DBUS_INTERFACE, signature="oa{sv}")
    def object_state_changed(self, object_path, values):
        pass

class ClipboardService(object):
    def __init__(self):
        self._dbus_helper = ClipboardDBusServiceHelper(self)

    def run(self):
        loop = gobject.MainLoop()
        try:
            loop.run()
        except KeyboardInterrupt:
            print 'Ctrl+C pressed, exiting...'
