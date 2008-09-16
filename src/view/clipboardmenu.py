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

from gettext import gettext as _
import tempfile
import urlparse
import os
import logging

import gtk

from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar.datastore import datastore
from sugar import mime
from sugar import profile
from sugar import activity

from model import clipboard
import journal.misc

class ClipboardMenu(Palette):

    def __init__(self, cb_object):
        Palette.__init__(self, cb_object.get_name())

        self._cb_object = cb_object

        self.set_group_id('frame')

        cb_service = clipboard.get_instance()
        cb_service.connect('object-state-changed',
                           self._object_state_changed_cb)

        self._progress_bar = None

        self._remove_item = MenuItem(_('Remove'), 'list-remove')
        self._remove_item.connect('activate', self._remove_item_activate_cb)
        self.menu.append(self._remove_item)
        self._remove_item.show()

        self._open_item = MenuItem(_('Open'), 'zoom-activity')
        self._open_item.connect('activate', self._open_item_activate_cb)
        self.menu.append(self._open_item)
        self._open_item.show()

        self._journal_item = MenuItem(_('Keep'))
        icon = Icon(icon_name='document-save', icon_size=gtk.ICON_SIZE_MENU,
                xo_color=profile.get_color())
        self._journal_item.set_image(icon)

        self._journal_item.connect('activate', self._journal_item_activate_cb)
        self.menu.append(self._journal_item)
        self._journal_item.show()

        self._update_items_visibility()
        self._update_open_submenu()

    def _update_open_submenu(self):
        activities = self._get_activities()
        logging.debug('_update_open_submenu: %r' % activities)
        child = self._open_item.get_child()
        if activities is None or len(activities) <= 1:
            child.set_text(_('Open'))
            if self._open_item.get_submenu() is not None:
                self._open_item.remove_submenu()
            return

        child.set_text(_('Open with'))
        submenu = self._open_item.get_submenu()
        if submenu is None:
            submenu = gtk.Menu()
            self._open_item.set_submenu(submenu)
            submenu.show()
        else:
            for item in submenu.get_children():
                submenu.remove(item)

        for service_name in activities:
            registry = activity.get_registry()
            activity_info = registry.get_activity(service_name)

            if not activity_info:
                logging.warning('Activity %s is unknown.' % service_name)

            item = gtk.MenuItem(activity_info.name)
            item.connect('activate', self._open_submenu_item_activate_cb,
                         service_name)
            submenu.append(item)
            item.show()

    def _update_items_visibility(self):
        activities = self._get_activities()
        installable = self._cb_object.is_bundle()
        percent = self._cb_object.get_percent()
        
        if percent == 100 and (activities or installable):
            self._remove_item.props.sensitive = True
            self._open_item.props.sensitive = True
            self._journal_item.props.sensitive = True
        elif percent == 100 and (not activities and not installable):
            self._remove_item.props.sensitive = True
            self._open_item.props.sensitive = False
            self._journal_item.props.sensitive = True
        else:
            self._remove_item.props.sensitive = True
            self._open_item.props.sensitive = False
            self._journal_item.props.sensitive = False

        self._update_progress_bar()

    def _get_activities(self):
        mime_type = self._cb_object.get_mime_type()
        if not mime_type:
            return ''

        registry = activity.get_registry()
        activities = registry.get_activities_for_type(mime_type)
        if activities:
            return [activity_info.bundle_id for activity_info in activities]
        else:
            return ''

    def _update_progress_bar(self):
        percent = self._cb_object.get_percent()
        if percent == 100.0:
            if self._progress_bar:
                self._progress_bar = None
                self.set_content(None)
        else:
            if self._progress_bar is None:
                self._progress_bar = gtk.ProgressBar()
                self._progress_bar.show()
                self.set_content(self._progress_bar)

            self._progress_bar.props.fraction = percent / 100.0
            self._progress_bar.props.text = '%.2f %%' % percent

    def _object_state_changed_cb(self, cb_service, cb_object):
        if cb_object != self._cb_object:
            return
        self.set_primary_text(cb_object.get_name())
        self._update_progress_bar()
        self._update_items_visibility()
        self._update_open_submenu()

    def _open_item_activate_cb(self, menu_item):
        logging.debug('_open_item_activate_cb')
        percent = self._cb_object.get_percent()
        if percent < 100 or menu_item.get_submenu() is not None:
            return
        jobject = self._copy_to_journal()
        journal.misc.resume(jobject, self._activities[0])
        jobject.destroy()

    def _open_submenu_item_activate_cb(self, menu_item, service_name):
        logging.debug('_open_submenu_item_activate_cb')
        percent = self._cb_object.get_percent()
        if percent < 100:
            return
        jobject = self._copy_to_journal()
        journal.misc.resume(jobject, service_name)
        jobject.destroy()

    def _remove_item_activate_cb(self, menu_item):
        cb_service = clipboard.get_instance()
        cb_service.delete_object(self._cb_object.get_id())

    def _journal_item_activate_cb(self, menu_item):
        logging.debug('_journal_item_activate_cb')
        jobject = self._copy_to_journal()
        jobject.destroy()

    def _write_to_temp_file(self, data):
        f, file_path = tempfile.mkstemp()
        try:
            os.write(f, data)
        finally:
            os.close(f)
        return file_path

    def _copy_to_journal(self):
        formats = self._cb_object.get_formats().keys()
        most_significant_mime_type = mime.choose_most_significant(formats)
        format = self._cb_object.get_formats()[most_significant_mime_type]

        transfer_ownership = False
        if most_significant_mime_type == 'text/uri-list':
            uris = mime.split_uri_list(format.get_data())
            if len(uris) == 1 and uris[0].startswith('file://'):
                file_path = urlparse.urlparse(uris[0]).path
                transfer_ownership = False
                mime_type = mime.get_for_file(file_path)
            else:
                file_path = self._write_to_temp_file(format.get_data())
                transfer_ownership = True
                mime_type = 'text/uri-list'
        else:
            if format.is_on_disk():
                file_path = urlparse.urlparse(format.get_data()).path
                transfer_ownership = False
                mime_type = mime.get_for_file(file_path)
            else:
                file_path = self._write_to_temp_file(format.get_data())
                transfer_ownership = True
                sniffed_mime_type = mime.get_for_file(file_path)
                if sniffed_mime_type == 'application/octet-stream':
                    mime_type = most_significant_mime_type
                else:
                    mime_type = sniffed_mime_type

        name = self._cb_object.get_name()
        jobject = datastore.create()
        jobject.metadata['title'] = _('%s clipping') % name
        jobject.metadata['keep'] = '0'
        jobject.metadata['buddies'] = ''
        jobject.metadata['preview'] = ''
        jobject.metadata['icon-color'] = profile.get_color().to_string()
        jobject.metadata['mime_type'] = mime_type
        jobject.file_path = file_path
        datastore.write(jobject, transfer_ownership=transfer_ownership)

        return jobject

