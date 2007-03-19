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

import _sugar
from sugar.presence import PresenceService
from sugar.activity.activityservice import ActivityService
from sugar.graphics.window import Window

class Activity(Window, gtk.Container):
    """Base Activity class that all other Activities derive from."""
    __gtype_name__ = 'SugarActivity'
    def __init__(self, handle):
        Window.__init__(self)

        # FIXME: This will work only for activities in python. We need a xsetting.
        display = gtk.gdk.display_manager_get().get_default_display()
        screen = display.get_default_screen()
        screen.set_resolution(_sugar.get_screen_dpi())

        self.connect('destroy', self._destroy_cb)

        self._shared = False
        self._activity_id = handle.activity_id
        self._pservice = PresenceService.get_instance()
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

    def get_default_type(self):
        """Gets the type of the default activity network service"""
        return os.environ['SUGAR_BUNDLE_DEFAULT_TYPE']

    def get_shared(self):
        """Returns TRUE if the activity is shared on the mesh."""
        return self._shared

    def get_id(self):
        """Get the unique activity identifier."""
        return self._activity_id

    def _join(self, service):
        self._service = service
        self._shared = True

        # Publish the default service, it's a copy of
        # one of those we found on the network.
        default_type = self.get_default_type()
        services = activity_ps.get_services_of_type(default_type)
        if len(services) > 0:
            service = services[0]
            addr = service.get_address()
            port = service.get_port()
            properties = service.get_published_values()
            self._service = self._pservice.share_activity(
                            self, default_type, properties, addr, port)
        else:
            logging.error('Cannot join the activity')

        self.present()

    def share(self):
        """Share the activity on the network."""
        logging.debug('Share activity %s on the network.' % self.get_id())

        default_type = self.get_default_type()
        self._service = self._pservice.share_activity(self, default_type)
        self._shared = True

    def execute(self, command, args):
        """Execute the given command with args"""
        return False

    def _destroy_cb(self, window):
        if self._bus:
            del self._bus
            self._bus = None
        if self._service:
            self._pservice.unregister_service(self._service)

def get_bundle_path():
    return os.environ['SUGAR_BUNDLE_PATH']
