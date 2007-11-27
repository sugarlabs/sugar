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

import os
import logging
import tempfile

import hippo
import gtk
 
from sugar import util
from sugar.clipboard import clipboardservice
from sugar.graphics.tray import VTray

from view.clipboardicon import ClipboardIcon

class _ContextMap:
    """Maps a drag context to the clipboard object involved in the dragging."""
    def __init__(self):
        self._context_map = {}
        
    def add_context(self, context, object_id, data_types):
        """Establishes the mapping. data_types will serve us for reference-
        counting this mapping.
        """
        self._context_map[context] = [object_id, data_types]
    
    def get_object_id(self, context):
        """Retrieves the object_id associated with context.
        Will release the association when this function was called as many times
        as the number of data_types that this clipboard object contains.
        """
        [object_id, data_types_left] = self._context_map[context]
        
        data_types_left = data_types_left - 1
        if data_types_left == 0:
            del self._context_map[context]
        else:
            self._context_map[context] = [object_id, data_types_left]

        return object_id

    def has_context(self, context):
        return context in self._context_map
 
class ClipboardBox(hippo.CanvasBox):
    
    def __init__(self):
        hippo.CanvasBox.__init__(self)
        self._icons = {}
        self._context_map = _ContextMap()

        self._tray = VTray()
        self.append(hippo.CanvasWidget(widget=self._tray), hippo.PACK_EXPAND)
        self._tray.show()

        cb_service = clipboardservice.get_instance()
        cb_service.connect('object-added', self._object_added_cb)
        cb_service.connect('object-deleted', self._object_deleted_cb)

    def owns_clipboard(self):
        for icon in self._icons.values():
            if icon.owns_clipboard:
                return True
        return False

    def _add_selection(self, object_id, selection):
        if not selection.data:
            return

        logging.debug('ClipboardBox: adding type ' + selection.type)

        cb_service = clipboardservice.get_instance()
        if selection.type == 'text/uri-list':
            uris = selection.data.split('\n')
            if len(uris) > 1:
                raise NotImplementedError('Multiple uris in text/uri-list still not supported.')

            cb_service.add_object_format(object_id, 
                                         selection.type,
                                         uris[0],
                                         on_disk=True)
        else:
            cb_service.add_object_format(object_id, 
                                         selection.type,
                                         selection.data,
                                         on_disk=False)
    
    def _object_added_cb(self, cb_service, object_id, name):
        if self._icons:
            group = self._icons.values()[0]
        else:
            group = None

        icon = ClipboardIcon(object_id, name, group)
        self._tray.add_item(icon, 0)
        icon.show()
        self._icons[object_id] = icon
        
        logging.debug('ClipboardBox: ' + object_id + ' was added.')

    def _object_deleted_cb(self, cb_service, object_id):
        icon = self._icons[object_id]
        self._tray.remove_item(icon)
        del self._icons[object_id]
        logging.debug('ClipboardBox: ' + object_id + ' was deleted.')

    def drag_motion_cb(self, widget, context, x, y, time):
        logging.debug('ClipboardBox._drag_motion_cb')
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True;

    def drag_drop_cb(self, widget, context, x, y, time):
        logging.debug('ClipboardBox._drag_drop_cb')
        cb_service = clipboardservice.get_instance()
        object_id = cb_service.add_object(name="")

        self._context_map.add_context(context, object_id, len(context.targets))
        
        if 'XdndDirectSave0' in context.targets:
            window = context.source_window
            prop_type, format, filename = \
                window.property_get('XdndDirectSave0','text/plain')

            # FIXME query the clipboard service for a filename?
            base_dir = tempfile.gettempdir()
            dest_filename = util.unique_id()

            name, dot, extension = filename.rpartition('.')
            dest_filename += dot + extension

            dest_uri = 'file://' + os.path.join(base_dir, dest_filename)

            window.property_change('XdndDirectSave0', prop_type, format,
                                   gtk.gdk.PROP_MODE_REPLACE, dest_uri)

            widget.drag_get_data(context, 'XdndDirectSave0', time)
        else:
            for target in context.targets:
                if str(target) not in ('TIMESTAMP', 'TARGETS', 'MULTIPLE'):
                    widget.drag_get_data(context, target, time)

        cb_service.set_object_percent(object_id, percent=100)
        
        return True

    def drag_data_received_cb(self, widget, context, x, y, selection, targetType, time):
        logging.debug('ClipboardBox: got data for target %r' % selection.target)

        object_id = self._context_map.get_object_id(context)
        try:
            if selection is None:
                logging.warn('ClipboardBox: empty selection for target ' + selection.target)
            elif selection.target == 'XdndDirectSave0':
                if selection.data == 'S':
                    window = context.source_window

                    prop_type, format, dest = \
                          window.property_get('XdndDirectSave0','text/plain')

                    clipboard = clipboardservice.get_instance()
                    clipboard.add_object_format(
                        object_id, 'XdndDirectSave0', dest, on_disk=True)
            else:
                self._add_selection(object_id, selection)

        finally:
            # If it's the last target to be processed, finish the dnd transaction
            if not self._context_map.has_context(context):
                context.drop_finish(True, gtk.get_current_event_time())

