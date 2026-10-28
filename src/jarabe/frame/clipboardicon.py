# Copyright (C) 2007, Red Hat, Inc.
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

from sugar4.graphics.radiotoolbutton import RadioToolButton
from sugar4.graphics.icon import Icon
from sugar4.graphics.xocolor import XoColor
from sugar4.graphics import style
from sugar4 import profile

from jarabe.frame import clipboard
from jarabe.frame.clipboardmenu import ClipboardMenu
from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.frame.notification import NotificationIcon
import jarabe.frame


class ClipboardIcon(RadioToolButton):
    __gtype_name__ = 'SugarClipboardIcon'

    def __init__(self, cb_object, group):
        RadioToolButton.__init__(self, group=group)

        invoker = FrameWidgetInvoker(self)
        self.set_palette_invoker(invoker)
        if hasattr(invoker, '_toggle_palette'):
            invoker._toggle_palette = True

        self._cb_object = cb_object
        self.owns_clipboard = False
        self.props.sensitive = False
        self.props.active = False
        self._notif_icon = None
        self._current_percent = 0

        self._icon = Icon()
        color = profile.get_color()
        self._icon.props.xo_color = color
        self.set_icon_widget(self._icon)
        self._icon.set_visible(True)

        cb_service = clipboard.get_instance()
        cb_service.connect('object-state-changed',
                           self._object_state_changed_cb)
        cb_service.connect('object-selected', self._object_selected_cb)

        self.connect('notify::active', self._notify_active_cb)

        self._clipboard = Gdk.Display.get_default().get_clipboard()
        self._clipboard.connect('notify::content', self._on_clipboard_content_changed)

    def _on_clipboard_content_changed(self, clipboard, pspec):
        if not getattr(self, '_setting_clipboard', False):
            self.owns_clipboard = False

    def create_palette(self):
        palette = ClipboardMenu(self._cb_object)
        palette.set_group_id('frame')
        return palette

    def get_object_id(self):
        return self._cb_object.get_id()

    def _put_in_clipboard(self):
        logging.debug('ClipboardIcon._put_in_clipboard')

        if self._cb_object.get_percent() < 100:
            raise ValueError('Object is not complete, cannot be put into the'
                             ' clipboard.')

        gdk_clipboard = Gdk.Display.get_default().get_clipboard()
        try:
            formats = self._cb_object.get_formats()
            providers = []
            
            for fmt_name, format_ in formats.items():
                data = format_.get_data()
                if isinstance(data, str):
                    if fmt_name == 'text/plain':
                        v = GObject.Value(GObject.TYPE_STRING, data)
                        providers.append(Gdk.ContentProvider.new_for_value(v))
                    else:
                        gbytes = GLib.Bytes.new(data.encode('utf-8'))
                        providers.append(Gdk.ContentProvider.new_for_bytes(fmt_name, gbytes))
                elif isinstance(data, bytes):
                    gbytes = GLib.Bytes.new(data)
                    providers.append(Gdk.ContentProvider.new_for_bytes(fmt_name, gbytes))

            if providers:
                provider = Gdk.ContentProvider.new_union(providers)
                self._setting_clipboard = True
                gdk_clipboard.set_content(provider)
                self._setting_clipboard = False
                self.owns_clipboard = True
        except Exception as e:
            logging.error('Failed to put in clipboard: %s', e)

    def _object_state_changed_cb(self, cb_service, cb_object):
        if cb_object != self._cb_object:
            return

        if cb_object.get_icon():
            self._icon.props.icon_name = cb_object.get_icon()
            if self._notif_icon:
                self._notif_icon.props.icon_name = self._icon.props.icon_name
        else:
            self._icon.props.icon_name = 'application-octet-stream'

        if not hasattr(self, '_drag_source'):
            self._drag_source = Gtk.DragSource.new()
            self._drag_source.connect('prepare', self._on_drag_prepare)
            self._drag_source.connect('drag-begin', self._drag_begin_cb)
            self.add_controller(self._drag_source)

        if cb_object.get_percent() == 100:
            self.props.sensitive = True

        # Clipboard object became complete. Make it the active one.
        percent = cb_object.get_percent()
        if self._current_percent < 100 and percent == 100:
            self.props.active = True
            self.show_notification()

        self._current_percent = percent

    def _object_selected_cb(self, cb_service, object_id):
        if object_id != self._cb_object.get_id():
            return
        self.props.active = True
        self.show_notification()
        logging.debug('ClipboardIcon: %r was selected', object_id)

    def show_notification(self):
        self._notif_icon = NotificationIcon()
        self._notif_icon.props.icon_name = self._icon.props.icon_name
        self._notif_icon.props.xo_color = \
            XoColor('%s,%s' % (self._icon.props.stroke_color,
                               self._icon.props.fill_color))
        frame = jarabe.frame.get_view()
        self._timeout_id = frame.add_notification(
            self._notif_icon, Gtk.CornerType.BOTTOM_LEFT)
            
        notif_drag_source = Gtk.DragSource.new()
        notif_drag_source.connect('prepare', self._on_drag_prepare)
        notif_drag_source.connect('drag-begin', self._drag_begin_cb)
        self._notif_icon.add_controller(notif_drag_source)

    def _on_drag_prepare(self, source, x, y):
        formats = self._cb_object.get_formats()
        providers = []
        for fmt_name, format_ in formats.items():
            data = format_.get_data()
            if isinstance(data, str):
                if fmt_name == 'text/plain':
                    v = GObject.Value(GObject.TYPE_STRING, data)
                    providers.append(Gdk.ContentProvider.new_for_value(v))
                else:
                    gbytes = GLib.Bytes.new(data.encode('utf-8'))
                    providers.append(Gdk.ContentProvider.new_for_bytes(fmt_name, gbytes))
            elif isinstance(data, bytes):
                gbytes = GLib.Bytes.new(data)
                providers.append(Gdk.ContentProvider.new_for_bytes(fmt_name, gbytes))
        
        if providers:
            return Gdk.ContentProvider.new_union(providers)
        
        return None

    def _drag_begin_cb(self, source, drag):
        if hasattr(self, '_timeout_id') and self._timeout_id > 0:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = 0
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        paintable = icon_theme.lookup_icon(self._icon.props.icon_name, None, style.STANDARD_ICON_SIZE, 1, 0, 0)
        if paintable:
            source.set_icon(paintable, 0, 0)

    def _notify_active_cb(self, widget, pspec):
        if self.props.active:
            self._put_in_clipboard()
        else:
            self.owns_clipboard = False
