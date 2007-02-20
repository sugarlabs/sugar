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
from sugar.graphics import button
from sugar.graphics import color
from sugar.graphics import font
from sugar.graphics.canvasicon import CanvasIcon

class Menu(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarMenu'

    __gsignals__ = {
        'action': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([object]))
    }

    def __init__(self):
        hippo.CanvasBox.__init__(self)
        self.props.background_color = color.MENU_BACKGROUND.get_int()
        self.props.border_color = color.MENU_BORDER.get_int()
        self.props.border = units.points_to_pixels(1)
        self._window = None

    def add_item(self, action_id, label, icon_name=None, icon_color=None):
        box = hippo.CanvasBox(orientation=hippo.ORIENTATION_HORIZONTAL)
        box.props.padding = 5
        box.props.spacing = 5
        if icon_name:
            icon = CanvasIcon(icon_name=icon_name,
                              scale=units.SMALL_ICON_SCALE)
            if icon_color:
                icon.props.color = icon_color
            box.append(icon)

        canvas_text = hippo.CanvasText()
        canvas_text.props.text = label
        canvas_text.props.color = color.LABEL_TEXT.get_int()
        canvas_text.props.font_desc = font.DEFAULT.get_pango_desc()
        box.append(canvas_text)

        box.connect('button-press-event', self._item_button_press_event_cb,
                    [action_id, label])
        self.append(box)
    
    def add_separator(self):
        box = hippo.CanvasBox()
        box.props.background_color = color.MENU_SEPARATOR.get_int()
        box.props.box_height = units.points_to_pixels(1)
        self.append(box)

    def show(self, x, y):
        if not self._window:
            self._window = hippo.CanvasWindow(gtk.WINDOW_POPUP)
            self._window.move(x, y)
            self._window.set_root(self)
            self._window.show()

    def hide(self):
        if self._window:
            self._window.destroy()
            self._window = None

    def _item_button_press_event_cb(self, item, event, data):
        self.emit('action', data)
        self.hide()
    
    def is_visible(self):
        return self._window != None

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
        self.append(self._round_box, hippo.PACK_EXPAND)

        self._canvas_text = hippo.CanvasText()
        self._canvas_text.props.text = _('No options')
        self._canvas_text.props.color = color.LABEL_TEXT.get_int()
        self._canvas_text.props.font_desc = font.DEFAULT.get_pango_desc()
        self._round_box.append(self._canvas_text, hippo.PACK_EXPAND)

        # TODO: Substitute for the right icon.
        arrow = button.Button(icon_name='theme:stock-close')
        arrow.props.size = button.SMALL_SIZE
        arrow.props.yalign = hippo.ALIGNMENT_CENTER
        arrow.props.xalign = hippo.ALIGNMENT_START
        self._round_box.append(arrow)

        self._menu = Menu()
        self._menu.connect('action', self._menu_action_cb)

        self.connect('button-press-event', self._button_press_event_cb)

    def do_set_property(self, pspec, value):
        if pspec.name == 'value':
            self._value = value

    def do_get_property(self, pspec):
        if pspec.name == 'value':
            return self._value

    def add_option(self, action_id, label, icon_name=None, icon_color=None):
        if not self._value:
            self._value = action_id
            self._canvas_text.props.text = label

        self._menu.add_item(action_id, label, icon_name, icon_color)

    def add_separator(self):
        self._menu.add_separator()

    def _button_press_event_cb(self, box, event):
        if self._menu.is_visible():
            self._menu.hide()
        else:
            context = self._round_box.get_context()
            #[x, y] = context.translate_to_screen(self._round_box)
            [x, y] = context.translate_to_widget(self._round_box)
            
            # TODO: Any better place to do this?
            self._menu.props.box_width = self.get_width_request()

            [width, height] = self._round_box.get_allocation()            
            self._menu.show(x, y + height)

    def _menu_action_cb(self, menu, data):
        [action_id, label] = data
        if action_id != self._value:
            self._value = action_id
            self._canvas_text.props.text = label
            self.emit('changed')
