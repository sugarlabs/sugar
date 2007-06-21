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
import shutil
import os
import logging
import urlparse

import hippo
import gtk
 
from sugar import util
from sugar.objects import mime
from view.clipboardicon import ClipboardIcon
from sugar.clipboard import clipboardservice

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
    
    def __init__(self, popup_context):
        hippo.CanvasBox.__init__(self)
        self._popup_context = popup_context
        self._icons = {}
        self._context_map = _ContextMap()
        self._selected_icon = None
        self._owns_clipboard = False

        self._pressed_button = None
        self._press_start_x = None
        self._press_start_y = None

        cb_service = clipboardservice.get_instance()
        cb_service.connect('object-added', self._object_added_cb)
        cb_service.connect('object-deleted', self._object_deleted_cb)
        cb_service.connect('object-state-changed', self._object_state_changed_cb)

    def owns_clipboard(self):
        return self._owns_clipboard

    def _get_icon_at_coords(self, x, y):
        box_x, box_y = self.get_context().get_position(self)
        x -= box_x
        y -= box_y
        for object_id, icon in self._icons.iteritems():
            icon_x, icon_y = self.get_position(icon)
            icon_width, icon_height = icon.get_allocation()

            if (x >= icon_x ) and (x <= icon_x + icon_width) and        \
                    (y >= icon_y ) and (y <= icon_y + icon_height):
                return icon
                
        return None

    def _add_selection(self, object_id, selection):
        if not selection.data:
            return

        logging.debug('ClipboardBox: adding type ' + selection.type + ' ' + selection.data)

        cb_service = clipboardservice.get_instance()
        if selection.type == 'text/uri-list':
            uris = selection.data.split('\n')
            if len(uris) > 1:
                raise NotImplementedError('Multiple uris in text/uri-list still not supported.')
            uri = urlparse.urlparse(uris[0])
            path, file_name = os.path.split(uri.path)

            root, ext = os.path.splitext(file_name)
            if not ext or ext == '.':
                mime_type = mime.get_for_file(uri.path)
                file_name = root + '.' + mime.get_primary_extension(mime_type)
            
            # Copy the file, as it will be deleted when the dnd operation finishes.
            new_file_path = os.path.join(path, 'cb' + file_name)
            shutil.copyfile(uri.path, new_file_path)

            cb_service.add_object_format(object_id, 
                                         selection.type,
                                         "file://" + new_file_path,
                                         on_disk=True)
        else:
            cb_service.add_object_format(object_id, 
                                         selection.type,
                                         selection.data,
                                         on_disk=False)
    
    def _object_added_cb(self, cb_service, object_id, name):
        icon = ClipboardIcon(self._popup_context, object_id, name)
        icon.connect('activated', self._icon_activated_cb)
        self._set_icon_selected(icon)

        self.prepend(icon)
        self._icons[object_id] = icon
        
        logging.debug('ClipboardBox: ' + object_id + ' was added.')

    def _set_icon_selected(self, icon):
        logging.debug('_set_icon_selected')
        icon.props.selected = True
        if self._selected_icon:
            self._selected_icon.props.selected = False
        self._selected_icon = icon

    def _put_in_clipboard(self, object_id):
        logging.debug('ClipboardBox._put_in_clipboard')
        targets = self._get_object_targets(object_id)
        if targets:
            clipboard = gtk.Clipboard()
            if not clipboard.set_with_data(targets,
                                           self._clipboard_data_get_cb,
                                           self._clipboard_clear_cb):
                logging.error('GtkClipboard.set_with_data failed!')
            else:
                self._owns_clipboard = True

    def _clipboard_data_get_cb(self, clipboard, selection, info, data):
        object_id = self._selected_icon.get_object_id()
        cb_service = clipboardservice.get_instance()
        data = cb_service.get_object_data(object_id, selection.target)['DATA']
        
        selection.set(selection.target, 8, data)

    def _clipboard_clear_cb(self, clipboard, data):
        logging.debug('ClipboardBox._clipboard_clear_cb')
        self._owns_clipboard = False

    def _icon_activated_cb(self, icon):
        logging.debug('ClipboardBox._icon_activated_cb')
        if not icon.props.selected:
            self._set_icon_selected(icon)

    def _object_deleted_cb(self, cb_service, object_id):
        icon = self._icons[object_id]
        position = self.get_children().index(icon)
        self.remove(icon)
        
        if icon.props.selected and self.get_children():
            self._set_icon_selected(self.get_children()[position])

        del self._icons[object_id]
        logging.debug('ClipboardBox: ' + object_id + ' was deleted.')

    def _object_state_changed_cb(self, cb_service, object_id, name, percent,
                                 icon_name, preview, activity):
        icon = self._icons[object_id]
        icon.set_state(name, percent, icon_name, preview, activity)
        if icon.props.selected and percent == 100:
            self._put_in_clipboard(object_id)

    def drag_motion_cb(self, widget, context, x, y, time):
        logging.debug('ClipboardBox._drag_motion_cb')
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True;

    def drag_drop_cb(self, widget, context, x, y, time):
        logging.debug('ClipboardBox._drag_drop_cb')
        cb_service = clipboardservice.get_instance()
        object_id = cb_service.add_object(name="")

        self._context_map.add_context(context, object_id, len(context.targets))
        
        for target in context.targets:
            if str(target) not in ('TIMESTAMP', 'TARGETS', 'MULTIPLE'):
                widget.drag_get_data(context, target, time)

        cb_service.set_object_percent(object_id, percent=100)
        
        return True

    def drag_data_received_cb(self, widget, context, x, y, selection, targetType, time):
        logging.debug('ClipboardBox: got data for target %r' % selection.target)
        try:
            if selection:
                object_id = self._context_map.get_object_id(context)
                self._add_selection(object_id, selection)
            else:
                logging.warn('ClipboardBox: empty selection for target ' + selection.target)
        finally:
            # If it's the last target to be processed, finish the dnd transaction
            if not self._context_map.has_context(context):
                context.drop_finish(True, gtk.get_current_event_time())

    def drag_data_get_cb(self, widget, context, selection, targetType, eventTime):
        logging.debug("drag_data_get_cb: requested target " + selection.target)
        
        object_id = self._last_clicked_icon.get_object_id()
        cb_service = clipboardservice.get_instance()
        data = cb_service.get_object_data(object_id, selection.target)['DATA']
        
        selection.set(selection.target, 8, data)

    def button_press_event_cb(self, widget, event):
        logging.debug("button_press_event_cb")

        if event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
            self._last_clicked_icon = self._get_icon_at_coords(event.x, event.y)
            if self._last_clicked_icon:
                self._pressed_button = event.button
                self._press_start_x = event.x
                self._press_start_y = event.y

        return True;

    def motion_notify_event_cb(self, widget, event):
       
        if not self._pressed_button:
            return True
        
        # if the mouse button is not pressed, no drag should occurr
        if not event.state & gtk.gdk.BUTTON1_MASK:
            self._pressed_button = None
            return True

        logging.debug("motion_notify_event_cb")
                        
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        if widget.drag_check_threshold(int(self._press_start_x),
                                       int(self._press_start_y),
                                       int(x),
                                       int(y)):
            targets = self._get_object_targets(
                self._last_clicked_icon.get_object_id())

            context = widget.drag_begin(targets,
                                        gtk.gdk.ACTION_COPY,
                                        1,
                                        event);

        return True

    def drag_end_cb(self, widget, drag_context):
        logging.debug("drag_end_cb")
        self._pressed_button = None

    def _get_object_targets(self, object_id):
        cb_service = clipboardservice.get_instance()

        attrs = cb_service.get_object(object_id)
        format_types = attrs[clipboardservice.FORMATS_KEY]
        
        targets = []        
        for format_type in format_types:
            targets.append((format_type, 0, 0))
        
        return targets
