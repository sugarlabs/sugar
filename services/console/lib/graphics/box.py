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
import cairo

class BoxGraphic(gtk.DrawingArea):
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose-event", self.do_expose)
        self.connect('size-allocate', self._change_size_cb)
        self.set_capacity(0)

    def do_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(0, 0, self._width, self._height)

        context.set_source_rgb (0,0,0)
        context.fill_preserve()
        context.stroke()
        
        print self._percent
        self._draw_content(context, self._percent)

    def set_capacity(self, percent):
        self._percent = percent
        self.queue_draw()

    def _draw_content(self, context, percent):
        usage_height = (percent*self._height)/100

        context.rectangle(0, self._height - usage_height, self._width, self._height)

        if self._percent > 50:
            context.set_source_rgb (0,1,0)

        if self._percent > 10 and self._percent <= 50:
            context.set_source_rgb (1,1,0)

        if self._percent <= 10:
            context.set_source_rgb (1,0,0)

        context.fill_preserve()

    def _change_size_cb(self, widget, allocation):
        self._width = allocation.width
        self._height = allocation.height
        self.queue_draw()
