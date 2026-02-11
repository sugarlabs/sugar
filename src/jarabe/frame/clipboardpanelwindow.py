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
from urllib.parse import urlparse
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
        # NOTE: we need to keep a reference to Gdk.Clipboard in order to keep
        # listening to it.
        self._clipboard = Gtk.Display.get_default().get_clipboard()
        self._clipboard.connect('changed', self._owner_change_cb)

        self._clipboard_tray = ClipboardTray()
        self._clipboard_tray.show()
        self.append(self._clipboard_tray)

        # Receiving dnd drops
        self.drag_dest_set(0, [], 0)
        self.connect('drag-motion', self._clipboard_tray.drag_motion_cb)
        self.connect('drag-leave', self._clipboard_tray.drag_leave_cb)
        self.connect('drag-drop', self._clipboard_tray.drag_drop_cb)
        self.connect('drag-data-received',
                     self._clipboard_tray.drag_data_received_cb)

    def _owner_change_cb(self, clipboard):
        logging.debug('owner_change_cb')

        if self._clipboard_tray.owns_clipboard():
            return

        cb_service = clipboard.get_instance()

        content = clipboard.get_content()

        if not content:
            return

        formats = content.ref_formats()

        if formats.is_empty():
            return

        mime_types = formats.get_mime_types()
        content_is_uri = False
        for mime_type in mime_types:
            if mime_type == 'text/uri-list':
                content_is_uri = True
                mt = mime_type

        if content_is_uri:
            uri = content.get_value()
            filename = uri[len('file://'):].strip()
            md5 = self._md5_for_file(filename)
            data_hash = hash(md5)
        else:
            data_hash = hash(content.get_value())

        key = cb_service.add_object(name="", data_hash=data_hash)
        if key is None:
            return
        cb_service.set_object_percent(key, percent=0)
        self._add_content(key, content, mt)
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

    def _add_content(self, key, content, mime_type):
        result, value = content.get_value()
        if not result:
            logging.warning('no data for content %s.',
                            mime_type)
            return

        logging.debug('adding type ' + mime_type + '.')
        cb_service = clipboard.get_instance()
        if mime_type == 'text/uri-list':
            uri = content.get_value()

            scheme, netloc_, path_, parameters_, query_, fragment_ = \
                urlparse(uri)
            on_disk = (scheme == 'file')

            cb_service.add_object_format(key,
                                         mime_type,
                                         uri,
                                         on_disk)
        else:
            cb_service.add_object_format(key,
                                         mime_type,
                                         content.get_value(),
                                         on_disk=False)
