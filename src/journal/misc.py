# Copyright (C) 2007, One Laptop Per Child
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
import time
import traceback
import sys
import os
from gettext import gettext as _

import gtk

from sugar import activity
from sugar.activity import activityfactory
from sugar.activity.activityhandle import ActivityHandle
from sugar import mime
from sugar.bundle.activitybundle import ActivityBundle
from sugar.bundle.contentbundle import ContentBundle
from sugar.bundle.bundle import MalformedBundleException
from sugar import util

from journal.journalentrybundle import JournalEntryBundle

def _get_icon_file_name(icon_name):
    icon_theme = gtk.icon_theme_get_default()
    info = icon_theme.lookup_icon(icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR, 0)
    if not info:
        # display standard icon when icon for mime type is not found
        info = icon_theme.lookup_icon('application-octet-stream',
                                      gtk.ICON_SIZE_LARGE_TOOLBAR, 0)
    fname = info.get_filename()
    del info
    return fname

_icon_cache = util.LRU(50)

def get_icon_name(jobject):

    cache_key = (jobject.object_id, jobject.metadata.get('timestamp', None))
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    file_name = None

    if jobject.is_activity_bundle() and jobject.file_path:
        try:
            bundle = ActivityBundle(jobject.file_path)
            file_name = bundle.get_icon()
        except Exception:
            logging.warning('Could not read bundle:\n' + \
                ''.join(traceback.format_exception(*sys.exc_info())))
            file_name = _get_icon_file_name('application-octet-stream')

    if not file_name and jobject.metadata['activity']:
        service_name = jobject.metadata['activity']
        activity_info = activity.get_registry().get_activity(service_name)
        if activity_info:
            file_name = activity_info.icon

    mime_type = jobject.metadata['mime_type']
    if not file_name and mime_type:
        icon_name = mime.get_mime_icon(mime_type)
        if icon_name:
            file_name = _get_icon_file_name(icon_name)

    if not file_name or not os.path.exists(file_name):
        file_name = _get_icon_file_name('application-octet-stream')

    _icon_cache[cache_key] = file_name

    return file_name

def get_date(jobject):
    """ Convert from a string in iso format to a more human-like format. """
    if jobject.metadata.has_key('timestamp'):
        timestamp = float(jobject.metadata['timestamp'])
        return util.timestamp_to_elapsed_string(timestamp)
    elif jobject.metadata.has_key('mtime'):
        ti = time.strptime(jobject.metadata['mtime'], "%Y-%m-%dT%H:%M:%S")
        return util.timestamp_to_elapsed_string(time.mktime(ti))
    else:
        return _('No date')

def get_bundle(jobject):
    try:
        if jobject.is_activity_bundle() and jobject.file_path:
            return ActivityBundle(jobject.file_path)
        elif jobject.is_content_bundle() and jobject.file_path:
            return ContentBundle(jobject.file_path)
        elif jobject.metadata['mime_type'] == JournalEntryBundle.MIME_TYPE \
                and jobject.file_path:
            return JournalEntryBundle(jobject.file_path)
        else:
            return None
    except MalformedBundleException, e:
        logging.warning('Incorrect bundle: %r' % e)
        return None

def _get_activities_for_mime(mime_type):
    registry = activity.get_registry()
    result = registry.get_activities_for_type(mime_type)
    if not result:
        for parent_mime in mime.get_mime_parents(mime_type):
            result.extend(registry.get_activities_for_type(parent_mime))
    return result

def get_activities(jobject):
    activities = []

    bundle_id = jobject.metadata.get('activity', '')
    if bundle_id:
        activity_info = activity.get_registry().get_activity(bundle_id)
        if activity_info:
            activities.append(activity_info)

    mime_type = jobject.metadata.get('mime_type', '')
    if mime_type:
        activities_info = _get_activities_for_mime(mime_type)
        for activity_info in activities_info:
            if activity_info.bundle_id != bundle_id:
                activities.append(activity_info)

    return activities

def resume(jobject, bundle_id=None):
    if jobject.is_activity_bundle() and not bundle_id:

        logging.debug('Creating activity bundle')
        bundle = ActivityBundle(jobject.file_path)
        if not bundle.is_installed():
            logging.debug('Installing activity bundle')
            bundle.install()
        elif bundle.need_upgrade():
            logging.debug('Upgrading activity bundle')
            bundle.upgrade()

        logging.debug('activityfactory.creating bundle with id %r',
                        bundle.get_bundle_id())
        activityfactory.create(bundle.get_bundle_id())

    elif jobject.is_content_bundle() and not bundle_id:

        logging.debug('Creating content bundle')
        bundle = ContentBundle(jobject.file_path)
        if not bundle.is_installed():
            logging.debug('Installing content bundle')
            bundle.install()

        activities = _get_activities_for_mime('text/html')
        if len(activities) == 0:
            logging.warning('No activity can open HTML content bundles')
            return

        uri = bundle.get_start_uri()
        logging.debug('activityfactory.creating with uri %s', uri)
        activityfactory.create_with_uri(activities[0].bundle_id,
                                        bundle.get_start_uri())
    else:
        if not get_activities(jobject) and bundle_id is None:
            logging.warning('No activity can open this object, %s.' %
                    jobject.metadata.get('mime_type', None))
            return
        if bundle_id is None:
            bundle_id = get_activities(jobject)[0].bundle_id

        activity_id = jobject.metadata['activity_id']
        object_id = jobject.object_id

        if activity_id:
            handle = ActivityHandle(object_id=object_id,
                                    activity_id=activity_id)
            activityfactory.create(bundle_id, handle)
        else:
            activityfactory.create_with_object_id(bundle_id, object_id)

