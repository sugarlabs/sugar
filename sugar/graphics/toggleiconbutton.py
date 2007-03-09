# Copyright (C) 2007, Red Hat
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

import gobject

from sugar.graphics.iconbutton import IconButton
from sugar.graphics import color
            
class ToggleIconButton(IconButton):
    __gtype_name__ = 'SugarToggleIconButton'    

    __gproperties__ = {
        'toggled' : (bool, None, None, False,
                     gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs):
        self._toggled = False

        IconButton.__init__(self, **kwargs)

        self.connect('button-press-event',
                     self._toggle_icon_button_press_event_cb)

    def _get_bg_color(self):
        if self._toggled:
            col = color.TOGGLE_BUTTON_BACKGROUND
        else:
            col = color.BUTTON_BACKGROUND_NORMAL

        return col.get_int()

    def _set_toggled(self, toggled):
        self._toggled = toggled
        self.props.background_color = self._get_bg_color()

    def do_set_property(self, pspec, value):
        if pspec.name == 'toggled':
            self._set_toggled(value)
        else:
            IconButton.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'toggled':
            return self._toggled

        return IconButton.do_get_property(self, pspec)

    def _toggle_icon_button_press_event_cb(self, widget, event):
        self.props.toggled = not self._toggled
        return True

    def prelight(self, enter):
        if enter:
            IconButton.prelight(self, enter)
        else:
            self.props.background_color = self._get_bg_color()
