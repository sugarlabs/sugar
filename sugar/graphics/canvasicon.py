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
import time

from sugar.graphics.iconcolor import IconColor

class _IconCacheIcon:
    def __init__(self, name, color, now):
        self.data_size = None
        self.handle = self._read_icon_data(name, color)
        self.last_used = now
        self.usage_count = 1

    def _read_icon_data(self, filename, color):
        icon_file = open(filename, 'r')
        data = icon_file.read()
        icon_file.close()

        if color:
            fill = color.get_fill_color()
            stroke = color.get_stroke_color()

            entity = '<!ENTITY fill_color "%s">' % fill
            data = re.sub('<!ENTITY fill_color .*>', entity, data)

            entity = '<!ENTITY stroke_color "%s">' % stroke
            data = re.sub('<!ENTITY stroke_color .*>', entity, data)

        self.data_size = len(data)
        return rsvg.Handle(data=data)

class _IconCache:
    _CACHE_MAX = 50000   # in bytes

    def __init__(self):
        self._icons = {}
        self._theme = gtk.icon_theme_get_default()
        self._cache_size = 0

    def _get_real_name_from_theme(self, name, size):
        info = self._theme.lookup_icon(name, size, 0)
        if not info:
            raise ValueError("Icon '" + name + "' not found.")
        fname = info.get_filename()
        del info
        return fname

    def _cache_cleanup(self, key, now):
        while self._cache_size > self._CACHE_MAX:
            evict_key = None
            oldest_key = None
            oldest_time = now
            for icon_key, icon in self._icons.items():
                # Don't evict the icon we are about to use if it's in the cache
                if icon_key == key:
                    continue

                # evict large icons first
                if icon.data_size > self._CACHE_MAX:
                    evict_key = icon_key
                    break
                # evict older icons next; those used over 2 minutes ago
                if icon.last_used < now - 120:
                    evict_key = icon_key
                    break
                # otherwise, evict the oldest
                if oldest_time > icon.last_used:
                    oldest_time = icon.last_used
                    oldest_key = icon_key

            # If there's nothing specific to evict, try evicting
            # the oldest thing
            if not evict_key:
                if not oldest_key:
                    break
                evict_key = oldest_key

            self._cache_size -= self._icons[evict_key].data_size
            del self._icons[evict_key]

    def get_handle(self, name, color, size):
        if name[0:6] == "theme:": 
            name = self._get_real_name_from_theme(name[6:], size)

        if color:
            key = (name, color.to_string())
        else:
            key = name

        # If we're over the cache limit, evict something from the cache
        now = time.time()
        self._cache_cleanup(key, now)

        if self._icons.has_key(key):
            icon = self._icons[key]
            icon.usage_count += 1
            icon.last_used = now
        else:
            icon = _IconCacheIcon(name, color, now)
            self._icons[key] = icon
            self._cache_size += icon.data_size
        return icon.handle


class CanvasIcon(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'CanvasIcon'

    __gproperties__ = {
        'icon-name': (str, None, None, None,
                      gobject.PARAM_READWRITE),
        'color'    : (object, None, None,
                      gobject.PARAM_READWRITE),
        'size'     : (int, None, None,
                      0, 1024, 24,
                      gobject.PARAM_READWRITE),
        'cache'    : (bool, None, None, False,
                      gobject.PARAM_READWRITE)
    }

    _cache = _IconCache()

    def __init__(self, **kwargs):
        self._buffers = {}
        self._cur_buffer = None
        self._size = 24
        self._color = None
        self._icon_name = None
        self._cache = False

        hippo.CanvasBox.__init__(self, **kwargs)

        self.connect('button-press-event', self._button_press_event_cb)

    def _clear_buffers(self):
        cur_buf_key = self._get_current_buffer_key()
        for key in self._buffers.keys():
            if key != cur_buf_key:
                del self._buffers[key]
        self._buffers = {}

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            if self._icon_name != value and not self._cache:
                self._clear_buffers()
            self._icon_name = value
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'color':
            if self._color != value and not self._cache:
                self._clear_buffers()
            self._color = value
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'size':
            if self._size != value and not self._cache:
                self._clear_buffers()
            self._size = value
            self.emit_request_changed()
        elif pspec.name == 'cache':
            self._cache = value

    def _get_current_buffer_key(self):
        return (self._icon_name, self._color, self._size)

    def do_get_property(self, pspec):
        if pspec.name == 'size':
            return self._size
        elif pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'color':
            return self._color
        elif pspec.name == 'cache':
            return self._cache

    def _get_buffer(self, cr, handle):
        key = self._get_current_buffer_key()
        buf = None
        if self._buffers.has_key(key):
            buf = self._buffers[key]
        else:
            target = cr.get_target()
            size = int(self._size) + 1
            buf = target.create_similar(cairo.CONTENT_COLOR_ALPHA, size, size)

            dimensions = handle.get_dimension_data()
            scale = float(size) / float(dimensions[0])

            ctx = cairo.Context(buf)
            ctx.scale(scale, scale)
            handle.render_cairo(ctx)
            del ctx
            self._buffers[key] = buf

        return buf

    def do_paint_below_children(self, cr, damaged_box):
        icon_name = self._icon_name
        if icon_name == None:
            icon_name = 'theme:stock-missing'

        handle = CanvasIcon._cache.get_handle(
                    icon_name, self._color, self._size)
        buf = self._get_buffer(cr, handle)

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
