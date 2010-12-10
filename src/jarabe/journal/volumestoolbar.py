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
import os
from gettext import gettext as _
import cPickle
import xapian
import json
import tempfile
import shutil

import gobject
import gio
import gtk
import gconf

from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.palette import Palette
from sugar.graphics.xocolor import XoColor

from jarabe.journal import model
from jarabe.view.palettes import VolumePalette

_JOURNAL_0_METADATA_DIR = '.olpc.store'

def _get_id(document):
    """Get the ID for the document in the xapian database."""
    tl = document.termlist()
    try:
        term = tl.skip_to('Q').term
        if len(term) == 0 or term[0] != 'Q':
            return None
        return term[1:]
    except StopIteration:
        return None

def _convert_entries(root):
    """Converts the entries written by the datastore version 0.
    The metadata and the preview will be written using the new
    scheme for writing Journal entries to removable storage
    devices.

    - entries that do not have an associated file are not
    converted.
    - when done we write the file converted to the old metadat
    directory, that we do not convert several times

    """
    try:
        database = xapian.Database(os.path.join(root, _JOURNAL_0_METADATA_DIR,
                                                'index'))
    except xapian.DatabaseError, e:
        logging.error('Convert DS-0 Journal entry. Error reading db: %s',
                      os.path.join(root, _JOURNAL_0_METADATA_DIR, 'index'))
        return

    metadata_dir_path = os.path.join(root, model.JOURNAL_METADATA_DIR)
    if not os.path.exists(metadata_dir_path):
        os.mkdir(metadata_dir_path)

    for i in range(1, database.get_lastdocid() + 1):
        try:
            document = database.get_document(i)
        except xapian.DocNotFoundError, e:
            logging.debug('Convert DS-0 Journal entry. ' \
                              'Error getting document %s: %s', i, e)
            continue

        try:
            metadata_loaded = cPickle.loads(document.get_data())
        except cPickle.PickleError, e:
            logging.debug('Convert DS-0 Journal entry. ' \
                              'Error converting metadata: %s', e)
            continue

        if 'activity_id' in metadata_loaded and \
                'mime_type' in metadata_loaded and \
                'title' in metadata_loaded:
            metadata = {}

            uid = _get_id(document)
            if uid is None:
                continue

            for key, value in metadata_loaded.items():
                metadata[str(key)] = str(value[0])

            if 'uid' not in metadata:
                metadata['uid'] = uid

            if 'filename' in metadata:
                filename = metadata['filename']
            else:
                continue
            if not os.path.exists(os.path.join(root, filename)):
                continue

            preview_path = os.path.join(root, _JOURNAL_0_METADATA_DIR,
                                        'preview', uid)
            if os.path.exists(preview_path):
                preview_fname = filename + '.preview'
                new_preview_path = os.path.join(root,
                                                model.JOURNAL_METADATA_DIR,
                                                preview_fname)
                if not os.path.exists(new_preview_path):
                    metadata['preview'] = preview_fname
                    shutil.copy(preview_path, new_preview_path)

            metadata_fname = filename + '.metadata'
            metadata_path = os.path.join(root, model.JOURNAL_METADATA_DIR,
                                         metadata_fname)
            if not os.path.exists(metadata_path):
                (fh, fn) = tempfile.mkstemp(dir=root)
                os.write(fh, json.dumps(metadata))
                os.close(fh)
                os.rename(fn, metadata_path)

            logging.debug('Convert DS-0 Journal entry. Entry converted: ' \
                              'File=%s Metadata=%s',
                          os.path.join(root, filename), metadata)


class VolumesToolbar(gtk.Toolbar):
    __gtype_name__ = 'VolumesToolbar'

    __gsignals__ = {
        'volume-changed': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([str])),
        'volume-error': (gobject.SIGNAL_RUN_FIRST,
                         gobject.TYPE_NONE,
                         ([str, str]))
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)
        self._mount_added_hid = None
        self._mount_removed_hid = None

        button = JournalButton()
        button.set_palette(Palette(_('Journal')))
        button.connect('toggled', self._button_toggled_cb)
        self.insert(button, 0)
        button.show()
        self._volume_buttons = [button]

        self.connect('destroy', self.__destroy_cb)

        gobject.idle_add(self._set_up_volumes)

    def __destroy_cb(self, widget):
        volume_monitor = gio.volume_monitor_get()
        volume_monitor.disconnect(self._mount_added_hid)
        volume_monitor.disconnect(self._mount_removed_hid)

    def _set_up_volumes(self):
        volume_monitor = gio.volume_monitor_get()
        self._mount_added_hid = \
                volume_monitor.connect('mount-added', self.__mount_added_cb)
        self._mount_removed_hid = \
                volume_monitor.connect('mount-removed', self.__mount_removed_cb)

        for mount in volume_monitor.get_mounts():
            self._add_button(mount)

    def __mount_added_cb(self, volume_monitor, mount):
        self._add_button(mount)

    def __mount_removed_cb(self, volume_monitor, mount):
        self._remove_button(mount)

    def _add_button(self, mount):
        logging.debug('VolumeToolbar._add_button: %r' % mount.get_name())

        if os.path.exists(os.path.join(mount.get_root().get_path(),
                                       _JOURNAL_0_METADATA_DIR)):
            logging.debug('Convert DS-0 Journal entries.')
            gobject.idle_add(_convert_entries, mount.get_root().get_path())

        button = VolumeButton(mount)
        button.props.group = self._volume_buttons[0]
        button.connect('toggled', self._button_toggled_cb)
        button.connect('volume-error', self.__volume_error_cb)
        position = self.get_item_index(self._volume_buttons[-1]) + 1
        self.insert(button, position)
        button.show()

        self._volume_buttons.append(button)

        if len(self.get_children()) > 1:
            self.show()

    def __volume_error_cb(self, button, strerror, severity):
        self.emit('volume-error', strerror, severity)

    def _button_toggled_cb(self, button):
        if button.props.active:
            self.emit('volume-changed', button.mount_point)

    def _unmount_activated_cb(self, menu_item, mount):
        logging.debug('VolumesToolbar._unmount_activated_cb: %r', mount)
        mount.unmount(self.__unmount_cb)

    def __unmount_cb(self, source, result):
        logging.debug('__unmount_cb %r %r' % (source, result))

    def _get_button_for_mount(self, mount):
        mount_point = mount.get_root().get_path()    
        for button in self.get_children():
            if button.mount_point == mount_point:
                return button
        logging.error('Couldnt find button with mount_point %r' % mount_point)
        return None

    def _remove_button(self, mount):
        button = self._get_button_for_mount(mount)
        self._volume_buttons.remove(button)
        self.remove(button)
        self.get_children()[0].props.active = True

        if len(self.get_children()) < 2:
            self.hide()

    def set_active_volume(self, mount):
        button = self._get_button_for_mount(mount)
        button.props.active = True

class BaseButton(RadioToolButton):
    __gsignals__ = {
        'volume-error': (gobject.SIGNAL_RUN_FIRST,
                         gobject.TYPE_NONE,
                         ([str, str]))
        }

    def __init__(self, mount_point):
        RadioToolButton.__init__(self)

        self.mount_point = mount_point

        self.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                           [('journal-object-id', 0, 0)],
                           gtk.gdk.ACTION_COPY)
        self.connect('drag-data-received', self._drag_data_received_cb)

    def _drag_data_received_cb(self, widget, drag_context, x, y, selection_data,
                               info, timestamp):
        object_id = selection_data.data
        metadata = model.get(object_id)
        file_path = model.get_file(metadata['uid'])

        if not file_path or not os.path.exists(file_path):
            logging.warn('Entries without a file cannot be copied.')
            self.emit('volume-error',
                      _('Entries without a file cannot be copied.'),
                      _('Warning'))
            return

        try:
            model.copy(metadata, self.mount_point)
        except (IOError, OSError), e:
            logging.exception('Error while copying the entry. %s', e.strerror)
            self.emit('volume-error',
                      _('Error while copying the entry. %s') % e.strerror,
                      _('Error'))

class VolumeButton(BaseButton):
    def __init__(self, mount):
        self._mount = mount
        mount_point = mount.get_root().get_path()
        BaseButton.__init__(self, mount_point)

        icon_name = None
        icon_theme = gtk.icon_theme_get_default()
        for icon_name in mount.get_icon().props.names:
            icon_info = icon_theme.lookup_icon(icon_name,
                                               gtk.ICON_SIZE_LARGE_TOOLBAR, 0)
            if icon_info is not None:
                break

        if icon_name is None:
            icon_name = 'drive'

        self.props.named_icon = icon_name
        
        # TODO: retrieve the colors from the owner of the device
        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self.props.xo_color = color

    def create_palette(self):
        palette = VolumePalette(self._mount)
        #palette.props.invoker = FrameWidgetInvoker(self)
        #palette.set_group_id('frame')
        return palette

class JournalButton(BaseButton):
    def __init__(self):
        BaseButton.__init__(self, mount_point='/')

        self.props.named_icon = 'computer-xo'

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self.props.xo_color = color

