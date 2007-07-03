# Copyright (C) 2006-2007 Red Hat, Inc.
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
        
        activity -- sugar.activity.activity.Activity instance
        
        Creates dbus services that use the instance's activity_id
        as discriminants among all active services 
        of this type.  That is, the services are all available 
        as names/paths derived from the instance's activity_id.
        
        The various methods exposed on dbus are just forwarded
        to the client Activity object's equally-named methods.
        """
        activity.realize()

        activity_id = activity.get_id()
        service_name = _ACTIVITY_SERVICE_NAME + activity_id
        object_path  = _ACTIVITY_SERVICE_PATH + "/" + activity_id

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(service_name, bus=bus)
        dbus.service.Object.__init__(self, bus_name, object_path)

        self._activity = activity

    @dbus.service.method(_ACTIVITY_INTERFACE)
    def set_active(self, active):
        logging.debug('ActivityService.set_active: %s.' % active)
        self._activity.props.active = active
