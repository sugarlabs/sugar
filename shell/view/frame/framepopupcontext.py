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
import logging

import gobject
import gtk
import hippo

from sugar.graphics.popupcontext import PopupContext
from sugar.graphics import units

class FramePopupContext(PopupContext):
    __gtype_name__ = 'SugarFramePopupContext'
    
    def __init__(self):
        PopupContext.__init__(self)

    def get_position(self, control, popup):
        [item_x, item_y] = control.get_context().translate_to_screen(control)
        [item_w, item_h] = control.get_allocation()

        [popup_w, natural_w] = popup.get_width_request()
        [popup_h, natural_h] = popup.get_height_request(popup_w)

        left_x = item_x + item_w
        left_y = item_y
        right_x = item_x - popup_w
        right_y = item_y
        top_x = item_x
        top_y = item_y + item_h
        bottom_x = item_x
        bottom_y = item_y - popup_h

        grid_size = units.grid_to_pixels(1)
        if item_x < grid_size:
            [x, y] = [left_x, left_y]
        elif item_x >= (gtk.gdk.screen_width() - grid_size):
            [x, y] = [right_x, right_y]
        elif item_y < grid_size:
            [x, y] = [top_x, top_y]
        elif item_y >= (gtk.gdk.screen_height() - grid_size):
            [x, y] = [bottom_x, bottom_y]
        else:
            logging.error('Item not in the frame!')
            return [None, None]

        x = min(x, gtk.gdk.screen_width() - popup_w)
        x = max(0, x)

        y = min(y, gtk.gdk.screen_height() - popup_h)
        y = max(0, y)

        return [x, y]
