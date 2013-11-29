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
import os
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GConf
from gi.repository import Gtk

from sugar3.activity import activityfactory
from sugar3.activity.activityhandle import ActivityHandle
from sugar3.graphics.icon import get_icon_file_name
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.alert import ConfirmationAlert
from sugar3 import mime
from sugar3.bundle.bundle import ZipExtractException, RegistrationException
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.bundle import AlreadyInstalledException
from sugar3.bundle.contentbundle import ContentBundle
from sugar3 import util

from jarabe.view import launcher
from jarabe.view import alerts
from jarabe.model import bundleregistry, shell
from jarabe.journal.journalentrybundle import JournalEntryBundle
from jarabe.journal import model
from jarabe.journal import journalwindow


def _get_icon_for_mime(mime_type):
    generic_types = mime.get_all_generic_types()
    for generic_type in generic_types:
        if mime_type in generic_type.mime_types:
            file_name = get_icon_file_name(generic_type.icon)
            if file_name is not None:
                return file_name

    icons = Gio.content_type_get_icon(mime_type)
    logging.debug('icons for this file: %r', icons.props.names)
    for icon_name in icons.props.names:
        file_name = get_icon_file_name(icon_name)
        if file_name is not None:
            return file_name


def get_mount_icon_name(mount, size):
    icon = mount.get_icon()
    if isinstance(icon, Gio.ThemedIcon):
        icon_theme = Gtk.IconTheme.get_default()
        for icon_name in icon.props.names:
            if icon_theme.lookup_icon(icon_name, size, 0) is not None:
                return icon_name
    logging.error('Cannot find icon name for %s, %s', icon, mount)
    return 'drive'


def get_icon_name(metadata):
    file_name = None

    bundle_id = metadata.get('activity', '')
    if not bundle_id:
        bundle_id = metadata.get('bundle_id', '')

    if bundle_id:
        activity_info = bundleregistry.get_registry().get_bundle(bundle_id)
        if activity_info:
            file_name = activity_info.get_icon()

    if file_name is None and is_activity_bundle(metadata):
        file_path = model.get_file(metadata['uid'])
        if file_path is not None and os.path.exists(file_path):
            try:
                bundle = ActivityBundle(file_path)
                file_name = bundle.get_icon()
            except Exception:
                logging.exception('Could not read bundle')

    if file_name is None:
        file_name = _get_icon_for_mime(metadata.get('mime_type', ''))

    if file_name is None:
        file_name = get_icon_file_name('application-octet-stream')

    return file_name


def get_date(metadata):
    """ Convert from a string in iso format to a more human-like format. """
    if 'timestamp' in metadata:
        try:
            timestamp = float(metadata['timestamp'])
        except (TypeError, ValueError):
            logging.warning('Invalid timestamp: %r', metadata['timestamp'])
        else:
            return util.timestamp_to_elapsed_string(timestamp)

    if 'mtime' in metadata:
        try:
            ti = time.strptime(metadata['mtime'], '%Y-%m-%dT%H:%M:%S')
        except (TypeError, ValueError):
            logging.warning('Invalid mtime: %r', metadata['mtime'])
        else:
            return util.timestamp_to_elapsed_string(time.mktime(ti))

    return _('No date')


def get_bundle(metadata):
    try:
        if is_activity_bundle(metadata):
            file_path = model.get_file(metadata['uid'])
            if not os.path.exists(file_path):
                logging.warning('Invalid path: %r', file_path)
                return None
            return ActivityBundle(file_path)

        elif is_content_bundle(metadata):
            file_path = model.get_file(metadata['uid'])
            if not os.path.exists(file_path):
                logging.warning('Invalid path: %r', file_path)
                return None
            return ContentBundle(file_path)

        elif is_journal_bundle(metadata):
            file_path = model.get_file(metadata['uid'])
            if not os.path.exists(file_path):
                logging.warning('Invalid path: %r', file_path)
                return None
            return JournalEntryBundle(file_path, metadata['uid'])
        else:
            return None
    except Exception:
        logging.exception('Incorrect bundle')
        return None


def _get_activities_for_mime(mime_type):
    registry = bundleregistry.get_registry()
    result = registry.get_activities_for_type(mime_type)
    if not result:
        for parent_mime in mime.get_mime_parents(mime_type):
            for activity in registry.get_activities_for_type(parent_mime):
                if activity not in result:
                    result.append(activity)
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
            if activity_info not in activities:
                activities.append(activity_info)

    return activities


def get_bundle_id_from_metadata(metadata):
    activities = get_activities(metadata)
    if not activities:
        logging.warning('No activity can open this object, %s.',
                        metadata.get('mime_type', None))
        return None
    return activities[0].get_bundle_id()


def resume(metadata, bundle_id=None, alert_window=None,
           force_bundle_downgrade=False):
    registry = bundleregistry.get_registry()

    ds_bundle, downgrade_required = \
        handle_bundle_installation(metadata, force_bundle_downgrade)

    if ds_bundle is not None and downgrade_required:
        # A bundle is being resumed but we didn't install it as that would
        # require a downgrade.
        _downgrade_option_alert(ds_bundle, metadata)
        return

    # Are we launching a bundle?
    if ds_bundle is not None and bundle_id is None:
        activity_bundle = registry.get_bundle(ds_bundle.get_bundle_id())
        if activity_bundle is not None:
            launch(activity_bundle)
        return

    # Otherwise we are launching a regular journal entry
    activity_id = metadata.get('activity_id', '')

    if bundle_id is None:
        activities = get_activities(metadata)
        if not activities:
            logging.warning('No activity can open this object, %s.',
                            metadata.get('mime_type', None))
            return
        bundle_id = activities[0].get_bundle_id()

    bundle = registry.get_bundle(bundle_id)

    if metadata.get('mountpoint', '/') == '/':
        object_id = metadata['uid']
    else:
        object_id = model.copy(metadata, '/')

    launch(bundle, activity_id=activity_id, object_id=object_id,
           color=get_icon_color(metadata), alert_window=alert_window)


def launch(bundle, activity_id=None, object_id=None, uri=None, color=None,
           invited=False, alert_window=None):

    bundle_id = bundle.get_bundle_id()

    if activity_id is None or not activity_id:
        activity_id = activityfactory.create_activity_id()

    logging.debug('launch bundle_id=%s activity_id=%s object_id=%s uri=%s',
                  bundle.get_bundle_id(), activity_id, object_id, uri)

    if isinstance(bundle, ContentBundle):
        # Content bundles are a special case: we treat them as launching
        # Browse with a specific URI.
        uri = bundle.get_start_uri()
        activities = _get_activities_for_mime('text/html')
        if len(activities) == 0:
            logging.error("No browser available for content bundle")
            return
        bundle = activities[0]
        logging.debug('Launching content bundle with uri %s', uri)

    shell_model = shell.get_model()
    activity = shell_model.get_activity_by_id(activity_id)
    if activity is not None:
        logging.debug('re-launch %r', activity.get_window())
        activity.get_window().activate(Gtk.get_current_event_time())
        return

    if not shell_model.can_launch_activity():
        if alert_window is None:
            from jarabe.desktop import homewindow
            alert_window = homewindow.get_instance()
        if alert_window is not None:
            alerts.show_max_open_activities_alert(alert_window)
        return

    if not shell_model.can_launch_activity_instance(bundle):
        if alert_window is None:
            from jarabe.desktop import homewindow
            alert_window = homewindow.get_instance()
        if alert_window is not None:
            alerts.show_multiple_instance_alert(
                alert_window, shell_model.get_name_from_bundle_id(bundle_id))
        return

    if color is None:
        client = GConf.Client.get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))

    launcher.add_launcher(activity_id, bundle.get_icon(), color)
    activity_handle = ActivityHandle(activity_id=activity_id,
                                     object_id=object_id,
                                     uri=uri,
                                     invited=invited)
    activityfactory.create(bundle, activity_handle)


def _downgrade_option_alert(bundle, metadata):
    alert = ConfirmationAlert()
    alert.props.title = _('Older Version Of %s Activity') % (bundle.get_name())
    alert.props.msg = _('Do you want to downgrade to version %s') % \
        bundle.get_activity_version()
    alert.connect('response', _downgrade_alert_response_cb, metadata)
    journalwindow.get_journal_window().add_alert(alert)
    alert.show()


def _downgrade_alert_response_cb(alert, response_id, metadata):
    journalwindow.get_journal_window().remove_alert(alert)
    if response_id is Gtk.ResponseType.OK:
        resume(metadata, force_bundle_downgrade=True)


def is_activity_bundle(metadata):
    mime_type = metadata.get('mime_type', '')
    return mime_type == ActivityBundle.MIME_TYPE


def is_content_bundle(metadata):
    return metadata.get('mime_type', '') == ContentBundle.MIME_TYPE


def is_journal_bundle(metadata):
    return metadata.get('mime_type', '') == JournalEntryBundle.MIME_TYPE


def is_bundle(metadata):
    return is_activity_bundle(metadata) or is_content_bundle(metadata) or \
        is_journal_bundle(metadata)


def can_resume(metadata):
    return get_activities(metadata) or is_bundle(metadata)


def handle_bundle_installation(metadata, force_downgrade=False):
    """
    Check metadata for a journal entry. If the metadata corresponds to a
    bundle, make sure that it is installed, and return the corresponding
    Bundle object.

    Installation sometimes requires a downgrade. Downgrades will not happen
    unless force_downgrade is set to True.

    Returns a tuple of two items:
    1. The corresponding Bundle object for the journal entry, or None if
       installation failed.
    2. A flag that indicates whether bundle installation was aborted due to
       a downgrade being required, and force_downgrade was False
    """
    if metadata.get('progress', '').isdigit():
        if int(metadata['progress']) < 100:
            return None, False

    bundle = get_bundle(metadata)
    if bundle is None:
        return None, False

    registry = bundleregistry.get_registry()
    try:
        installed = registry.install(bundle, force_downgrade)
    except AlreadyInstalledException:
        return bundle, True
    except (ZipExtractException, RegistrationException):
        logging.exception('Could not install bundle %s', bundle.get_path())
        return None, False

    # If we just installed a bundle, update the datastore accordingly.
    # We do not do this for JournalEntryBundles because the JEB code transforms
    # its own datastore entry and writes appropriate metadata.
    if installed and not isinstance(bundle, JournalEntryBundle):
        metadata['bundle_id'] = bundle.get_bundle_id()
        model.write(metadata)

    return bundle, False


def get_icon_color(metadata):
    if metadata is None or not 'icon-color' in metadata:
        client = GConf.Client.get_default()
        return XoColor(client.get_string('/desktop/sugar/user/color'))
    else:
        return XoColor(metadata['icon-color'])
