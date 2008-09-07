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
from sugar.clipboard import clipboardservice
from sugar.datastore import datastore
from sugar import mime
from sugar import profile
from sugar import activity

class ClipboardMenu(Palette):

    def __init__(self, object_id, name, percent, preview,
                 activities, installable):
        Palette.__init__(self, name)

        self._object_id = object_id
        self._percent = percent
        self._activities = activities

        self.set_group_id('frame')

        self._progress_bar = None

        self._remove_item = MenuItem(_('Remove'), 'list-remove')
        self._remove_item.connect('activate', self._remove_item_activate_cb)
        self.menu.append(self._remove_item)
        self._remove_item.show()

        self._open_item = MenuItem(_('Open'), 'zoom-activity')
        self._open_item.connect('activate', self._open_item_activate_cb)
        self.menu.append(self._open_item)
        self._open_item.show()

        #self._stop_item = MenuItem(_('Stop download'), 'stock-close')
        # TODO: Implement stopping downloads
        #self._stop_item.connect('activate', self._stop_item_activate_cb)
        #self.append_menu_item(self._stop_item)

        self._journal_item = MenuItem(_('Keep'))
        icon = Icon(icon_name='document-save', icon_size=gtk.ICON_SIZE_MENU,
                xo_color=profile.get_color())
        self._journal_item.set_image(icon)

        self._journal_item.connect('activate', self._journal_item_activate_cb)
        self.menu.append(self._journal_item)
        self._journal_item.show()

        self._update_items_visibility(installable)
        self._update_open_submenu()

    def _update_open_submenu(self):
        logging.debug('_update_open_submenu: %r' % self._activities)
        child = self._open_item.get_child()
        if self._activities is None or len(self._activities) <= 1:
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

        for service_name in self._activities:
            registry = activity.get_registry()
            activity_info = registry.get_activity(service_name)

            if not activity_info:
                logging.warning('Activity %s is unknown.' % service_name)

            item = gtk.MenuItem(activity_info.name)
            item.connect('activate', self._open_submenu_item_activate_cb,
                         service_name)
            submenu.append(item)
            item.show()

    def _update_items_visibility(self, installable):
        if self._percent == 100 and (self._activities or installable):
            self._remove_item.props.sensitive = True
            self._open_item.props.sensitive = True
            #self._stop_item.props.sensitive = False
            self._journal_item.props.sensitive = True
        elif self._percent == 100 and \
                    (not self._activities and not installable):
            self._remove_item.props.sensitive = True
            self._open_item.props.sensitive = False
            #self._stop_item.props.sensitive = False
            self._journal_item.props.sensitive = True
        else:
            self._remove_item.props.sensitive = True
            self._open_item.props.sensitive = False
            # TODO: reenable the stop item when we implement stoping downloads.
            #self._stop_item.props.sensitive = True
            self._journal_item.props.sensitive = False

        self._update_progress_bar()

    def _update_progress_bar(self):
        if self._percent == 100.0:
            if self._progress_bar:
                self._progress_bar = None
                self.set_content(None)
        else:
            if self._progress_bar is None:
                self._progress_bar = gtk.ProgressBar()
                self._progress_bar.show()
                self.set_content(self._progress_bar)

            self._progress_bar.props.fraction = self._percent / 100.0
            self._progress_bar.props.text = '%.2f %%' % self._percent

    def update_state(self, name, percent, preview, activities, installable):
        self.set_primary_text(name)
        self._percent = percent
        self._activities = activities
        self._update_progress_bar()
        self._update_items_visibility(installable)
        self._update_open_submenu()

    def _open_item_activate_cb(self, menu_item):
        logging.debug('_open_item_activate_cb')
        if self._percent < 100 or menu_item.get_submenu() is not None:
            return
        jobject = self._copy_to_journal()
        jobject.resume(self._activities[0])
        jobject.destroy()

    def _open_submenu_item_activate_cb(self, menu_item, service_name):
        logging.debug('_open_submenu_item_activate_cb')
        if self._percent < 100:
            return
        jobject = self._copy_to_journal()
        jobject.resume(service_name)
        jobject.destroy()

    def _remove_item_activate_cb(self, menu_item):
        cb_service = clipboardservice.get_instance()
        cb_service.delete_object(self._object_id)

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
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)

        format = mime.choose_most_significant(obj['FORMATS'])
        data = cb_service.get_object_data(self._object_id, format)

        transfer_ownership = False
        if format == 'text/uri-list':
            uris = mime.split_uri_list(data['DATA'])
            if len(uris) == 1 and uris[0].startswith('file://'):
                file_path = urlparse.urlparse(uris[0]).path
                transfer_ownership = False
                mime_type = mime.get_for_file(file_path)
            else:
                file_path = self._write_to_temp_file(data['DATA'])
                transfer_ownership = True
                mime_type = 'text/uri-list'
        else:
            if data['ON_DISK']:
                file_path = urlparse.urlparse(data['DATA']).path
                transfer_ownership = False
                mime_type = mime.get_for_file(file_path)
            else:
                file_path = self._write_to_temp_file(data['DATA'])
                transfer_ownership = True
                sniffed_mime_type = mime.get_for_file(file_path)
                if sniffed_mime_type == 'application/octet-stream':
                    mime_type = format
                else:
                    mime_type = sniffed_mime_type

        jobject = datastore.create()
        jobject.metadata['title'] = _('Clipboard object: %s.') % obj['NAME']
        jobject.metadata['keep'] = '0'
        jobject.metadata['buddies'] = ''
        jobject.metadata['preview'] = ''
        jobject.metadata['icon-color'] = profile.get_color().to_string()
        jobject.metadata['mime_type'] = mime_type
        jobject.file_path = file_path
        datastore.write(jobject, transfer_ownership=transfer_ownership)

        return jobject

