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

import gobject
import gtk
import hippo

from sugar.graphics import units
from sugar.graphics.roundbox import RoundBox
from sugar.graphics import button
from sugar.graphics import color
from sugar.graphics import font
from sugar.graphics.canvasicon import CanvasIcon

class Popup(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarPopup'

    __gsignals__ = {
        'action-completed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
    }

    def __init__(self, title):
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

        box.connect('button-press-event', self._item_button_press_event_cb)
        self.append(box)
    
    def add_separator(self):
        box = hippo.CanvasBox()
        box.props.background_color = color.MENU_SEPARATOR.get_int()
        box.props.box_height = units.points_to_pixels(1)
        self.append(box)

    def popup(self, x, y):
        if not self._window:
            self._window = hippo.CanvasWindow(gtk.WINDOW_POPUP)
            self._window.move(x, y)
            self._window.set_root(self)
            self._window.show()

    def popdown(self):
        if self._window:
            self._window.destroy()
            self._window = None

    def _item_button_press_event_cb(self, item, event):
        self.emit('action-completed')
