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

import gobject
import hippo

from canvasicon import CanvasIcon
from iconcolor import IconColor
from sugar.graphics import units
from sugar import profile
            
STANDARD_SIZE = 0
SMALL_SIZE    = 1

class Button(hippo.CanvasBox):
    __gtype_name__ = 'Button'    

    __gproperties__ = {
        'icon-name' : (str, None, None, None,
                       gobject.PARAM_READWRITE),
        'size'      : (int, None, None,
                       0, sys.maxint, STANDARD_SIZE,
                       gobject.PARAM_READWRITE),
        'active'    : (bool, None, None, True,
                       gobject.PARAM_READWRITE)
    }

    def __init__(self, icon_name):
        self._normal_color = IconColor('white')
        self._prelight_color = profile.get_color()
        self._inactive_color = IconColor('#808080,#424242')
        self._active = True

        self._icon = CanvasIcon(icon_name=icon_name, cache=True,
                                color=self._normal_color)
        self._connect_signals(self._icon)

        hippo.CanvasBox.__init__(self)

        self._set_size(STANDARD_SIZE)

        self.append(self._icon, hippo.PACK_EXPAND)

    def _set_size(self, size):
        if size == SMALL_SIZE:
            self.props.box_width = -1
            self.props.box_height = -1
            self._icon.props.scale = units.SMALL_ICON_SCALE
        else:
            self.props.box_width = units.grid_to_pixels(1)
            self.props.box_height = units.grid_to_pixels(1)
            self._icon.props.scale = units.STANDARD_ICON_SCALE

        self._size = size

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            self._icon.props.icon_name = value
        elif pspec.name == 'size':
            self._set_size(value)
        elif pspec.name == 'active':
            self._active = value
            if self._active:
                self._icon.props.color = self._normal_color
            else:
                self._icon.props.color = self._inactive_color            
        else:
            hippo.CanvasBox.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'icon-name':
            return self._icon.props.icon_name
        elif pspec.name == 'size':
            return self._icon.props.size
        elif pspec.name == 'active':
            return self._active
        else:
            return hippo.CanvasBox.get_property(self, pspec)

    def _connect_signals(self, item):
        item.connect('button-release-event', self._button_release_event_cb)
        # TODO: Prelighting is disabled by now. Need to figure how we want it to behave.
        #item.connect('motion-notify-event', self._motion_notify_event_cb)

    def _button_release_event_cb(self, widget, event):
        if self._active:
            self.emit_activated()

    def _motion_notify_event_cb(self, widget, event):
        if self._active and event.detail == hippo.MOTION_DETAIL_ENTER:
            self._icon.props.color = self._prelight_color
        elif self._active and event.detail == hippo.MOTION_DETAIL_LEAVE:
            self._icon.props.color = self._normal_color
