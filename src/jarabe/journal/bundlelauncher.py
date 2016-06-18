# Copyright (C) 2014, Sugarlabs (Manuel Quinones)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging

from sugar3.activity import activityfactory
from sugar3.activity.activityhandle import ActivityHandle
from sugar3.datastore import datastore

from jarabe.model import bundleregistry
from jarabe.journal.misc import get_activities_for_mime


def get_bundle(bundle_id=None, object_id=None):
    if bundle_id is None and object_id is None:
        logging.error('At least one parameter has to be passed')
        return None

    if bundle_id is None:
        obj = datastore.get(object_id)

        if obj.metadata['mime_type'] is None:
            return None
        mime_type = str(obj.metadata['mime_type'])

        activities = get_activities_for_mime(mime_type)

        if not activities:
            logging.warning('No activity can start object with type, %s.',
                            mime_type)
            return None

        return activities[0]
    else:
        bundle = bundleregistry.get_registry().get_bundle(bundle_id)
        if bundle is None:
            logging.warning('Activity with the bundle_id %s was not found',
                            mime_type)
            return None
        return bundle


def launch_bundle(bundle_id=None, object_id=None):
    '''
    Launch a bundle with the given parameters.

    If an object_id is given, the bundle will be launched with the
    object that has that id.  Otherwise, the bundle with the given
    bundle_id will be launched.

    Note: this function should not be used out side of the sugar
    shell process.  The `JournalActivityDBusService` makes this
    avaliable over DBus.
    '''
    bundle = get_bundle(bundle_id, object_id)
    if bundle is None:
        return False

    activity_handle = ActivityHandle(activity_id=None,
                                     object_id=object_id,
                                     uri=None,
                                     invited=False)
    activityfactory.create(bundle, activity_handle)
    return True
