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
import os

import gobject

from sugar.graphics.canvasicon import CanvasIcon
from view.clipboardmenu import ClipboardMenu
from sugar.graphics.xocolor import XoColor
from sugar.graphics import units
from sugar.graphics import color
from sugar.activity import activityfactory
from sugar.clipboard import clipboardservice
from sugar import util

class ClipboardIcon(CanvasIcon):
    __gtype_name__ = 'SugarClipboardIcon'

    __gproperties__ = {
        'selected'      : (bool, None, None, False,
                           gobject.PARAM_READWRITE)
    }

    def __init__(self, popup_context, object_id, name):
        CanvasIcon.__init__(self)
        self._popup_context = popup_context
        self._object_id = object_id
        self._name = name
        self._percent = 0
        self._preview = None
        self._selected = False
        self._hover = False
        self.props.box_width = units.grid_to_pixels(1)
        self.props.box_height = units.grid_to_pixels(1)
        self.props.scale = units.STANDARD_ICON_SCALE
        self._menu = None

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
                self.props.background_color = color.DESKTOP_BACKGROUND.get_int()
        else:
            self.props.background_color = color.TOOLBAR_BACKGROUND.get_int()

    def get_popup(self):
        self._menu = ClipboardMenu(self._name, self._percent, self._preview)
        self._menu.connect('action', self._popup_action_cb)
        return self._menu

    def get_popup_context(self):
        return self._popup_context

    def set_name(self, name):
        self._name = name
        if self._menu:
            self._menu.set_title(name)
            
    def set_formats(self, formats):
        self._preview = None
        self.props.icon_name = 'theme:stock-missing'

    def set_state(self, percent):
        self._percent = percent
        if self._menu:
            self._menu.set_state(percent)
                        
    def _popup_action_cb(self, popup, menu_item):
        action = menu_item.props.action_id
        
        if action == ClipboardMenu.ACTION_STOP_DOWNLOAD:
            raise "Stopping downloads still not implemented."
        elif action == ClipboardMenu.ACTION_DELETE:
            cb_service = clipboardservice.get_instance()
            cb_service.delete_object(self._object_id)
        elif action == ClipboardMenu.ACTION_OPEN:
            self._open_file()
        
    def get_object_id(self):
        return self._object_id

    def prelight(self, enter):
        if enter:
            self._hover = True
            self.props.background_color = color.BLACK.get_int()
        else:
            self._hover = False
            if self._selected:
                self.props.background_color = color.DESKTOP_BACKGROUND.get_int()
            else:
                self.props.background_color = color.TOOLBAR_BACKGROUND.get_int()
