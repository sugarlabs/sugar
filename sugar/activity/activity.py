"""Base class for Python-coded activities

This is currently the only reference for what an 
activity must do to participate in the Sugar desktop.
"""
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
import os

import gtk
import hippo

from sugar.presence import presenceservice
from sugar.activity.activityservice import ActivityService
from sugar.graphics.window import Window

class Activity(Window, gtk.Container):
    """Base Activity class that all other Activities derive from."""
    __gtype_name__ = 'SugarActivity'
    def __init__(self, handle):
        """Initialise the Activity 
        
        handle -- sugar.activity.activityhandle.ActivityHandle
            instance providing the activity id and access to the 
            presence service which *may* provide sharing for this 
            application
        
        Side effects: 
        
            Sets the gdk screen DPI setting (resolution) to the 
            Sugar screen resolution.
            
            Connects our "destroy" message to our _destroy_cb
            method.
        
            Creates a base gtk.Window within this window.
            
            Creates an ActivityService (self._bus) servicing
            this application.
        """
        Window.__init__(self)

        self.connect('destroy', self._destroy_cb)

        self._shared = False
        self._activity_id = handle.activity_id
        self._pservice = presenceservice.get_instance()
        self._service = None

        service = handle.get_presence_service()
        if service:
            self._join(service)

        self.realize()
    
        group = gtk.Window()
        group.realize()
        self.window.set_group(group.window)

        self._bus = ActivityService(self)

    # DEPRECATED It will be removed after 3-6-2007 stable image
    def do_add(self, widget):
        if self.child:
            self.remove(self.child)
        gtk.Window.do_add(self, widget)

    def get_service_name(self):
        """Gets the activity service name."""
        return os.environ['SUGAR_BUNDLE_SERVICE_NAME']

    def get_shared(self):
        """Returns TRUE if the activity is shared on the mesh."""
        return self._shared

    def get_id(self):
        """Get the unique activity identifier."""
        return self._activity_id

    def _join(self, service):
        """Join an existing instance of this activity on the network."""
        self._service = service
        self._shared = True
        self._service.join()
        self.present()

    def share(self):
        """Share the activity on the network."""
        logging.debug('Share activity %s on the network.' % self.get_id())
        self._service = self._pservice.share_activity(self)
        self._shared = True

    def execute(self, command, args):
        """Execute the given command with args"""
        return False

    def _destroy_cb(self, window):
        """Destroys our ActivityService and sharing service"""
        if self._bus:
            del self._bus
            self._bus = None
        if self._service:
            self._pservice.unregister_service(self._service)

def get_bundle_path():
    """Return the bundle path for the current process' bundle
    """
    return os.environ['SUGAR_BUNDLE_PATH']
