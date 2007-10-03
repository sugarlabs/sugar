# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
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

import logging

import dbus
import dbus.glib
import gobject

from sugar import util

DS_DBUS_SERVICE = "org.laptop.sugar.DataStore"
DS_DBUS_INTERFACE = "org.laptop.sugar.DataStore"
DS_DBUS_PATH = "/org/laptop/sugar/DataStore"

_data_store = None

def _get_data_store():
    global _data_store

    if not _data_store:
        _bus = dbus.SessionBus()
        _data_store = dbus.Interface(_bus.get_object(DS_DBUS_SERVICE,
                                                     DS_DBUS_PATH),
                                     DS_DBUS_INTERFACE)
    return _data_store

def create(properties, filename, transfer_ownership=False):
    object_id = _get_data_store().create(dbus.Dictionary(properties), filename,
                    transfer_ownership)
    logging.debug('dbus_helpers.create: ' + object_id)
    return object_id

def update(uid, properties, filename, transfer_ownership=False,
        reply_handler=None, error_handler=None, timeout=-1):
    debug_props = properties.copy()
    if debug_props.has_key("preview"):
        debug_props["preview"] = "<omitted>"
    logging.debug('dbus_helpers.update: %s, %s, %s, %s' % (uid, filename, debug_props, transfer_ownership))
    if reply_handler and error_handler:
        _get_data_store().update(uid, dbus.Dictionary(properties), filename,
                transfer_ownership,
                reply_handler=reply_handler,
                error_handler=error_handler,
                timeout=timeout)
    else:
        _get_data_store().update(uid, dbus.Dictionary(properties), filename, transfer_ownership)

def delete(uid):
    logging.debug('dbus_helpers.delete: %r' % uid)
    _get_data_store().delete(uid)
        
def get_properties(uid):
    logging.debug('dbus_helpers.get_properties: %s' % uid)
    return _get_data_store().get_properties(uid)

def get_filename(uid):
    filename = _get_data_store().get_filename(uid)
    logging.debug('dbus_helpers.get_filename: %s, %s' % (uid, filename))
    return filename

def find(query, properties, reply_handler, error_handler):
    logging.debug('dbus_helpers.find: %r %r' % (query, properties))
    if reply_handler and error_handler:
        return _get_data_store().find(query, properties,
                reply_handler=reply_handler, error_handler=error_handler)
    else:
        return _get_data_store().find(query, properties)

def mount(uri, options):
    return _get_data_store().mount(uri, options)

def unmount(mount_point_id):
    _get_data_store().unmount(mount_point_id)

def mounts():
    return _get_data_store().mounts()

def get_unique_values(key):
    return _get_data_store().get_uniquevaluesfor(key, dbus.Dictionary({}, signature='ss'))

def complete_indexing():
    return _get_data_store().complete_indexing()

