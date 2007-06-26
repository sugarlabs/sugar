# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

#
# DEPRECATED. Do not use in new code. We will reimplement it in gtk
#

import sys

import gtk
import hippo
import gobject

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.popup import Popup
from sugar.graphics.roundbox import RoundBox
from sugar.graphics import color
from sugar.graphics import font
from sugar.graphics import units

class MenuItem(hippo.CanvasBox):
    __gtype_name__ = 'SugarMenuItem'

    __gproperties__ = {
        'action-id': (object, None, None,
                      gobject.PARAM_READWRITE),
        'label'    : (str, None, None, None,
                      gobject.PARAM_READWRITE)
    }

    def __init__(self, action_id, label, icon_name=None, icon_color=None):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)
        
        self._action_id = action_id
        self.props.spacing = units.points_to_pixels(2)
        self.props.padding = units.points_to_pixels(2)

        if icon_name:
            icon = CanvasIcon(icon_name=icon_name,
                              scale=units.SMALL_ICON_SCALE,
                              box_width=units.microgrid_to_pixels(2),
                              box_height=units.microgrid_to_pixels(2))
            if icon_color:
                icon.props.xo_color = icon_color
            self.append(icon)

        self._canvas_text = hippo.CanvasText(text=label)
        self._canvas_text.props.color = color.LABEL_TEXT.get_int()
        self._canvas_text.props.font_desc = font.DEFAULT.get_pango_desc()
        self.append(self._canvas_text)
        
        self.connect('motion-notify-event', self._motion_notify_event_cb)
        
    def _motion_notify_event_cb(self, menu_item, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.props.background_color = color.MENU_BACKGROUND_HOVER.get_int()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.props.background_color = color.MENU_BACKGROUND.get_int()

    def do_set_property(self, pspec, value):
        if pspec.name == 'action-id':
            self._action_id = value
        elif pspec.name == 'label':
            self._canvas_text.props.text = value
        else:
            hippo.CanvasBox.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'action-id':
            return self._action_id
        elif pspec.name == 'label':
            return self._canvas_text.props.text
        else:
            return hippo.CanvasBox.do_get_property(self, pspec)

class Menu(Popup):
    __gtype_name__ = 'SugarCanvasMenu'

    __gsignals__ = {
        'action': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([object]))
    }

    def __init__(self, title=None):
        Popup.__init__(self)

        self.props.background_color = color.MENU_BACKGROUND.get_int()
        self.props.border_color = color.MENU_BORDER.get_int()
        self.props.border = units.points_to_pixels(1) 

        self._title_item = None
        if title:
            self._title_item = hippo.CanvasText(text=title)
            self._title_item.props.color = color.LABEL_TEXT.get_int()
            self._title_item.props.font_desc = font.DEFAULT.get_pango_desc()
            self._title_item.props.padding = units.points_to_pixels(2)
            self.append(self._title_item)
            self.add_separator()

    def add_item(self, item):
        item.connect('button-press-event', self._item_button_press_event_cb)
        self.append(item)

    def remove_item(self, item):
        self.remove(item)

    def add_separator(self):
        box = hippo.CanvasBox()
        box.props.padding = units.points_to_pixels(2)
        self.append(box)
        
        separator = hippo.CanvasBox()
        separator.props.background_color = color.MENU_SEPARATOR.get_int()
        separator.props.box_height = units.points_to_pixels(1)
        box.append(separator)

    def _item_button_press_event_cb(self, menu_item, event):
        self.emit('action', menu_item)

    def set_title(self, title):
        # FIXME: allow adding a title after __init__ when hippo support is complete
        if self._title_item:
            self._title_item.props.text = title
