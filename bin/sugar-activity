#!/usr/bin/env python

# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import sys
import gettext
from optparse import OptionParser

import pygtk
pygtk.require('2.0')
import gtk
import dbus
import dbus.service
import dbus.glib

from sugar.activity import activityhandle
from sugar.bundle.activitybundle import ActivityBundle
from sugar import _sugarbaseext
from sugar import logger

activity_instances = []

def activity_destroy_cb(window):
    activity_instances.remove(window)
    if len(activity_instances) == 0:
        gtk.main_quit()

def create_activity_instance(constructor, handle):
    activity = constructor(handle)
    activity.connect('destroy', activity_destroy_cb)
    activity.show()

    activity_instances.append(activity)

def get_single_process_name(bundle_id):
    return bundle_id

def get_single_process_path(bundle_id):
    return '/' + bundle_id.replace('.', '/')

class SingleProcess(dbus.service.Object):
    def __init__(self, service_name, constructor):
        self.constructor = constructor
    
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(service_name, bus = bus)
        object_path = get_single_process_path(service_name)
        dbus.service.Object.__init__(self, bus_name, object_path)

    @dbus.service.method("org.laptop.SingleProcess", in_signature="a{ss}")
    def create(self, handle_dict):
        handle = activityhandle.create_from_dict(handle_dict)
        create_activity_instance(self.constructor, handle)

parser = OptionParser()
parser.add_option("-b", "--bundle-id", dest="bundle_id",
                  help="identifier of the activity bundle")
parser.add_option("-a", "--activity-id", dest="activity_id",
                  help="identifier of the activity instance")
parser.add_option("-o", "--object-id", dest="object_id",
                  help="identifier of the associated datastore object")
parser.add_option("-u", "--uri", dest="uri",
                  help="URI to load")
parser.add_option('-s', '--single-process', dest='single_process',
                  action='store_true',
                  help='start all the instances in the same process')
(options, args) = parser.parse_args()

logger.start()

if 'SUGAR_BUNDLE_PATH' not in os.environ:
    print 'SUGAR_BUNDLE_PATH is not defined in the environment.'
    sys.exit(1)

if len(args) == 0:
    print 'A python class must be specified as first argument.'
    sys.exit(1)    

bundle_path = os.environ['SUGAR_BUNDLE_PATH']
sys.path.append(bundle_path)

splitted_module = args[0].rsplit('.', 1)
module_name = splitted_module[0]
class_name = splitted_module[1]

module = __import__(module_name)        
for comp in module_name.split('.')[1:]:
    module = getattr(module, comp)

constructor = getattr(module, class_name)
handle = activityhandle.ActivityHandle(
            activity_id=options.activity_id,
            object_id=options.object_id, uri=options.uri)

if options.single_process is True:
    bus = dbus.SessionBus()

    service_name = get_single_process_name(options.bundle_id)
    service_path = get_single_process_path(options.bundle_id)

    bus_object = bus.get_object(
            'org.freedesktop.DBus', '/org/freedesktop/DBus')
    try:
        name = bus_object.GetNameOwner(
                service_name, dbus_interface='org.freedesktop.DBus')
    except  dbus.DBusException:
        name = None

    if not name:
        service = SingleProcess(service_name, constructor)
    else:
        single_process = bus.get_object(service_name, service_path)
        single_process.create(handle.get_dict())

        print 'Created %s in a single process.' % service_name
        sys.exit(0)

if hasattr(module, 'start'):
    module.start()

bundle = ActivityBundle(bundle_path)

os.environ['SUGAR_BUNDLE_ID'] = bundle.get_bundle_id()
os.environ['SUGAR_BUNDLE_NAME'] = bundle.get_name()

gettext.bindtextdomain(bundle.get_bundle_id(),
                       bundle.get_locale_path())
gettext.textdomain(bundle.get_bundle_id())

gtk.icon_theme_get_default().append_search_path(bundle.get_icons_path())

create_activity_instance(constructor, handle)

gtk.main()
