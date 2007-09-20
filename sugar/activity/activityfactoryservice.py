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

import os
import sys
from optparse import OptionParser
import gettext
import traceback
import logging

import gobject
import gtk
import dbus
import dbus.service
import dbus.glib

from sugar.bundle.activitybundle import ActivityBundle
from sugar.activity import activityhandle
from sugar import logger
from sugar import _sugarext
from sugar import env

# Work around for dbus mutex locking issue
gobject.threads_init()
dbus.glib.threads_init()

_ACTIVITY_FACTORY_INTERFACE = "org.laptop.ActivityFactory"

class ActivityFactoryService(dbus.service.Object):
    """D-Bus service that creates instances of Python activities
    
    The ActivityFactoryService is a dbus service created for 
    each Python based activity type (that is, each activity 
    bundle which declares a "class" in its activity.info file,
    rather than an "exec").
    
    The ActivityFactoryService is the actual process which 
    instantiates the Python classes for Sugar interfaces.  That
    is, your Python code runs in the same process as the 
    ActivityFactoryService itself.
    
    The "service" process is created at the moment Sugar first 
    attempts to create an instance of the activity type.  It
    then remains in memory until the last instance of the 
    activity type is terminated.
    """

    def __init__(self, service_name, activity_class):
        """Initialize the service to create activities of this type
        
        service_name -- bundle's service name, this is used 
            to construct the dbus service name used to access
            the created service.
        activity_class -- dotted Python class name for the 
            Activity class which is to be instantiated by 
            the service.  Assumed to be composed of a module 
            followed by a class.
            
        if the module specified has a "start" attribute this object
        will be called on service initialisation (before first 
        instance is created).
        
        if the module specified has a "stop" attribute this object 
        will be called after every instance exits (note: may be 
        called multiple times for each time start is called!)
        """
        self._activities = []
        self._service_name = service_name

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

    @dbus.service.method("org.laptop.ActivityFactory", in_signature="a{ss}")
    def create(self, handle):
        """Create a new instance of this activity 
        
        handle -- sugar.activity.activityhandle.ActivityHandle
            compatible dictionary providing the instance-specific
            values for the new instance 
        
        returns xid for the created instance' root window
        """
        activity_handle = activityhandle.create_from_dict(handle)

        try:
            activity = self._constructor(activity_handle)
        except Exception, e:
            logging.error(traceback.format_exc())
            sys.exit(1)

        activity.present()

        self._activities.append(activity)
        activity.connect('destroy', self._activity_destroy_cb)

        return activity.window.xid

    def _activity_destroy_cb(self, activity):
        """On close of an instance's root window
        
        Removes the activity from the tracked activities.
        
        If our implementation module has a stop, calls 
        that.
        
        If there are no more tracked activities, closes 
        the activity.
        """
        self._activities.remove(activity)

        if hasattr(self._module, 'stop'):
            self._module.stop()

        if len(self._activities) == 0:
            gtk.main_quit()

def run_with_args(args):
    """Start the activity factory."""
    parser = OptionParser()
    parser.add_option("-p", "--bundle-path", dest="bundle_path",
                      help="path to the activity bundle")
    (options, args) = parser.parse_args()

    run(options.bundle_path)

def run(bundle_path):
    sys.path.append(bundle_path)

    bundle = ActivityBundle(bundle_path)

    logger.start(bundle.get_service_name())

    gettext.bindtextdomain(bundle.get_service_name(),
                           bundle.get_locale_path())
    gettext.textdomain(bundle.get_service_name())

    gtk.icon_theme_get_default().append_search_path(bundle.get_icons_path())

    os.environ['SUGAR_BUNDLE_PATH'] = bundle_path
    os.environ['SUGAR_ACTIVITY_ROOT'] = env.get_profile_path(bundle.get_service_name())

    _sugarext.set_prgname(bundle.get_service_name())
    _sugarext.set_application_name(bundle.get_name())

    factory = ActivityFactoryService(bundle.get_service_name(),
                                     bundle.activity_class)
