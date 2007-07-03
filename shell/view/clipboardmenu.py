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
import hippo

from sugar.graphics.palette import Palette
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import color
from sugar.graphics import font
from sugar.activity import activityfactory
from sugar.activity.bundle import Bundle
from sugar.clipboard import clipboardservice
from sugar.datastore import datastore
from sugar.objects import mime
from sugar import profile
from sugar import util

class ClipboardMenu(Palette):
    
    def __init__(self, object_id, name, percent, preview, activity, installable):
        Palette.__init__(self, name)

        self._object_id = object_id
        self._percent = percent
        self._activity = activity

        if percent < 100:        
            self._progress_bar = gtk.ProgressBar()
            self._update_progress_bar()

            self.set_content(self._progress_bar)   
            self._progress_bar.show()         
        else:
            self._progress_bar = None

        """
        if preview:
            self._preview_text = hippo.CanvasText(text=preview,
                    size_mode=hippo.CANVAS_SIZE_WRAP_WORD)
            self._preview_text.props.color = color.LABEL_TEXT.get_int()
            self._preview_text.props.font_desc = font.DEFAULT.get_pango_desc()        
            self.append(self._preview_text)
        """

        self._remove_item = gtk.MenuItem(_('Remove')) #, 'theme:stock-remove')
        self._remove_item.connect('activate', self._remove_item_activate_cb)
        self.append_menu_item(self._remove_item)

        self._open_item = gtk.MenuItem(_('Open')) #, 'theme:stock-keep')
        self._open_item.connect('activate', self._open_item_activate_cb)
        self.append_menu_item(self._open_item)

        self._stop_item = gtk.MenuItem(_('Stop download')) #, 'theme:stock-close')
        # TODO: Implement stopping downloads
        #self._stop_item.connect('activate', self._stop_item_activate_cb)
        self.append_menu_item(self._stop_item)

        self._journal_item = gtk.MenuItem(_('Add to journal')) #, 'theme:document-save')
        self._journal_item.connect('activate', self._journal_item_activate_cb)
        self.append_menu_item(self._journal_item)

        self._update_items_visibility(installable)

    def _update_items_visibility(self, installable):
        if self._percent == 100 and (self._activity or installable):
            self._remove_item.show()
            self._open_item.show()
            self._stop_item.hide()
            self._journal_item.show()
        elif self._percent == 100 and (not self._activity and not installable):
            self._remove_item.show()
            self._open_item.hide()
            self._stop_item.hide()
            self._journal_item.show()
        else:
            self._remove_item.hide()
            self._open_item.hide()
            self._stop_item.show()
            self._journal_item.hide()

    def _update_progress_bar(self):
        if self._progress_bar:
            self._progress_bar.props.fraction = self._percent / 100.0
            self._progress_bar.props.text = '%.2f %%' % self._percent

    def set_state(self, name, percent, preview, activity, installable):
        self.set_primary_text(name)
        self._percent = percent
        self._activity = activity
        if self._progress_bar:
            self._update_progress_bar()
            self._update_items_visibility(installable)

    def _open_item_activate_cb(self, menu_item):
        if self._percent < 100:
            return

        # Get the file path
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        formats = obj['FORMATS']
        if len(formats) == 0:
            return

        if not self._activity and \
                not formats[0] == 'application/vnd.olpc-x-sugar':
            return

        uri = cb_service.get_object_data(self._object_id, formats[0])['DATA']
        if not uri.startswith('file://'):
            return

        (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(uri)

        # FIXME: would be better to check for format.onDisk
        try:
            path_exists = os.path.exists(path)
        except TypeError:
            path_exists = False

        if path_exists:
            if self._activity:
                activityfactory.create_with_uri(self._activity, uri)
            else:
                self._install_xo(path)
        else:
            logging.debug("Clipboard item file path %s didn't exist" % path)

    def _remove_item_activate_cb(self, menu_item):
        cb_service = clipboardservice.get_instance()
        cb_service.delete_object(self._object_id)

    def _journal_item_activate_cb(self, menu_item):
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)

        format = util.choose_most_significant_mime_type(obj['FORMATS'])
        data = cb_service.get_object_data(self._object_id, format)

        if format == 'text/uri-list':
            file_path = urlparse.urlparse(data['DATA']).path
            mime_type = mime.get_for_file(file_path)
        else:
            if data['ON_DISK']:
                file_path = urlparse.urlparse(data['DATA']).path
            else:
                f, file_path = tempfile.mkstemp()
                try:
                    os.write(f, data['DATA'])
                finally:
                    os.close(f)
            mime_type = format

        jobject = datastore.create()
        jobject.metadata['title'] = _('Clipboard object: %s.') % obj['NAME']
        jobject.metadata['keep'] = '0'
        jobject.metadata['buddies'] = ''
        jobject.metadata['preview'] = ''
        jobject.metadata['icon-color'] = profile.get_color().to_string()
        jobject.metadata['mime_type'] = mime_type
        jobject.file_path = file_path
        datastore.write(jobject)

    def _install_xo(self, path):
        bundle = Bundle(path)
        if not bundle.is_installed():
            bundle.install()

