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

class HorizontalGraphic(gtk.DrawingArea):
    _MARGIN = 5
    _LINE_WIDTH = 2
    _GRAPH_OFFSET = 7
    _range_x = []
    _range_y = []
    _frequency_timer = 0

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.connect('expose-event', self.do_expose)
        self.connect('size-allocate', self._change_size_cb)
        self._buffer = [0]

    def do_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(0, 0, self._width - 1, self._height - 1)
        context.set_source_rgb (0,0,0)
        context.fill_preserve()
        context.set_line_width(self._LINE_WIDTH)

        if event.area.x == 0:
            draw_all = True
            self._draw_border_lines(context)
            context.stroke()
        else:
            draw_all = False
            context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
            context.clip()

        context.set_source_rgb(1, 1, 1)
        self._draw_buffer(event, widget, context, draw_all)
        context.stroke()

        self._updated = False
        return False

    def draw_value(self, percent):
        redraw_all = False

        if (len(self._buffer) + 1) *self._GRAPH_OFFSET >= self._width:
            redraw_all = True
            self._buffer = [self._buffer[-1]]
            length = 1
        else:
            length = len(self._buffer) - 1

        self._buffer.append(percent)
        self._updated = True

        if redraw_all:
            area_x = 0
            area_y = 0
            height = self._height
            width = self._width
        else:
            area_x = self._graph_x + (length*self._GRAPH_OFFSET)
            area_y = self._graph_y
            width = self._GRAPH_OFFSET*2
            height = self._graph_height

        self.queue_draw_area(area_x, area_y, width, height)
        self._frequency_timer += 1

        return True

    def _draw_border_lines(self, context):
        context.set_source_rgb(1, 1, 1)
        self._draw_line(context, self._MARGIN, self._MARGIN, self._MARGIN, self._height - self._MARGIN)
        self._draw_line(context, self._MARGIN, self._height - self._MARGIN - 1, self._width - self._MARGIN, self._height - self._MARGIN - 1)

    def _draw_line(self, context, from_x, from_y, to_x, to_y):               
        context.move_to(from_x, from_y)
        context.line_to(to_x, to_y)         

    def _draw_buffer(self, event, drwarea, context, draw_all=True):
        buffer_offset = 0
        freq = 1 # Frequency timer

        length = len(self._buffer)
        
        if length == 0:
            return

        # Context properties
        context.set_line_width(self._LINE_WIDTH)
        context.set_source_rgb(0,1,0)

        if draw_all == True:
            buffer_offset = 0
            freq = 0
        else:
            freq = buffer_offset = (event.area.x/self._GRAPH_OFFSET)

        for percent in self._buffer[buffer_offset:length]:
            if buffer_offset == 0:
                from_y = self._get_y(self._buffer[0])
                from_x = self._graph_x
            else:
                from_y = self._get_y(self._buffer[buffer_offset-1])
                from_x = (freq * self._GRAPH_OFFSET)

            to_x = (freq+1) * self._GRAPH_OFFSET
            to_y = self._get_y(percent)

            self._draw_line(context, from_x, from_y, to_x, to_y)
            buffer_offset+=1
            freq+=1

        context.stroke()

    def _get_y(self, percent):
        if percent==0:
            percent = 1
        
        graph_y = ((self._height)/(100 - 1))*(percent - 1)
        y = self._LINE_WIDTH + abs(abs(self._height - graph_y) - self._MARGIN*2)
        return int(y)

    def _change_size_cb(self, widget, allocation):
        self._width = allocation.width
        self._height = allocation.height

        self._graph_x = self._MARGIN + self._LINE_WIDTH
        self._graph_y = self._MARGIN
        self._graph_width = self._width - (self._MARGIN*2 + self._LINE_WIDTH)
        self._graph_height = self._height - ((self._MARGIN*2 + self._LINE_WIDTH))
