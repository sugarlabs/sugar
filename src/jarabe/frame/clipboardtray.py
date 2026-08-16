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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio

from sugar4.graphics import tray
from sugar4.graphics import style

from jarabe.frame import clipboard
from jarabe.frame.clipboardicon import ClipboardIcon


def _get_screen_height():
    display = Gdk.Display.get_default()
    if display:
        monitors = display.get_monitors()
        if monitors and monitors.get_n_items() > 0:
            return monitors.get_item(0).get_geometry().height
    return 768


class ClipboardTray(tray.VTray):

    MAX_ITEMS = _get_screen_height() // style.GRID_CELL_SIZE - 2

    def __init__(self):
        tray.VTray.__init__(self, align=tray.ALIGN_TO_END)
        self._icons = {}

        cb_service = clipboard.get_instance()
        self._object_added_hid = cb_service.connect('object-added', self._object_added_cb)
        self._object_deleted_hid = cb_service.connect('object-deleted', self._object_deleted_cb)

        builder = Gdk.ContentFormatsBuilder.new()
        builder.add_mime_type('journal-object-id')
        builder.add_mime_type('text/uri-list')
        builder.add_mime_type('text/plain')
        builder.add_mime_type('text/html')
        builder.add_mime_type('image/png')
        builder.add_mime_type('image/jpeg')
        builder.add_mime_type('image/gif')
        builder.add_mime_type('image/svg+xml')
        builder.add_gtype(GObject.TYPE_STRING)
        formats = builder.to_formats()
        
        self._drop_target = Gtk.DropTargetAsync.new(formats, actions=Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self._drop_target.connect('drop', self._on_drop_async_cb)
        self.add_controller(self._drop_target)

    def do_dispose(self):
        cb_service = clipboard.get_instance()
        if hasattr(self, '_object_added_hid'):
            cb_service.disconnect(self._object_added_hid)
            del self._object_added_hid
        if hasattr(self, '_object_deleted_hid'):
            cb_service.disconnect(self._object_deleted_hid)
            del self._object_deleted_hid
        if getattr(self, '_drop_target', None) is not None:
            self.remove_controller(self._drop_target)
            self._drop_target = None
        super().do_dispose()

    def owns_clipboard(self):
        for icon in list(self._icons.values()):
            if icon.owns_clipboard:
                return True
        return False

    def _object_added_cb(self, cb_service, cb_object):
        group = None
        if self._icons:
            group = list(self._icons.values())[0]

        icon = ClipboardIcon(cb_object, group)
        self.add_item(icon)
        icon.set_visible(True)
        self._icons[cb_object.get_id()] = icon

        # Enforce MAX_ITEMS
        children = []
        child = self.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()

        if len(children) > self.MAX_ITEMS:
            objects_to_delete = children[:-self.MAX_ITEMS]
            for icon_to_delete in objects_to_delete:
                logging.debug('ClipboardTray: deleting surplus object')
                cb_service = clipboard.get_instance()
                cb_service.delete_object(icon_to_delete.get_object_id())

        logging.debug('ClipboardTray: %r was added', cb_object.get_id())

    def _object_deleted_cb(self, cb_service, object_id):
        icon = self._icons.get(object_id)
        if icon:
            self.remove_item(icon)
            del self._icons[object_id]
            
            # select the last available icon if the deleted one was active
            if icon.props.active and self._icons:
                children = []
                child = self.get_first_child()
                while child:
                    children.append(child)
                    child = child.get_next_sibling()
                if children:
                    last_icon = children[-1]
                    if hasattr(last_icon, 'set_active'):
                        last_icon.set_active(True)

        logging.debug('ClipboardTray: %r was deleted', object_id)

    def _on_drop_async_cb(self, target, drop, x, y):
        logging.debug('ClipboardTray._on_drop_async_cb')
        formats = drop.get_formats()
        mime_types = formats.get_mime_types()
        if not mime_types:
            return False
            
        skip_targets = frozenset(['TIMESTAMP', 'TARGETS', 'MULTIPLE', 'SAVE_TARGETS', 'DELETE', 'INSERT_SELECTION', 'INSERT_PROPERTY'])
        valid_targets = [t for t in mime_types if t not in skip_targets]
        if not valid_targets:
            return False
            
        cb_service = clipboard.get_instance()
        object_id = cb_service.add_object(name="")
        cb_service.set_object_percent(object_id, percent=0)
        
        state = {'pending': len(valid_targets), 'object_id': object_id}
        for mime_type in valid_targets:
            drop.read_async([mime_type], GLib.PRIORITY_DEFAULT, None, self._on_read_raw_cb, (mime_type, state))
        return True

    def _on_read_raw_cb(self, drop, result, user_data):
        mime_type, state = user_data
        try:
            stream, out_mime = drop.read_finish(result)
            if stream:
                stream.read_bytes_async(65536, GLib.PRIORITY_DEFAULT, None, self._on_bytes_read_cb, (stream, mime_type, state))
                return
        except Exception as e:
            logging.error("Failed to read raw drop: %s", e)
        self._check_complete(state)

    def _on_bytes_read_cb(self, stream, result, user_data):
        stream, mime_type, state = user_data
        try:
            bytes_data = stream.read_bytes_finish(result)
            data = bytes_data.get_data() if bytes_data else None
            if data:
                cb_service = clipboard.get_instance()
                
                if mime_type == 'text/uri-list':
                    try:
                        text = data.decode('utf-8').strip()
                        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith('#')]
                        if lines:
                            uri = lines[0]
                            f = Gio.File.new_for_uri(uri)
                            path = f.get_path()
                            if path:
                                cb_service.add_object_format(state['object_id'], mime_type, path, on_disk=True)
                                self._check_complete(state)
                                return
                    except Exception:
                        pass

                if mime_type.startswith('text/') or mime_type == 'journal-object-id':
                    try:
                        data = data.decode('utf-8')
                    except Exception:
                        pass
                cb_service.add_object_format(state['object_id'], mime_type, data, on_disk=False)
        except Exception as e:
            logging.error("Failed to read dropped bytes: %s", e)
        self._check_complete(state)
        
    def _check_complete(self, state):
        state['pending'] -= 1
        if state['pending'] <= 0:
            cb_service = clipboard.get_instance()
            cb_service.set_object_percent(state['object_id'], percent=100)
