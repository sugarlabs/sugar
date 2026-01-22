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
from gi.repository import SugarExt
from gi.repository import GLib

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

        self.props.palette_invoker = FrameWidgetInvoker(self)
        self.palette_invoker.props.toggle_palette = True

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
        self._icon.show()

        cb_service = clipboard.get_instance()
        cb_service.connect('object-state-changed',
                           self._object_state_changed_cb)
        cb_service.connect('object-selected', self._object_selected_cb)

        child = self.get_child()
        child.connect('drag-data-get', self._drag_data_get_cb)
        self.connect('notify::active', self._notify_active_cb)

    def create_palette(self):
        palette = ClipboardMenu(self._cb_object)
        palette.set_group_id('frame')
        return palette

    def get_object_id(self):
        return self._cb_object.get_id()

    def _drag_data_get_cb(self, widget, context, selection, target_type,
                          event_time):
        target_atom = selection.get_target()
        target_name = target_atom.name()
        logging.debug('_drag_data_get_cb: requested target %s', target_name)
        data = self._cb_object.get_formats()[target_name].get_data()
        selection.set(target_atom, 8, data)
        GLib.source_remove(self._timeout_id)

    def _put_in_clipboard(self):
        logging.debug('ClipboardIcon._put_in_clipboard')

        if self._cb_object.get_percent() < 100:
            raise ValueError('Object is not complete, cannot be put into the'
                             ' clipboard.')

        clipboard = Gdk.Display.get_default().get_clipboard()
        try:
            content_provider = Gdk.ContentProvider.new_for_bytes(
                self._cb_object.get_mime_type(),
                self._cb_object)
            stored = clipboard.set_content(content_provider)
        # this is empty as I don't yet know what exceptions can be raised here.
        except:
             stored = SugarExt.clipboard_set_with_data(
                self._cb_object.get_mime_type(),
                self._cb_object)

        if not stored:
            logging.error('GtkClipboard.set_with_data failed!')
        else:
            self.owns_clipboard = True

    def _object_state_changed_cb(self, cb_service, cb_object):
        if cb_object != self._cb_object:
            return

        if cb_object.get_icon():
            self._icon.props.icon_name = cb_object.get_icon()
            if self._notif_icon:
                self._notif_icon.props.icon_name = self._icon.props.icon_name
        else:
            self._icon.props.icon_name = 'application-octet-stream'

        child = self.get_child()
        child.connect('drag-begin', self._drag_begin_cb)
        child.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                              self._get_targets(),
                              Gdk.DragAction.COPY)

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
        self._notif_icon.connect('drag-data-get', self._drag_data_get_cb)
        self._notif_icon.connect('drag-begin', self._drag_begin_cb)
        self._notif_icon.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                                         self._get_targets(),
                                         Gdk.DragAction.COPY)

    def _drag_begin_cb(self, widget, context):
        # TODO: We should get the pixbuf from the icon, with colors, etc.
        frame = jarabe.frame.get_view()
        self._timeout_id = GLib.timeout_add(
            jarabe.frame.frame.NOTIFICATION_DURATION,
            lambda: frame.remove_notification(self._notif_icon))
        icon_theme = Gtk.IconTheme.get_default()
        pixbuf = icon_theme.load_icon(self._icon.props.icon_name,
                                      style.STANDARD_ICON_SIZE, 0)
        Gtk.drag_set_icon_pixbuf(context, pixbuf, hot_x=pixbuf.props.width / 2,
                                 hot_y=pixbuf.props.height / 2)

    def _notify_active_cb(self, widget, pspec):
        if self.props.active:
            self._put_in_clipboard()
        else:
            self.owns_clipboard = False
