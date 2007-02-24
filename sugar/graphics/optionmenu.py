# Copyright (C) 2007, One Laptop Per Child
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
import sys
import logging
from gettext import gettext as _

import gobject
import gtk
import hippo

from sugar.graphics import units
from sugar.graphics.roundbox import RoundBox
from sugar.graphics.menu import Menu, MenuItem
from sugar.graphics import iconbutton
from sugar.graphics import color
from sugar.graphics import font
from sugar.graphics.canvasicon import CanvasIcon

class _Menu(Menu):
    def __init__(self):
        Menu.__init__(self)
        self._is_visible = False
    
    def is_visible(self):
        return self._is_visible
    
    def popup(self, x, y):
        Menu.popup(self, x, y)
        self._is_visible = True
    
    def popdown(self):
        Menu.popdown(self)
        self._is_visible = False

class OptionMenu(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarOptionMenu'

    __gproperties__ = {
        'value'    : (int, None, None, 0, sys.maxint, 1, gobject.PARAM_READWRITE)
    }

    __gsignals__ = {
        'changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
    }
    
    def __init__(self):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)
        self.props.yalign = hippo.ALIGNMENT_CENTER
        self._value = None
                    
        self._round_box = RoundBox()
        self._round_box.props.border_color = color.FRAME_BORDER.get_int()
        self._round_box.props.spacing = units.points_to_pixels(3)
        self._round_box.props.padding = units.points_to_pixels(1)
        self.append(self._round_box, hippo.PACK_EXPAND)

        self._canvas_text = hippo.CanvasText()
        self._canvas_text.props.text = _('No options')
        self._canvas_text.props.color = color.LABEL_TEXT.get_int()
        self._canvas_text.props.font_desc = font.DEFAULT.get_pango_desc()
        self._round_box.append(self._canvas_text, hippo.PACK_EXPAND)

        # TODO: Substitute for the right icon.
        arrow = iconbutton.IconButton(icon_name='theme:stock-close')
        arrow.props.size = iconbutton.SMALL_SIZE
        arrow.props.yalign = hippo.ALIGNMENT_CENTER
        arrow.props.xalign = hippo.ALIGNMENT_START
        self._round_box.append(arrow)

        self._menu = _Menu()
        self._menu.connect('action', self._menu_action_cb)
        self._menu.connect('action-completed', self._menu_action_completed_cb)

        self.connect('button-press-event', self._button_press_event_cb)

    def do_set_property(self, pspec, value):
        if pspec.name == 'value':
            self._value = value

    def do_get_property(self, pspec):
        if pspec.name == 'value':
            return self._value

    def add_item(self, menu_item):
        if not self._value:
            self._value = menu_item.props.action_id
            self._canvas_text.props.text = menu_item.props.label

        self._menu.add_item(menu_item)

    def add_separator(self):
        self._menu.add_separator()

    def _button_press_event_cb(self, box, event):
        if self._menu.is_visible():
            self._menu.popdown()
        else:
            context = self._round_box.get_context()
            [x, y] = context.translate_to_screen(self._round_box)
            
            # TODO: Any better place to do this?
            self._menu.props.box_width = max(self.get_width_request(),
                                             self._menu.get_width_request())

            [width, height] = self._round_box.get_allocation()            
            self._menu.popup(x, y + height)
            
            # Grab the pointer so the menu will popdown on mouse click.
            self._menu.grab_pointer()

    def _menu_action_cb(self, menu, menu_item):
        action_id = menu_item.props.action_id
        label = menu_item.props.label
        
        if action_id != self._value:
            self._value = action_id
            self._canvas_text.props.text = label
            self.emit('changed')

    def _menu_action_completed_cb(self, menu):
        self._menu.popdown()
