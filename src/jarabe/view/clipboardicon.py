# Copyright (C) 2007, Red Hat, Inc.
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

from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor
from sugar import profile

from jarabe.model import clipboard
from jarabe.view.clipboardmenu import ClipboardMenu
from jarabe.view.frame.frameinvoker import FrameWidgetInvoker
from jarabe.view.frame.notification import NotificationIcon
import view.frame.frame

class ClipboardIcon(RadioToolButton):
    __gtype_name__ = 'SugarClipboardIcon'

    def __init__(self, cb_object, group):
        RadioToolButton.__init__(self, group=group)
        self._cb_object = cb_object
        self.owns_clipboard = False
        self.props.sensitive = False
        self.props.active = False
        self._notif_icon = None
        self._current_percent = None

        self._icon = Icon()
        self._icon.props.xo_color = profile.get_color()
        self.set_icon_widget(self._icon)
        self._icon.show()

        cb_service = clipboard.get_instance()
        cb_service.connect('object-state-changed',
                           self._object_state_changed_cb)

        self.palette = ClipboardMenu(cb_object)
        self.palette.props.invoker = FrameWidgetInvoker(self)

        child = self.get_child()
        child.connect('drag_data_get', self._drag_data_get_cb)
        self.connect('notify::active', self._notify_active_cb)

    def get_object_id(self):
        return self._cb_object.get_id()

    def _drag_data_get_cb(self, widget, context, selection, target_type,
                          event_time):
        logging.debug('_drag_data_get_cb: requested target ' + selection.target)
        data = self._cb_object.get_formats()[selection.target].get_data()
        selection.set(selection.target, 8, data)

    def _put_in_clipboard(self):
        logging.debug('ClipboardIcon._put_in_clipboard')

        if self._cb_object.get_percent() < 100:
            raise ValueError('Object is not complete,' \
                             ' cannot be put into the clipboard.')

        targets = self._get_targets()
        if targets:
            x_clipboard = gtk.Clipboard()
            if not x_clipboard.set_with_data(targets,
                                           self._clipboard_data_get_cb,
                                           self._clipboard_clear_cb,
                                           targets):
                logging.error('GtkClipboard.set_with_data failed!')
            else:
                self.owns_clipboard = True

    def _clipboard_data_get_cb(self, x_clipboard, selection, info, targets):
        if not selection.target in [target[0] for target in targets]:
            logging.warning('ClipboardIcon._clipboard_data_get_cb: asked %s' \
                            ' but only have %r.' % (selection.target, targets))
            return
        data = self._cb_object.get_formats()[selection.target].get_data()
        selection.set(selection.target, 8, data)

    def _clipboard_clear_cb(self, x_clipboard, targets):
        logging.debug('ClipboardIcon._clipboard_clear_cb')
        self.owns_clipboard = False

    def _object_state_changed_cb(self, cb_service, cb_object):
        if cb_object != self._cb_object:
            return

        if cb_object.get_icon():
            self._icon.props.icon_name = cb_object.get_icon()
        else:
            self._icon.props.icon_name = 'application-octet-stream'

        child = self.get_child()
        child.drag_source_set(gtk.gdk.BUTTON1_MASK,
                              self._get_targets(),
                              gtk.gdk.ACTION_COPY)
        child.drag_source_set_icon_name(self._icon.props.icon_name)

        if cb_object.get_percent() == 100:
            self.props.sensitive = True

        # Clipboard object became complete. Make it the active one.
        if self._current_percent < 100 and cb_object.get_percent() == 100:
            self.props.active = True

            self._notif_icon = NotificationIcon()
            self._notif_icon.props.icon_name = self._icon.props.icon_name
            self._notif_icon.props.xo_color = \
                    XoColor('%s,%s' % (self._icon.props.stroke_color,
                                       self._icon.props.fill_color))
            frame = view.frame.frame.get_instance()
            frame.add_notification(self._notif_icon, 
                                   view.frame.frame.BOTTOM_LEFT)
        self._current_percent = cb_object.get_percent()

    def _notify_active_cb(self, widget, pspec):
        if self.props.active:
            self._put_in_clipboard()
        else:
            self.owns_clipboard = False

    def _get_targets(self):
        targets = []
        for format_type in self._cb_object.get_formats().keys():
            targets.append((format_type, 0, 0))
        return targets

