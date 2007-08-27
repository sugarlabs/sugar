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

from sugar.graphics.icon import CanvasIcon
from view.clipboardmenu import ClipboardMenu
from sugar.graphics.xocolor import XoColor
from sugar.graphics import style
from sugar.clipboard import clipboardservice
from sugar import util
from sugar import profile

class ClipboardIcon(CanvasIcon):
    __gtype_name__ = 'SugarClipboardIcon'

    __gproperties__ = {
        'selected'      : (bool, None, None, False,
                           gobject.PARAM_READWRITE)
    }

    def __init__(self, object_id, name):
        CanvasIcon.__init__(self)
        self._object_id = object_id
        self._name = name
        self._percent = 0
        self._preview = None
        self._activity = None
        self._selected = False
        self._hover = False
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.xo_color = XoColor(profile.get_color().to_string())
        
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        formats = obj['FORMATS']

        self.palette = ClipboardMenu(self._object_id, self._name, self._percent,
                                     self._preview, self._activity,
                                     formats and formats[0] == 'application/vnd.olpc-sugar')

    def do_set_property(self, pspec, value):
        if pspec.name == 'selected':
            self._set_selected(value)
            self.emit_paint_needed(0, 0, -1, -1)
        else:
            CanvasIcon.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'selected':
            return self._selected
        else:
            return CanvasIcon.do_get_property(self, pspec)

    def _set_selected(self, selected):
        self._selected = selected
        if selected:
            if not self._hover:
                self.props.background_color = style.COLOR_SELECTION_GREY.get_int()
        else:
            self.props.background_color = style.COLOR_PANEL_GREY.get_int()

    def set_state(self, name, percent, icon_name, preview, activity):
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        if obj['FORMATS'] and obj['FORMATS'][0] == 'application/vnd.olpc-sugar':
            installable = True
        else:
            installable = False

        if icon_name:
            self.props.icon_name = icon_name
        else:
            self.props.icon_name = 'application-octet-stream'

        self._name = name
        self._percent = percent
        self._preview = preview
        self._activity = activity
        self.palette.set_state(name, percent, preview, activity, installable)

        if (activity or installable) and percent < 100:
            self.props.xo_color = XoColor("#000000,#424242")
        else:
            self.props.xo_color = XoColor(profile.get_color().to_string())

    def get_object_id(self):
        return self._object_id

    def prelight(self, enter):
        if enter:
            self._hover = True
            self.props.background_color = style.COLOR_BLACK.get_int()
        else:
            self._hover = False
            if self._selected:
                self.props.background_color = style.COLOR_SELECTION_GREY.get_int()
            else:
                self.props.background_color = style.COLOR_PANEL_GREY.get_int()

