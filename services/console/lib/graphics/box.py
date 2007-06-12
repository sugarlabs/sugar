##!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com).
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

import gtk
import gobject
import cairo

COLOR_MODE_NORMAL = 0
COLOR_MODE_REVERSE = 1

class BoxGraphic(gtk.DrawingArea):
    __gtype_name__ = 'ConsoleBoxGraphic'

    __gproperties__ = {
        'color-mode': (gobject.TYPE_INT, None, None, 0, 1, COLOR_MODE_NORMAL,
                    gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT_ONLY)

    }

    _color_status_high = [0, 0, 0]
    _color_status_medium = [0, 0, 0]
    _color_status_low = [0, 0, 0]

    _limit_high = 0
    _limit_medium = 0
    _limit_low = 0

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, **kwargs)
        gtk.DrawingArea.__init__(self)
        self.connect("expose-event", self.do_expose)
        self.connect('size-allocate', self._change_size_cb)

    def do_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(0, 0, self._width, self._height)

        context.set_source_rgb (0,0,0)
        context.fill_preserve()
        context.stroke()

        self._draw_content(context, self._percent)

    def do_set_property(self, pspec, value):
        if pspec.name == 'color-mode':
            self._configure(mode=value)
        else:
            raise AssertionError

    def set_capacity(self, percent):
        self._percent = percent
        self.queue_draw()

    def _configure(self, mode):
        # Normal mode configure the box as a battery
        # full is good, empty is bad
        if mode == COLOR_MODE_NORMAL:
            self._color_status_high = [0, 1, 0]
            self._color_status_medium = [1,1,0]
            self._color_status_low = [1,0,0]
            self._limit_high = 60
            self._limit_medium = 10
        # Reverse mode configure the box as a storage device
        # full is bad, empty is good
        elif mode == COLOR_MODE_REVERSE:
            self._color_status_high = [1,0,0] 
            self._color_status_medium = [1,1,0]
            self._color_status_low = [0, 1, 0]
            self._limit_high = 85
            self._limit_medium = 40

    def _draw_content(self, context, percent):
        usage_height = (percent*self._height)/100
        context.rectangle(0, self._height - usage_height, self._width, self._height)

        if self._percent > self._limit_high:
            context.set_source_rgb(*self._color_status_high)
        elif self._percent >= self._limit_medium and self._percent <= self._limit_high:
            context.set_source_rgb(*self._color_status_medium)
        elif self._percent < self._limit_medium:
            context.set_source_rgb(*self._color_status_low)

        context.fill_preserve()

    def _change_size_cb(self, widget, allocation):
        self._width = allocation.width
        self._height = allocation.height
        self.queue_draw()
