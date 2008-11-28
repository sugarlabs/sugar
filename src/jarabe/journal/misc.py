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

from sugar.activity import activityfactory
from sugar.activity.activityhandle import ActivityHandle
from sugar import mime
from sugar.bundle.activitybundle import ActivityBundle
from sugar.bundle.contentbundle import ContentBundle
from sugar.bundle.bundle import MalformedBundleException
from sugar import util

from jarabe.model import bundleregistry
from jarabe.journal.journalentrybundle import JournalEntryBundle
from jarabe.journal import model

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

def get_icon_name(metadata):
    cache_key = (metadata['uid'], metadata.get('timestamp', None))
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    file_name = None

    #TODO: figure out the best place to get rid of that temp file
    file_path = model.get_file(metadata['uid'])
    if is_activity_bundle(metadata) and os.path.exists(file_path):
        try:
            bundle = ActivityBundle(file_path)
            file_name = bundle.get_icon()
        except Exception:
            logging.warning('Could not read bundle:\n' + \
                ''.join(traceback.format_exception(*sys.exc_info())))
            file_name = _get_icon_file_name('application-octet-stream')

    if not file_name and metadata['activity']:
        service_name = metadata['activity']
        activity_info = bundleregistry.get_registry().get_bundle(service_name)
        if activity_info:
            file_name = activity_info.get_icon()

    mime_type = metadata['mime_type']
    if not file_name and mime_type:
        icon_name = mime.get_mime_icon(mime_type)
        if icon_name:
            file_name = _get_icon_file_name(icon_name)

    if not file_name or not os.path.exists(file_name):
        file_name = _get_icon_file_name('application-octet-stream')

    _icon_cache[cache_key] = file_name

    return file_name

def get_date(metadata):
    """ Convert from a string in iso format to a more human-like format. """
    if metadata.has_key('timestamp'):
        timestamp = float(metadata['timestamp'])
        return util.timestamp_to_elapsed_string(timestamp)
    elif metadata.has_key('mtime'):
        ti = time.strptime(metadata['mtime'], "%Y-%m-%dT%H:%M:%S")
        return util.timestamp_to_elapsed_string(time.mktime(ti))
    else:
        return _('No date')

def get_bundle(metadata):
    try:
        #TODO: figure out the best place to get rid of that temp file
        file_path = model.get_file(metadata['uid'])
        if is_activity_bundle(metadata) and os.path.exists(file_path):
            return ActivityBundle(file_path)
        elif is_content_bundle(metadata) and os.path.exists(file_path):
            return ContentBundle(file_path)
        elif is_journal_bundle(metadata) and os.path.exists(file_path):
            return JournalEntryBundle(file_path)
        else:
            return None
    except MalformedBundleException, e:
        logging.warning('Incorrect bundle: %r' % e)
        return None

def _get_activities_for_mime(mime_type):
    registry = bundleregistry.get_registry()
    result = registry.get_activities_for_type(mime_type)
    if not result:
        for parent_mime in mime.get_mime_parents(mime_type):
            result.extend(registry.get_activities_for_type(parent_mime))
    return result

def get_activities(metadata):
    activities = []

    bundle_id = metadata.get('activity', '')
    if bundle_id:
        activity_info = bundleregistry.get_registry().get_bundle(bundle_id)
        if activity_info:
            activities.append(activity_info)

    mime_type = metadata.get('mime_type', '')
    if mime_type:
        activities_info = _get_activities_for_mime(mime_type)
        for activity_info in activities_info:
            if activity_info.get_bundle_id() != bundle_id:
                activities.append(activity_info)

    return activities

def resume(metadata, bundle_id=None):
    registry = bundleregistry.get_registry()

    if is_activity_bundle(metadata) and bundle_id is None:

        logging.debug('Creating activity bundle')
        #TODO: figure out the best place to get rid of that temp file
        file_path = model.get_file(metadata['uid'])
        bundle = ActivityBundle(file_path)
        if not registry.is_installed(bundle):
            logging.debug('Installing activity bundle')
            registry.install(bundle)
        else:
            logging.debug('Upgrading activity bundle')
            registry.upgrade(bundle)

        logging.debug('activityfactory.creating bundle with id %r',
                        bundle.get_bundle_id())
        installed_bundle = registry.get_bundle(bundle.get_bundle_id())
        if installed_bundle:
            activityfactory.create(installed_bundle)
        else:
            logging.error('Bundle %r is not installed.',
                          bundle.get_bundle_id())

    elif is_content_bundle(metadata) and bundle_id is None:

        logging.debug('Creating content bundle')
        #TODO: figure out the best place to get rid of that temp file
        file_path = model.get_file(metadata['uid'])
        bundle = ContentBundle(file_path)
        if not bundle.is_installed():
            logging.debug('Installing content bundle')
            bundle.install()

        activities = _get_activities_for_mime('text/html')
        if len(activities) == 0:
            logging.warning('No activity can open HTML content bundles')
            return

        uri = bundle.get_start_uri()
        logging.debug('activityfactory.creating with uri %s', uri)

        activity_bundle = registry.get_bundle(activities[0].get_bundle_id())
        activityfactory.create_with_uri(activity_bundle, bundle.get_start_uri())
    else:
        if bundle_id is None:
            activities = get_activities(metadata)
            if not activities:
                logging.warning('No activity can open this object, %s.' %
                        metadata.get('mime_type', None))
                return
            bundle_id = activities[0].get_bundle_id()

        bundle = registry.get_bundle(bundle_id)

        activity_id = metadata['activity_id']

        if metadata['mountpoint'] == '/':
            object_id = metadata['uid']
        else:
            object_id = model.copy(metadata, '/')

        if activity_id is None:
            handle = ActivityHandle(object_id=object_id,
                                    activity_id=activity_id)
            activityfactory.create(bundle, handle)
        else:
            activityfactory.create_with_object_id(bundle, object_id)

def is_activity_bundle(metadata):
    return metadata['mime_type'] in \
            [ActivityBundle.MIME_TYPE, ActivityBundle.DEPRECATED_MIME_TYPE]

def is_content_bundle(metadata):
    return metadata['mime_type'] == ContentBundle.MIME_TYPE

def is_journal_bundle(metadata):
    return metadata['mime_type'] == JournalEntryBundle.MIME_TYPE

def is_bundle(metadata):
    return is_activity_bundle(metadata) or is_content_bundle(metadata) or \
            is_journal_bundle(metadata)

