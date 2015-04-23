# Copyright (C) 2014, Sugarlabs
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
import logging
import dbus

from sugar3 import mime
from sugar3.activity import activityfactory
from sugar3.activity.activityhandle import ActivityHandle
from sugar3.datastore import datastore
from jarabe.model import bundleregistry

_DBUS_SERVICE = 'org.sugarlabs.BundleLauncher'
_DBUS_INTERFACE = 'org.sugarlabs.BundleLauncher'
_DBUS_PATH = '/org/sugarlabs/BundleLauncher'

_service_instance = None


def launch_bundle(bundle_id=None, object_id=None, mime_type=None):
    """Launch a bundle with the given parameters.

    If an object_id is given, the bundle will be launched with the
    object that has that id.

    If the bundle_id is not given, the first bundle that can
    handle a mime type is used.  The mime type is A. inferred from
    the object with id object_id, in case object_id is given, or
    B. the explicit mime_type parameter is used.

    """
    if bundle_id is None and object_id is None and mime_type is None:
        logging.error('At least one parameter has to be passed')
        return False

    bundle = None

    if bundle_id is None:
        if object_id is not None:
            obj = datastore.get(object_id)
            mime_type = str(obj.metadata['mime_type'])

        activities = _get_activities_for_mime(mime_type)

        if not activities:
            logging.error('No activity can start object with type, %s.',
                          mime_type)
            return False

        bundle = activities[0]

    else:
        bundle = bundleregistry.get_registry().get_bundle(bundle_id)
        # FIXME error if no bundle with the given id

    activity_handle = ActivityHandle(activity_id=None,
                                     object_id=object_id,
                                     uri=None,
                                     invited=False)

    activityfactory.create(bundle, activity_handle)
    return True


def _get_activities_for_mime(mime_type):
    registry = bundleregistry.get_registry()
    result = registry.get_activities_for_type(mime_type)

    # FIXME, move this to
    # registry.get_activities_for_type(with_parents=True) ?
    if not result:
        for parent_mime in mime.get_mime_parents(mime_type):
            for activity in registry.get_activities_for_type(parent_mime):
                if activity not in result:
                    result.append(activity)
    return result


class BundleLauncherDBusService(dbus.service.Object):

    def __init__(self):
        session_bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_DBUS_SERVICE,
                                        bus=session_bus,
                                        replace_existing=False,
                                        allow_replacement=False)
        dbus.service.Object.__init__(self, bus_name, _DBUS_PATH)

    @dbus.service.method(_DBUS_INTERFACE, in_signature='sss',
                         out_signature='b')
    def launch(self, bundle_id, object_id, mime_type):
        # Convert dbus empty strings to None, is the only way to pass
        # optional parameters with dbus.
        if bundle_id == "":
            bundle_id = None
        if object_id == "":
            object_id = None
        if mime_type == "":
            mime_type = None

        return launch_bundle(bundle_id, object_id, mime_type)


def get_service():
    global _service_instance
    if not _service_instance:
        _service_instance = BundleLauncherDBusService()
    return _service_instance


def init():
    get_service()
