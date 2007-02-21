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

import os

import dbus
import dbus.service

from sugar.activity.bundle import Bundle
from sugar import logger

class ActivityFactoryService(dbus.service.Object):
    """Dbus service that takes care of creating new instances of an activity"""

    def __init__(self, service_name, activity_class):
        self._activities = []

        splitted_module = activity_class.rsplit('.', 1)
        module_name = splitted_module[0]
        class_name = splitted_module[1]

        module = __import__(module_name)        
        for comp in module_name.split('.')[1:]:
            module = getattr(module, comp)
        if hasattr(module, 'start'):
            module.start()

        self._module = module
        self._constructor = getattr(module, class_name)
    
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(service_name, bus = bus)
        object_path = '/' + service_name.replace('.', '/')
        dbus.service.Object.__init__(self, bus_name, object_path)

    @dbus.service.method("com.redhat.Sugar.ActivityFactory")
    def create(self):
        activity = self._constructor()

        self._activities.append(activity)
        activity.connect('destroy', self._activity_destroy_cb)

        return activity.window.xid

    def _activity_destroy_cb(self, activity):
        self._activities.remove(activity)

        if hasattr(self._module, 'stop'):
            self._module.stop()

        if len(self._activities) == 0:
            gtk.main_quit()

def start(activity_class, bundle_path):
    """Start the activity factory."""
    bundle = Bundle(bundle_path)

    logger.start(bundle.get_name())

    os.environ['SUGAR_BUNDLE_PATH'] = bundle_path
    os.environ['SUGAR_BUNDLE_SERVICE_NAME'] = bundle.get_service_name()
    os.environ['SUGAR_BUNDLE_DEFAULT_TYPE'] = bundle.get_default_type()

    factory = ActivityFactoryService(bundle.get_service_name(),
                                     activity_class)
