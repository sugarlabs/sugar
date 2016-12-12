# Copyright (C) 2007, One Laptop Per Child
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
from urlparse import urlparse
import hashlib

from gi.repository import Gtk
from gi.repository import Gdk

from jarabe.frame.framewindow import FrameWindow
from jarabe.frame.clipboardtray import ClipboardTray

from jarabe.frame import clipboard


class ClipboardPanelWindow(FrameWindow):

    def __init__(self, frame, orientation):
        FrameWindow.__init__(self, orientation)

        self._frame = frame

        # Listening for new clipboard objects
        # NOTE: we need to keep a reference to Gtk.Clipboard in order to keep
        # listening to it.
        self._clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self._clipboard.connect('owner-change', self._owner_change_cb)

        self._clipboard_tray = ClipboardTray()
        self._clipboard_tray.show()
        self.append(self._clipboard_tray)

        # Receiving dnd drops
        self.drag_dest_set(0, [], 0)
        self.connect('drag_motion', self._clipboard_tray.drag_motion_cb)
        self.connect('drag_leave', self._clipboard_tray.drag_leave_cb)
        self.connect('drag_drop', self._clipboard_tray.drag_drop_cb)
        self.connect('drag_data_received',
                     self._clipboard_tray.drag_data_received_cb)

    def _owner_change_cb(self, x_clipboard, event):
        logging.debug('owner_change_cb')

        if self._clipboard_tray.owns_clipboard():
            return

        cb_service = clipboard.get_instance()

        result, targets = x_clipboard.wait_for_targets()
        cb_selections = []
        if not result:
            return

        target_is_uri = False
        for target in targets:
            if target not in ('TIMESTAMP', 'TARGETS',
                              'MULTIPLE', 'SAVE_TARGETS'):
                logging.debug('Asking for target %s.', target)
                if target == 'text/uri-list':
                    target_is_uri = True

                selection = x_clipboard.wait_for_contents(target)
                if not selection:
                    logging.warning('no data for selection target %s.', target)
                    continue
                cb_selections.append(selection)

        if target_is_uri:
            uri = selection.get_uris()[0]
            filename = uri[len('file://'):].strip()
            md5 = self._md5_for_file(filename)
            data_hash = hash(md5)
        else:
            data_hash = hash(selection.get_data())

        if len(cb_selections) > 0:
            key = cb_service.add_object(name="", data_hash=data_hash)
            if key is None:
                return
            cb_service.set_object_percent(key, percent=0)
            for selection in cb_selections:
                self._add_selection(key, selection)
            cb_service.set_object_percent(key, percent=100)

    def _md5_for_file(self, file_name):
        '''Calculate md5 for file data

        Calculating block wise to prevent issues with big files in memory
        '''
        block_size = 8192
        md5 = hashlib.md5()
        f = open(file_name, 'r')
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        f.close()
        return md5.digest()

    def _add_selection(self, key, selection):
        if not selection.get_data():
            logging.warning('no data for selection target %s.',
                            selection.get_data_type())
            return

        selection_type = str(selection.get_data_type())
        logging.debug('adding type ' + selection_type + '.')

        cb_service = clipboard.get_instance()
        if selection_type == 'text/uri-list':
            uris = selection.get_uris()

            if len(uris) > 1:
                raise NotImplementedError('Multiple uris in text/uri-list'
                                          ' still not supported.')
            uri = uris[0]
            scheme, netloc_, path_, parameters_, query_, fragment_ = \
                urlparse(uri)
            on_disk = (scheme == 'file')

            cb_service.add_object_format(key,
                                         selection_type,
                                         uri,
                                         on_disk)
        else:
            cb_service.add_object_format(key,
                                         selection_type,
                                         selection.get_data(),
                                         on_disk=False)
