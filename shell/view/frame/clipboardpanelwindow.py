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

import gtk
import hippo

from view.frame.framewindow import FrameWindow
from view.frame.clipboardbox import ClipboardBox
from sugar.clipboard import clipboardservice
from sugar import util

class ClipboardPanelWindow(FrameWindow):
    def __init__(self, frame, orientation):
        FrameWindow.__init__(self, orientation)

        self._frame = frame

        # Listening for new clipboard objects
        # NOTE: we need to keep a reference to gtk.Clipboard in order to keep
        # listening to it.
        self._clipboard = gtk.Clipboard()
        self._clipboard.connect("owner-change", self._owner_change_cb)

        self._clipboard_box = ClipboardBox()
        self.append(self._clipboard_box, hippo.PACK_EXPAND)

        # Receiving dnd drops
        self.drag_dest_set(0, [], 0)
        self.connect("drag_motion", self._clipboard_box.drag_motion_cb)
        self.connect("drag_drop", self._clipboard_box.drag_drop_cb)
        self.connect("drag_data_received",
                     self._clipboard_box.drag_data_received_cb)

    def _owner_change_cb(self, clipboard, event):
        logging.debug("owner_change_cb")

        if self._clipboard_box.owns_clipboard():
            return

        cb_service = clipboardservice.get_instance()
        key = cb_service.add_object(name="")
        cb_service.set_object_percent(key, percent=0)
        
        targets = clipboard.wait_for_targets()
        for target in targets:
            if target not in ('TIMESTAMP', 'TARGETS', 'MULTIPLE', 'SAVE_TARGETS'):
                logging.debug('Asking for target %s.' % target)
                selection = clipboard.wait_for_contents(target)
                if not selection:
                    logging.warning('no data for selection target %s.' % target)
                    continue
                self._add_selection(key, selection)

        cb_service.set_object_percent(key, percent=100)

    def _add_selection(self, key, selection):
        if not selection.data:
            logging.warning('no data for selection target %s.' % selection.type)
            return
            
        logging.debug('adding type ' + selection.type + '.')
                    
        cb_service = clipboardservice.get_instance()
        if selection.type == 'text/uri-list':
            uris = selection.data.split('\n')
            if len(uris) > 1:
                raise NotImplementedError('Multiple uris in text/uri-list still not supported.')

            cb_service.add_object_format(key,
                                            selection.type,
                                            uris[0],
                                            on_disk=True)
        else:
            cb_service.add_object_format(key, 
                                            selection.type,
                                            selection.data,
                                            on_disk=False)

