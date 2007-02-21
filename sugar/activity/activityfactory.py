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

from sugar.presence import PresenceService
from sugar.activity import bundleregistry
from sugar.activity.activityhandle import ActivityHandle
from sugar import util

_ACTIVITY_SERVICE_NAME = "org.laptop.Activity"
_ACTIVITY_SERVICE_PATH = "/org/laptop/Activity"
_ACTIVITY_INTERFACE = "org.laptop.Activity"

class ActivityCreationHandler(gobject.GObject):

    __gsignals__ = {
        'error':       (gobject.SIGNAL_RUN_FIRST,
                        gobject.TYPE_NONE, 
                       ([gobject.TYPE_PYOBJECT])),
    }

    def __init__(self, service_name, activity_handle):
        gobject.GObject.__init__(self)

        self._service_name = service_name

        if activity_handle:
            self._activity_handle = activity_handle
        else:
            activity_id = self._find_unique_activity_id()
            if activity_id:
                self._activity_handle = ActivityHandle(activity_id)
            else:
                raise RuntimeError("Cannot generate activity id.")

        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(service_name)

        bus = dbus.SessionBus()
        proxy_obj = bus.get_object(service_name, bundle.get_object_path())
        factory = dbus.Interface(proxy_obj, "com.redhat.Sugar.ActivityFactory")

        factory.create(self._activity_handle.get_dict(),
                       reply_handler=self._reply_handler,
                       error_handler=self._error_handler)

    def get_activity_id(self):
        return self._activity_handle.activity_id

    def _find_unique_activity_id(self):
        pservice = PresenceService.get_instance()

        # create a new unique activity ID
        i = 0
        act_id = None
        while i < 10:
            act_id = util.unique_id()
            i += 1

            # check through network activities
            found = False
            activities = pservice.get_activities()
            for act in activities:
                if act_id == act.get_id():
                    found = True
                    break
            if found:
                act_id = None
                continue

        return act_id

    def _reply_handler(self, xid):
        logging.debug("Activity created %s (%s)." % 
            (self._activity_handle.activity_id, self._service_name))

    def _error_handler(self, err):
        logging.debug("Couldn't create activity %s (%s): %s" %
            (self._activity_handle.activity_id, self._service_name, err))
        self.emit('error', err)

def create(service_name, activity_handle=None):
    """Create a new activity from its name."""
    return ActivityCreationHandler(service_name, activity_handle)
