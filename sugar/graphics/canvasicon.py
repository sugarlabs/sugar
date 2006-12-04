# Copyright (C) 2006, Red Hat, Inc.
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

import re

import gobject
import gtk
import hippo
import rsvg
import cairo

from sugar.graphics.iconcolor import IconColor

class _IconCache:
    def __init__(self):
        self._icons = {}
        self._theme = gtk.icon_theme_get_default()

    def _read_icon(self, filename, color):
        icon_file = open(filename, 'r')

        if color == None:
            return rsvg.Handle(file=filename)
        else:
            data = icon_file.read()
            icon_file.close()

            fill = color.get_fill_color()
            stroke = color.get_stroke_color()
    
            entity = '<!ENTITY fill_color "%s">' % fill
            data = re.sub('<!ENTITY fill_color .*>', entity, data)

            entity = '<!ENTITY stroke_color "%s">' % stroke
            data = re.sub('<!ENTITY stroke_color .*>', entity, data)

            return rsvg.Handle(data=data)

    def get_handle(self, name, color, size):
        info = self._theme.lookup_icon(name, int(size), 0)

        if color:
            key = (info.get_filename(), color.to_string())
        else:
            key = info.get_filename()

        if self._icons.has_key(key):
            icon = self._icons[key]
        else:
            icon = self._read_icon(info.get_filename(), color)
            self._icons[key] = icon
        return icon

class CanvasIcon(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'CanvasIcon'

    __gproperties__ = {
        'icon-name': (str, None, None, None,
                      gobject.PARAM_READWRITE),
        'color'    : (object, None, None,
                      gobject.PARAM_READWRITE),
        'size'     : (int, None, None,
                      0, 1024, 24,
                      gobject.PARAM_READWRITE)
    }

    _cache = _IconCache()

    def __init__(self, **kwargs):
        self._size = 24
        self._color = None
        self._icon_name = None

        hippo.CanvasBox.__init__(self, **kwargs)

        self._buffer = None

        self.connect('button-press-event', self._button_press_event_cb)

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            self._icon_name = value
            self._buffer = None
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'color':
            self._buffer = None
            self._color = value
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'size':
            self._buffer = None
            self._size = value
            self.emit_request_changed()

    def do_get_property(self, pspec):
        if pspec.name == 'size':
            return self._size
        elif pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'color':
            return self._color

    def _get_buffer(self, cr, handle, size):
        if self._buffer == None:
            target = cr.get_target()
            surface = target.create_similar(cairo.CONTENT_COLOR_ALPHA,
                                             int(size) + 1, int(size) + 1)

            dimensions = handle.get_dimension_data()
            scale = float(size) / float(dimensions[0])

            ctx = cairo.Context(surface)
            ctx.scale(scale, scale)
            handle.render_cairo(ctx)
            del ctx

            self._buffer = surface
            self._buffer_scale = scale

        return self._buffer

    def do_paint_below_children(self, cr, damaged_box):
        icon_name = self._icon_name
        if icon_name == None:
            icon_name = 'stock-missing'

        handle = CanvasIcon._cache.get_handle(
                    icon_name, self._color, self._size)
        buf = self._get_buffer(cr, handle, self._size)

        [width, height] = self.get_allocation()
        x = (width - self._size) / 2
        y = (height - self._size) / 2
        
        cr.set_source_surface(buf, x, y)
        cr.paint()

    def do_get_width_request(self):
        return self._size

    def do_get_height_request(self, for_width):
        return self._size

    def _button_press_event_cb(self, item, event):
        item.emit_activated()
