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

from gi.repository import Gdk
from gi.repository import GLib

from jarabe.frame.framewindow import FrameWindow
from jarabe.frame.clipboardtray import ClipboardTray

import jarabe.frame.clipboard as clipboard

# Clipboard target names that carry no data content.
_SKIP_TARGETS = frozenset([
    'TIMESTAMP', 'TARGETS', 'MULTIPLE', 'SAVE_TARGETS',
    'DELETE', 'INSERT_SELECTION', 'INSERT_PROPERTY',
])


class ClipboardPanelWindow(FrameWindow):

    def __init__(self, frame, orientation):
        FrameWindow.__init__(self, orientation)

        self._frame = frame

        # Listening for new clipboard objects.
        self._clipboard = Gdk.Display.get_default().get_clipboard()
        self._clipboard.connect('changed', self._owner_change_cb)

        self._clipboard_tray = ClipboardTray()
        self._clipboard_tray.set_visible(True)
        self.append(self._clipboard_tray)

    def _owner_change_cb(self, cb):
        logging.debug('owner_change_cb')

        if self._clipboard_tray.owns_clipboard():
            return

        formats = cb.get_formats()
        if formats is None:
            return

        mime_types = formats.get_mime_types()
        if not mime_types:
            return

        # Filter out internal/control targets â€” same as GTK3 baseline.
        targets = [t for t in mime_types if t not in _SKIP_TARGETS]
        if not targets:
            return

        cb_service = clipboard.get_instance()
        
        # Read all targets asynchronously; track how many are still pending.
        state = {'pending': len(targets), 'key': None, 'data_hash': None, 'cancelled': False}
        for mime_type in targets:
            cb.read_async(
                [mime_type],
                GLib.PRIORITY_DEFAULT,
                None,
                self._read_mime_cb,
                (cb_service, mime_type, state))

    # ------------------------------------------------------------------
    # Async reading chain
    # ------------------------------------------------------------------

    def _read_mime_cb(self, cb, result, user_data):
        cb_service, mime_type, state = user_data
        try:
            stream, _ = cb.read_finish(result)
            if stream:
                stream.read_bytes_async(
                    65536,
                    GLib.PRIORITY_DEFAULT,
                    None,
                    self._read_bytes_cb,
                    (cb_service, mime_type, state, stream))
                return
        except Exception as e:
            logging.debug('Could not read clipboard mime %s: %s', mime_type, e)

        # Count this target as done even on failure.
        self._check_complete(cb_service, state)

    def _read_bytes_cb(self, stream, result, user_data):
        cb_service, mime_type, state, _ = user_data
        try:
            raw = stream.read_bytes_finish(result)
            data = raw.get_data() if raw else None
            if data and not state['cancelled']:
                on_disk = False
                if mime_type == 'text/uri-list':
                    # Mirror GTK3 _add_selection(): extract first URI,
                    # determine on_disk, compute data_hash from file md5.
                    text = data.decode('utf-8', errors='replace')
                    uris = [u.strip() for u in text.splitlines()
                            if u.strip() and not u.strip().startswith('#')]
                    if uris:
                        uri = uris[0]
                        scheme = urlparse(uri).scheme
                        on_disk = (scheme == 'file')
                        if on_disk and state['data_hash'] is None:
                            filename = urlparse(uri).path
                            state['data_hash'] = hash(
                                self._md5_for_file(filename))
                        data = uri
                else:
                    if state['data_hash'] is None:
                        state['data_hash'] = hash(data)
                    # Decode text/* to str; keep binary as bytes.
                    if mime_type.startswith('text/'):
                        try:
                            data = data.decode('utf-8', errors='replace')
                        except Exception:
                            pass
                            
                if state['key'] is None:
                    # Create the clipboard object now that we have a hash
                    state['key'] = cb_service.add_object(name='', data_hash=state['data_hash'])
                    if state['key'] is None:
                        state['cancelled'] = True
                    else:
                        cb_service.set_object_percent(state['key'], percent=0)
                
                if not state['cancelled']:
                    cb_service.add_object_format(
                        state['key'], mime_type, data, on_disk=on_disk)
        except Exception as e:
            logging.debug('Error reading bytes for %s: %s', mime_type, e)

        self._check_complete(cb_service, state)

    def _check_complete(self, cb_service, state):
        state['pending'] -= 1
        if state['pending'] <= 0 and state['key'] is not None and not state['cancelled']:
            cb_service.set_object_percent(state['key'], percent=100)

    def _md5_for_file(self, file_name):
        '''Calculate md5 for file data

        Calculating block wise to prevent issues with big files in memory
        '''
        block_size = 8192
        md5 = hashlib.md5()
        try:
            with open(file_name, 'rb') as f:
                while True:
                    data = f.read(block_size)
                    if not data:
                        break
                    md5.update(data)
        except OSError as e:
            logging.warning('md5_for_file failed for %s: %s', file_name, e)
        return md5.digest()
