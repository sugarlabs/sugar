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
from gi.repository import Gio

from gi.repository import Gtk

from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.modal import SelectorModal
from sugar3.graphics.menuitem import MenuItem
from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.datastore import datastore
from sugar3 import mime
from sugar3 import env
from sugar3 import profile
from sugar3.activity.i18n import pgettext

import jarabe.frame
from jarabe.frame import clipboard
from jarabe.journal import misc
from jarabe.model import bundleregistry


class ClipboardMenu(Palette):

    def __init__(self, cb_object):
        Palette.__init__(self, text_maxlen=100)
        box = PaletteMenuBox()
        self.set_content(box)
        box.show()

        self._cb_object = cb_object

        self.set_group_id('frame')

        cb_service = clipboard.get_instance()
        cb_service.connect('object-state-changed',
                           self._object_state_changed_cb)

        self._remove_item = PaletteMenuItem(pgettext('Clipboard', 'Remove'),
                                            'list-remove')
        self._remove_item.connect('activate', self._remove_item_activate_cb)
        box.append_item(self._remove_item)
        self._remove_item.show()

        self._open_item = PaletteMenuItem(_('Open'), 'zoom-activity')
        self._open_item.connect('activate', self._open_item_activate_cb)
        box.append_item(self._open_item)
        self._open_item.show()

        color = profile.get_color()
        self._journal_item = PaletteMenuItem(_('Keep'), 'document-save',
                                             xo_color=color)
        self._journal_item.connect('activate', self._journal_item_activate_cb)
        box.append_item(self._journal_item)
        self._journal_item.show()

        self._update()

    def _update_open(self):
        activities = self._get_activities()
        logging.debug('_update_open_submenu: %r', activities)

        if activities is None or len(activities) <= 1:
            self._open_item.set_label(_('Open'))
            self._open_item.set_has_modal(False)
        else:
            self._open_item.set_label(_('Open with'))
            self._open_item.set_has_modal(True)

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

    def _get_activities(self):
        mime_type = self._cb_object.get_mime_type()
        if not mime_type:
            return ''

        registry = bundleregistry.get_registry()
        activities = registry.get_activities_for_type(mime_type)
        if activities:
            return activities
        else:
            return ''

    def _object_state_changed_cb(self, cb_service, cb_object):
        if cb_object != self._cb_object:
            return
        self._update()

    def _update(self):
        self.props.primary_text = self._cb_object.get_name()
        preview = self._cb_object.get_preview()
        if preview:
            self.props.secondary_text = preview
        self._update_items_visibility()
        self._update_open()

    def _open_item_activate_cb(self, menu_item):
        logging.debug('_open_item_activate_cb')
        percent = self._cb_object.get_percent()
        if percent < 100:
            return

        activities = self._get_activities()
        if len(activities) == 1:
            jobject = self._copy_to_journal()
            misc.resume(jobject.metadata,
                        self._get_activities()[0].get_bundle_id())
            jobject.destroy()
        else:
            modal = SelectorModal()
            # TRANS:  <i>%s</i> will be replaces with the object name
            modal.props.title = \
                _('Open <i>%s</i> with') % self._cb_object.get_name()
            for activity in activities:
                modal.model.add_item(activity.get_name(),
                                     icon_file=activity.get_icon(),
                                     data=activity.get_bundle_id())

            modal.item_selected_signal.connect(self.__modal_item_selected_cb)
            modal.cancel_clicked_signal.connect(self.__modal_cancel_cb)
            jarabe.frame.get_view().hide()
            modal.show()

    def __modal_item_selected_cb(self, modal, bundle_id):
        jobject = self._copy_to_journal()
        misc.resume(jobject.metadata, bundle_id)
        jobject.destroy()

    def __modal_cancel_cb(self, modal):
        jarabe.frame.get_view().show()
        self.popup()

    def _remove_item_activate_cb(self, menu_item):
        cb_service = clipboard.get_instance()
        cb_service.delete_object(self._cb_object.get_id())

    def _journal_item_activate_cb(self, menu_item):
        logging.debug('_journal_item_activate_cb')
        jobject = self._copy_to_journal()
        jobject.destroy()

    def _write_to_temp_file(self, data):
        tmp_dir = os.path.join(env.get_profile_path(), 'data')
        f, file_path = tempfile.mkstemp(dir=tmp_dir)
        try:
            os.write(f, data)
        finally:
            os.close(f)
        return file_path

    def _copy_to_journal(self):
        formats = self._cb_object.get_formats().keys()
        most_significant_mime_type = mime.choose_most_significant(formats)
        format_ = self._cb_object.get_formats()[most_significant_mime_type]

        transfer_ownership = False
        if most_significant_mime_type == 'text/uri-list':
            uri = format_.get_data()
            if uri.startswith('file://'):
                parsed_url = urlparse.urlparse(uri)
                file_path = parsed_url.path  # pylint: disable=E1101
                transfer_ownership = False
                mime_type = mime.get_for_file(file_path)
            else:
                file_path = self._write_to_temp_file(format_.get_data())
                transfer_ownership = True
                mime_type = 'text/uri-list'
        else:
            if format_.is_on_disk():
                parsed_url = urlparse.urlparse(format_.get_data())
                file_path = parsed_url.path  # pylint: disable=E1101
                transfer_ownership = False
                mime_type = mime.get_for_file(file_path)
            else:
                file_path = self._write_to_temp_file(format_.get_data())
                transfer_ownership = True
                sniffed_mime_type = mime.get_for_file(file_path)
                if sniffed_mime_type == 'application/octet-stream':
                    mime_type = most_significant_mime_type
                else:
                    mime_type = sniffed_mime_type

        jobject = datastore.create()
        jobject.metadata['title'] = self._cb_object.get_name()
        jobject.metadata['keep'] = '0'
        jobject.metadata['buddies'] = ''
        jobject.metadata['preview'] = ''
        settings = Gio.Settings('org.sugarlabs.user')
        color = settings.get_string('color')
        jobject.metadata['icon-color'] = color
        jobject.metadata['mime_type'] = mime_type
        jobject.file_path = file_path

        datastore.write(jobject, transfer_ownership=transfer_ownership)

        return jobject
