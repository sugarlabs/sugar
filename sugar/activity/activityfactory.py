"""Shell side object which manages request to start activity"""
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

from sugar.presence import presenceservice
from sugar.activity.activityhandle import ActivityHandle
from sugar import util

_ACTIVITY_FACTORY_INTERFACE = "org.laptop.ActivityFactory"

def create_activity_id():
    """Generate a new, unique ID for this activity"""
    pservice = presenceservice.get_instance()

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
            if act_id == act.props.id:
                found = True
                break
        if not found:
            return act_id
    raise RuntimeError("Cannot generate unique activity id.")

class ActivityCreationHandler(gobject.GObject):
    """Sugar-side activity creation interface
    
    This object uses a dbus method on the ActivityFactory
    service to create the new activity.  It generates 
    GObject events in response to the success/failure of
    activity startup using callbacks to the service's 
    create call.
    """
    __gsignals__ = {
        'success': (gobject.SIGNAL_RUN_FIRST,
                    gobject.TYPE_NONE, ([])),
        'error':   (gobject.SIGNAL_RUN_FIRST,
                    gobject.TYPE_NONE, 
                   ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, service_name, activity_handle):
        """Initialise the handler
        
        service_name -- the service name of the bundle factory
        activity_handle -- stores the values which are to 
            be passed to the service to uniquely identify
            the activity to be created and the sharing 
            service that may or may not be connected with it
            
            sugar.activity.activityhandle.ActivityHandle instance
        
        calls the "create" method on the service for this 
        particular activity type and registers the 
        _reply_handler and _error_handler methods on that 
        call's results.
        
        The specific service which creates new instances of this 
        particular type of activity is created during the activity
        registration process in shell bundle registry which creates 
        service definition files for each registered bundle type.
        """
        gobject.GObject.__init__(self)
        self._service_name = service_name
        self._activity_handle = activity_handle

        bus = dbus.SessionBus()
        object_path = '/' + service_name.replace('.', '/')
        proxy_obj = bus.get_object(service_name, object_path,
                                   follow_name_owner_changes=True)
        factory = dbus.Interface(proxy_obj, _ACTIVITY_FACTORY_INTERFACE)

        factory.create(self._activity_handle.get_dict(),
                       reply_handler=self._reply_handler,
                       error_handler=self._error_handler)

    def get_activity_id(self):
        """Retrieve the unique identity for this activity"""
        return self._activity_handle.activity_id

    def _reply_handler(self, xid):
        """Reply from service regarding what window was created 
        
        xid -- X windows ID for the window that was just created
        
        emits the "success" message (on ourselves)
        """
        logging.debug("Activity created %s (%s)." % 
            (self._activity_handle.activity_id, self._service_name))
        self.emit('success')

    def _error_handler(self, err):
        """Reply from service with an error message (exception)
        
        err -- exception object describing the error
        
        emits the "error" message (on ourselves)
        """
        logging.debug("Couldn't create activity %s (%s): %s" %
            (self._activity_handle.activity_id, self._service_name, err))
        self.emit('error', err)

def create(service_name, activity_handle=None):
    """Create a new activity from its name."""
    if not activity_handle:
        activity_handle = ActivityHandle(create_activity_id())
    return ActivityCreationHandler(service_name, activity_handle)

def create_with_uri(service_name, uri):
    """Create a new activity and pass the uri as handle."""
    activity_handle = ActivityHandle(create_activity_id())
    activity_handle.uri = uri
    return ActivityCreationHandler(service_name, activity_handle)

def create_with_object_id(service_name, object_id):
    """Create a new activity and pass the object id as handle."""
    activity_handle = ActivityHandle(create_activity_id())
    activity_handle.object_id = object_id
    return ActivityCreationHandler(service_name, activity_handle)
