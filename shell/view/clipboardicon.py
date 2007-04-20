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
import urlparse

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
        self._activity = None
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
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        formats = obj['FORMATS']

        self._menu = ClipboardMenu(self._name, self._percent, self._preview,
                                   self._activity,
                                   formats[0] == 'application/vnd.olpc-x-sugar')
        self._menu.connect('action', self._popup_action_cb)
        return self._menu

    def get_popup_context(self):
        return self._popup_context

    def set_state(self, name, percent, icon_name, preview, activity):
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        installable = (obj['FORMATS'][0] == 'application/vnd.olpc-x-sugar')

        self._name = name
        self._percent = percent
        self._preview = preview
        self._activity = activity
        self.set_property("icon_name", icon_name)
        if self._menu:
            self._menu.set_state(name, percent, preview, activity, installable)

        if (activity or installable) and percent < 100:
            self.props.xo_color = XoColor("#000000,#424242")
        else:
            self.props.xo_color = XoColor("#000000,#FFFFFF")

        if activity and percent == 100:
            # FIXME: restrict based on file type rather than activity once
            # we have a better type registry
            # restrict auto-open to a specific set of activities
            allowed = ["org.laptop.AbiWordActivity",
                       "org.laptop.sugar.Xbook",
                       "org.vpri.EtoysActivity"]
            if activity in allowed:
                self._open_file()

    def _open_file(self):
        if self._percent < 100:
            return

        # Get the file path
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        formats = obj['FORMATS']
        if len(formats) == 0:
            return

        if not self._activity and \
                not formats[0] == 'application/vnd.olpc-x-sugar':
            return

        uri = cb_service.get_object_data(self._object_id, formats[0])
        if not uri.startswith('file://'):
            return

        path = urlparse.urlparse(uri).path

        # FIXME: would be better to check for format.onDisk
        try:
            path_exists = os.path.exists(path)
        except TypeError:
            path_exists = False

        if path_exists:
            if self._activity:
                activityfactory.create_with_uri(self._activity, uri)
            else:
                self._install_xo(path)
        else:
            logging.debug("Clipboard item file path %s didn't exist" % path)
                        
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

    def _install_xo(self, path):
        logging.debug('mec')
        if os.spawnlp(os.P_WAIT, 'sugar-install-bundle', 'sugar-install-bundle',
                      path):
            raise RuntimeError, 'An error occurred while extracting the .xo contents.'
