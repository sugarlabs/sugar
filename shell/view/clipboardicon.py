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
from gettext import gettext as _

import gobject
import gtk

from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.xocolor import XoColor
from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar.clipboard import clipboardservice
from sugar import util
from sugar import profile

from view.clipboardmenu import ClipboardMenu
from view.frame.frameinvoker import FrameWidgetInvoker

class ClipboardIcon(RadioToolButton):
    __gtype_name__ = 'SugarClipboardIcon'

    def __init__(self, object_id, name, group):
        RadioToolButton.__init__(self, group=group)
        self._object_id = object_id
        self._name = name
        self._percent = 0
        self._preview = None
        self._activity = None
        self.owns_clipboard = False

        self._icon = Icon()
        self._icon.props.xo_color = profile.get_color()
        self.set_icon_widget(self._icon)
        self._icon.show()

        self.props.sensitive = False
        
        cb_service = clipboardservice.get_instance()
        cb_service.connect('object-state-changed', self._object_state_changed_cb)
        obj = cb_service.get_object(self._object_id)
        formats = obj['FORMATS']

        self.palette = ClipboardMenu(self._object_id, self._name, self._percent,
                                     self._preview, self._activity,
                                     formats and formats[0] == 'application/vnd.olpc-sugar')
        self.palette.props.invoker = FrameWidgetInvoker(self)
        
        self.child.connect('drag_data_get', self._drag_data_get_cb)
        self.connect('notify::active', self._notify_active_cb)

    def get_object_id(self):
        return self._object_id

    def _drag_data_get_cb(self, widget, context, selection, targetType, eventTime):
        logging.debug('_drag_data_get_cb: requested target ' + selection.target)
        
        cb_service = clipboardservice.get_instance()
        data = cb_service.get_object_data(self._object_id, selection.target)['DATA']
        
        selection.set(selection.target, 8, data)

    def _put_in_clipboard(self):
        logging.debug('ClipboardIcon._put_in_clipboard')
        targets = self._get_targets()
        if targets:
            clipboard = gtk.Clipboard()
            if not clipboard.set_with_data(targets,
                                           self._clipboard_data_get_cb,
                                           self._clipboard_clear_cb,
                                           targets):
                logging.error('GtkClipboard.set_with_data failed!')
            else:
                self.owns_clipboard = True

    def _clipboard_data_get_cb(self, clipboard, selection, info, targets):
        if not selection.target in [target[0] for target in targets]:
            logging.warning('ClipboardIcon._clipboard_data_get_cb: asked %s but' \
                            ' only have %r.' % (selection.target, targets))
            return
        cb_service = clipboardservice.get_instance()
        data = cb_service.get_object_data(self._object_id, selection.target)['DATA']
        
        selection.set(selection.target, 8, data)

    def _clipboard_clear_cb(self, clipboard, targets):
        logging.debug('ClipboardIcon._clipboard_clear_cb')
        self.owns_clipboard = False

    def _object_state_changed_cb(self, cb_service, object_id, name, percent,
                                 icon_name, preview, activity):

        if object_id != self._object_id:
            return

        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        if obj['FORMATS'] and obj['FORMATS'][0] == 'application/vnd.olpc-sugar':
            installable = True
        else:
            installable = False

        if icon_name:
            self._icon.props.icon_name = icon_name
        else:
            self._icon.props.icon_name = 'application-octet-stream'

        self.child.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                         self._get_targets(),
                                         gtk.gdk.ACTION_COPY)
        self.child.drag_source_set_icon_name(self._icon.props.icon_name)
        
        self._name = name
        self._percent = percent
        self._preview = preview
        self._activity = activity
        self.palette.set_state(name, percent, preview, activity, installable)

        self.props.sensitive = (percent == 100)

        if self.props.active:
            self._put_in_clipboard()

    def _notify_active_cb(self, widget, pspec):
        if self.props.active:
            self._put_in_clipboard()
        else:
            self.owns_clipboard = False

    def _get_targets(self):
        cb_service = clipboardservice.get_instance()

        attrs = cb_service.get_object(self._object_id)
        format_types = attrs[clipboardservice.FORMATS_KEY]
        
        targets = []        
        for format_type in format_types:
            targets.append((format_type, 0, 0))
        
        return targets

