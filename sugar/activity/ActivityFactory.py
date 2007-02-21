# Copyright (C) 2006, Red Hat, Inc.
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
import gobject
import gtk

from sugar.presence.PresenceService import PresenceService
from sugar.activity import bundleregistry

_ACTIVITY_SERVICE_NAME = "org.laptop.Activity"
_ACTIVITY_SERVICE_PATH = "/org/laptop/Activity"
_ACTIVITY_INTERFACE = "org.laptop.Activity"

class ActivityCreationHandler(gobject.GObject):

    __gsignals__ = {
        'error':       (gobject.SIGNAL_RUN_FIRST,
                        gobject.TYPE_NONE, 
                       ([gobject.TYPE_PYOBJECT])),
        'success':     (gobject.SIGNAL_RUN_FIRST,
                        gobject.TYPE_NONE, 
                       ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, service_name):
        gobject.GObject.__init__(self)

        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(service_name)

        bus = dbus.SessionBus()
        proxy_obj = bus.get_object(service_name, bundle.get_object_path())
        factory = dbus.Interface(proxy_obj, "com.redhat.Sugar.ActivityFactory")

        factory.create(reply_handler=self._reply_handler, error_handler=self._error_handler)

    def _reply_handler(self, xid):
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object(_ACTIVITY_SERVICE_NAME + '%d' % xid,
                                   _ACTIVITY_SERVICE_PATH + "/%s" % xid)
        activity = dbus.Interface(proxy_obj, _ACTIVITY_INTERFACE)
        self.emit('success', activity)

    def _error_handler(self, err):
        logging.debug("Couldn't create activity: %s" % err)
        self.emit('error', err)

def create(service_name):
    """Create a new activity from its name."""
    return ActivityCreationHandler(service_name)
