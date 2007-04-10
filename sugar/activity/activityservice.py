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

import dbus
import dbus.service

_ACTIVITY_SERVICE_NAME = "org.laptop.Activity"
_ACTIVITY_SERVICE_PATH = "/org/laptop/Activity"
_ACTIVITY_INTERFACE = "org.laptop.Activity"

class ActivityService(dbus.service.Object):
    """Base dbus service object that each Activity uses to export dbus methods.
    
    The dbus service is separate from the actual Activity object so that we can
    tightly control what stuff passes through the dbus python bindings."""

    def __init__(self, activity):
        """Initialise the service for the given activity
        
        activity -- sugar.activity.activity.Activity instance,
            must have already bound it's window (i.e. it must 
            have already initialised to the point of having
            the X window available).
        
        Creates dbus services that use the xid of the activity's
        root window as discriminants among all active services 
        of this type.  That is, the services are all available 
        as names/paths derived from the xid for the window.
        
        The various methods exposed on dbus are just forwarded
        to the client Activity object's equally-named methods.
        """
        xid = activity.window.xid
        service_name = _ACTIVITY_SERVICE_NAME + '%d' % xid 
        object_path = _ACTIVITY_SERVICE_PATH + "/%s" % xid

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(service_name, bus=bus)
        dbus.service.Object.__init__(self, bus_name, object_path)

        self._activity = activity

    @dbus.service.method(_ACTIVITY_INTERFACE)
    def share(self):
        """Called by the shell to request the activity to share itself on the network."""
        self._activity.share()

    @dbus.service.method(_ACTIVITY_INTERFACE)
    def get_id(self):
        """Get the activity identifier"""
        return self._activity.get_id()

    @dbus.service.method(_ACTIVITY_INTERFACE)
    def get_service_name(self):
        """Get the activity service name"""
        return self._activity.get_service_name()

    @dbus.service.method(_ACTIVITY_INTERFACE)
    def get_shared(self):
        """Returns True if the activity is shared on the mesh."""
        return self._activity.get_shared()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                         in_signature="sas", out_signature="b")
    def execute(self, command, args):
        return self._activity.execute(command, args)

