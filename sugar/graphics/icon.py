# Copyright (C) 2006-2007 Red Hat, Inc.
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

import os
import re
import time
import logging

import gobject
import gtk
import hippo
import rsvg
import cairo

from sugar.graphics.style import Color
from sugar.graphics.xocolor import XoColor
from sugar.graphics import style
from sugar.graphics.palette import Palette, CanvasInvoker

_BADGE_SIZE = 0.45

_svg_loader = None

def _get_svg_loader():
    global _svg_loader
    if _svg_loader == None:
        _svg_loader = _SVGLoader()
    return _svg_loader

class _SVGLoader(object):
    def load(self, file_name, entities):
        icon_file = open(file_name, 'r')
        data = icon_file.read()
        icon_file.close()

        for entity, value in entities.items():
            xml = '<!ENTITY %s "%s">' % (entity, value)
            data = re.sub('<!ENTITY %s .*>' % entity, xml, data)

        return rsvg.Handle(data=data)

class _IconBuffer(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)

        self._svg_loader = _get_svg_loader()
        self._surface = None

        self.icon_name = None
        self.file_name = None
        self.fill_color = None
        self.stroke_color = None
        self.badge_name = None
        self.width = None
        self.height = None

    def _load_svg(self, file_name):
        entities = {}
        if self.fill_color:
            entities['fill_color'] = self.fill_color
        if self.stroke_color:
            entities['stroke_color'] = self.stroke_color

        return self._svg_loader.load(file_name, entities)

    def _load_pixbuf(self, file_name):
        if self.width is None or self.height is None:
            pixbuf = gtk.gdk.pixbuf_new_from_file(file_name)
        else:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                                        file_name, self.width, self.height)
        return hippo.cairo_surface_from_gdk_pixbuf(pixbuf)

    def _get_icon_size_request(self):
        if self.width != None:
            return self.width
        else:
            return 50

    def _get_file_name(self):
        file_name = None

        if self.file_name:
            return self.file_name

        if self.icon_name:
            theme = gtk.icon_theme_get_default()
            size_request = self._get_icon_size_request()
            info = theme.lookup_icon(self.icon_name, size_request, 0)
            if info:
                return info.get_filename()

        return None

    def _render_badge(self, surface):
        context = cairo.Context(surface)
        theme = gtk.icon_theme_get_default()

        size_request = self._get_icon_size_request()
        icon_info = theme.lookup_icon(self.icon_name, size_request, 0)
        if not icon_info or not icon_info.get_attach_points():
            logging.info(
                'Badge attach points not found, icon %s.' % self.icon_name)
            return

        attach_points = icon_info.get_attach_points()
        attach_x = float(attach_points[0][0]) / size_request
        attach_y = float(attach_points[0][1]) / size_request

        badge_size = int(_BADGE_SIZE * surface.get_width())
        badge_x = attach_x * surface.get_width() - badge_size / 2
        badge_y = attach_y * surface.get_height() - badge_size / 2

        badge_info = theme.lookup_icon(self.badge_name, badge_size, 0)
        if not badge_info:
            logging.info('Badge not found, %s.' % self.badge_name)
            return

        badge_file_name = badge_info.get_filename()
        if badge_file_name.endswith('.svg'):
            handle = self._svg_loader.load(badge_file_name, {})

            context.translate(badge_x, badge_y)
            scale = float(badge_size) / float(badge_info.get_base_size())
            context.scale(scale, scale)

            handle.render_cairo(context)
        else:
            buf = gtk.gdk.pixbuf_new_from_file_at_size(
                                badge_file_name, badge_size, badge_size)
            surface = hippo.cairo_surface_from_gdk_pixbuf(buf)
            context.set_source_surface(badge_buf, badge_x, badge_y)
            context.paint()

    def get_surface(self):
        if self._surface is not None:
            return self._surface

        file_name = self._get_file_name()
        if file_name is None:
            return None

        if file_name.endswith('.svg'):
            handle = self._load_svg(file_name)

            dimensions = handle.get_dimension_data()
            icon_width = int(dimensions[0])
            icon_height = int(dimensions[1])

            if self.width is not None and self.height is not None:
                target_width = self.width
                target_height = self.height
            else:
                target_width = icon_width
                target_height = icon_height

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         target_width, target_height)

            context = cairo.Context(surface)
            context.scale(float(target_width) / float(icon_width),
                          float(target_height) / float(icon_height))
            handle.render_cairo(context)
        else:
            surface = self._load_pixbuf(file_name)

        if self.badge_name:
            self._render_badge(surface)

        self._surface = surface

        return surface

    def invalidate(self):
        self._surface = None

class Icon(gtk.Image):
    __gtype_name__ = 'SugarIcon'

    __gproperties__ = {
        'xo-color'      : (object, None, None,
                           gobject.PARAM_WRITABLE),
        'fill-color'    : (object, None, None,
                           gobject.PARAM_READWRITE),
        'stroke-color'  : (object, None, None,
                           gobject.PARAM_READWRITE),
        'badge-name'    : (str, None, None, None,
                           gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs):
        self._buffer = _IconBuffer()

        gobject.GObject.__init__(self, **kwargs)

    def _sync_image_properties(self):
        if self._buffer.icon_name != self.props.icon_name:
            self._buffer.icon_name = self.props.icon_name
            self._buffer.invalidate()

        if self._buffer.file_name != self.props.file:
            self._buffer.file_name = self.props.file
            self._buffer.invalidate()

        width, height = gtk.icon_size_lookup(self.props.icon_size)
        if self._buffer.width != width and self._buffer.height != height:
            self._buffer.width = width
            self._buffer.height = height
            self._buffer.invalidate()

    def _icon_size_changed_cb(self, image, pspec):
        self._buffer.icon_size = self.props.icon_size
        self._buffer.invalidate()

    def _icon_name_changed_cb(self, image, pspec):
        self._buffer.icon_name = self.props.icon_name
        self._buffer.invalidate()

    def _file_changed_cb(self, image, pspec):
        self._buffer.file_name = self.props.file
        self._buffer.invalidate()

    def _update_buffer_size(self):
        width, height = gtk.icon_size_lookup(self.props.icon_size)

        self._buffer.width = width
        self._buffer.height = height

        self._buffer.invalidate()

    def do_expose_event(self, event):
        self._sync_image_properties()

        surface = self._buffer.get_surface()
        if surface is not None:
            cr = self.window.cairo_create()

            x = self.allocation.x
            y = self.allocation.y

            cr.set_source_surface(surface, x, y)
            cr.paint()

    def do_set_property(self, pspec, value):
        if pspec.name == 'xo-color':
            self.props.fill_color = value.get_fill_color()
            self.props.stroke_color = value.get_stroke_color()
        elif pspec.name == 'fill-color':
            self._buffer.fill_color = value
            self._buffer.invalidate()
        elif pspec.name == 'stroke-color':
            self._buffer.fill_color = value
            self._buffer.invalidate()
        elif pspec.name == 'badge-name':
            self._buffer.badge_name = value
            self._buffer.invalidate()
        else:
            gtk.Image.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'fill-color':
            return self._buffer.fill_color
        elif pspec.name == 'stroke-color':
            return self._buffer.stroke_color
        elif pspec.name == 'badge-name':
            return self._buffer.badge_name
        else:
            return gtk.Image.do_get_property(self, pspec)

_ICON_REQUEST_SIZE = 50

class _IconCacheIcon:
    def __init__(self, name, fill_color, stroke_color, now):
        self.last_used = now
        self.usage_count = 1
        self.badge_x = 1.0 - _BADGE_SIZE / 2
        self.badge_y = 1.0 - _BADGE_SIZE / 2

        if name[0:6] == "theme:": 
            info = gtk.icon_theme_get_default().lookup_icon(
                name[6:], _ICON_REQUEST_SIZE, 0)
            if not info:
                raise ValueError("Icon '" + name + "' not found.")

            fname = info.get_filename()
            attach_points = info.get_attach_points()
            if attach_points is not None:
                self.badge_x = float(attach_points[0][0]) / _ICON_REQUEST_SIZE
                self.badge_y = float(attach_points[0][1]) / _ICON_REQUEST_SIZE
            del info
        else:
            fname = name

        self.handle = self._read_icon_data(fname, fill_color, stroke_color)

    def _read_icon_data(self, filename, fill_color, stroke_color):
        icon_file = open(filename, 'r')
        data = icon_file.read()
        icon_file.close()

        if fill_color:
            entity = '<!ENTITY fill_color "%s">' % fill_color
            data = re.sub('<!ENTITY fill_color .*>', entity, data)

        if stroke_color:
            entity = '<!ENTITY stroke_color "%s">' % stroke_color
            data = re.sub('<!ENTITY stroke_color .*>', entity, data)

        self.data_size = len(data)
        return rsvg.Handle(data=data)

class _IconCache:
    _CACHE_MAX = 50000   # in bytes

    def __init__(self):
        self._icons = {}
        self._cache_size = 0

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

    def get_icon(self, name, fill_color, stroke_color):
        if not name:
            return None

        if fill_color or stroke_color:
            key = (name, fill_color, stroke_color)
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
            icon = _IconCacheIcon(name, fill_color, stroke_color, now)
            self._icons[key] = icon
            self._cache_size += icon.data_size
        return icon


class CanvasIcon(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'CanvasIcon'

    __gproperties__ = {
        'icon-name'     : (str, None, None, None,
                           gobject.PARAM_READWRITE),
        'xo-color'      : (object, None, None,
                           gobject.PARAM_WRITABLE),
        'fill-color'    : (object, None, None,
                           gobject.PARAM_READWRITE),
        'stroke-color'  : (object, None, None,
                           gobject.PARAM_READWRITE),
        'size'          : (int, None, None, 0, 1024, 0,
                           gobject.PARAM_READWRITE),
        'scale'         : (int, None, None, 0, 1024, 0,
                           gobject.PARAM_READWRITE),
        'cache'         : (bool, None, None, False,
                           gobject.PARAM_READWRITE),
        'active'        : (bool, None, None, True,
                           gobject.PARAM_READWRITE),
        'badge-name'    : (str, None, None, None,
                           gobject.PARAM_READWRITE)
    }

    _cache = _IconCache()

    def __init__(self, **kwargs):
        self._buffers = {}
        self._cur_buffer = None
        self._size = 0
        self._scale = 0
        self._fill_color = None
        self._stroke_color = None
        self._icon_name = None
        self._cache = False
        self._icon = None
        self._active = True
        self._palette = None
        self._badge_name = None
        self._badge_icon = None

        hippo.CanvasBox.__init__(self, **kwargs)
        
        self.connect_after('motion-notify-event', self._motion_notify_event_cb)

    def _clear_buffers(self):
        icon_key = self._get_current_buffer_key(self._icon_name)
        badge_key = None
        if self._badge_name:
            badge_key = self._get_current_buffer_key(self._badge_name)
        for key in self._buffers.keys():
            if key != icon_key:
                if not badge_key or (key != badge_key):
                    del self._buffers[key]
        self._buffers = {}

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            if self._icon_name != value and not self._cache:
                self._clear_buffers()
            self._icon_name = value
            self._icon = None
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'xo-color':
            self.props.fill_color = style.Color(value.get_fill_color())
            self.props.stroke_color = style.Color(value.get_stroke_color())
        elif pspec.name == 'fill-color':
            if self._fill_color != value:
                if not self._cache:
                    self._clear_buffers()
                self._fill_color = value
                self._icon = None
                self._badge_icon = None
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'stroke-color':
            if self._stroke_color != value:
                if not self._cache:
                    self._clear_buffers()
                self._stroke_color = value
                self._icon = None
                self._badge_icon = None
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'size':
            if self._size != value and not self._cache:
                self._clear_buffers()
            self._size = value
            self.emit_request_changed()
        elif pspec.name == 'scale':
            if self._scale != value and not self._cache:
                self._clear_buffers()
            self._scale = value
            self.emit_request_changed()
        elif pspec.name == 'cache':
            self._cache = value
        elif pspec.name == 'active':
            if self._active != value:
                if not self._cache:
                    self._clear_buffers()
                self._active = value
                self._icon = None
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'badge-name':
            if self._badge_name != value and not self._cache:
                self._clear_buffers()
            self._badge_name = value
            self._badge_icon = None
            self.emit_paint_needed(0, 0, -1, -1)

    def _choose_colors(self):
        fill_color = None
        stroke_color = None
        if self._active:
            if self._fill_color:
                fill_color = self._fill_color.get_svg()
            if self._stroke_color:
                stroke_color = self._stroke_color.get_svg()
        else:
            stroke_color = color.ICON_STROKE_INACTIVE.get_svg()
            if self._fill_color:
                fill_color = self._fill_color.get_svg()
        return [fill_color, stroke_color]

    def _get_icon_from_cache(self, name, icon):
        if not icon:
            cache = CanvasIcon._cache

            [fill_color, stroke_color] = self._choose_colors()

            icon = cache.get_icon(name, fill_color, stroke_color)
        return icon

    def _get_icon(self):
        self._icon = self._get_icon_from_cache(self._icon_name, self._icon)
        return self._icon

    def _get_badge_icon(self):
        self._badge_icon = self._get_icon_from_cache(self._badge_name,
                                                     self._badge_icon)
        return self._badge_icon

    def _get_current_buffer_key(self, name):
        [fill_color, stroke_color] = self._choose_colors()
        return (name, fill_color, stroke_color, self._size)

    def do_get_property(self, pspec):
        if pspec.name == 'size':
            return self._size
        elif pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'fill-color':
            return self._fill_color
        elif pspec.name == 'stroke-color':
            return self._stroke_color
        elif pspec.name == 'cache':
            return self._cache
        elif pspec.name == 'active':
            return self._active
        elif pspec.name == 'badge-name':
            return self._badge_name
        elif pspec.name == 'scale':
            return self._scale

    def _get_icon_size(self, icon):
        if icon:
            dimensions = icon.handle.get_dimension_data()
            return int(dimensions[0]), int(dimensions[1])
        else:
            return [0, 0]

    def _get_size(self, icon):
        width, height = self._get_icon_size(icon)
        if self._scale != 0:
            width = int(width * self._scale)
            height = int(height * self._scale)
        elif self._size != 0:
            width = height = self._size

        return [width, height]

    def _get_buffer(self, cr, name, icon, scale_factor=None):
        """Return a cached cairo surface for the SVG icon, or if none exists,
        create a new cairo surface with the right size."""
        buf = None

        key = self._get_current_buffer_key(name)
        if self._buffers.has_key(key):
            buf = self._buffers[key]
        else:
            [icon_w, icon_h] = self._get_icon_size(icon)
            [target_w, target_h] = self._get_size(icon)

            if scale_factor:
                target_w = int(target_w * scale_factor)
                target_h = int(target_h * scale_factor)

            target = cr.get_target()
            buf = target.create_similar(cairo.CONTENT_COLOR_ALPHA,
                                        target_w, target_h)
            ctx = cairo.Context(buf)
            ctx.scale(float(target_w) / float(icon_w),
                      float(target_h) / float(icon_h))
            icon.handle.render_cairo(ctx)

            del ctx
            self._buffers[key] = buf

        return buf

    def do_paint_below_children(self, cr, damaged_box):
        icon = self._get_icon()
        if icon is None:
            return

        icon_buf = self._get_buffer(cr, self._icon_name, icon)
        [width, height] = self.get_allocation()
        icon_x = (width - icon_buf.get_width()) / 2
        icon_y = (height - icon_buf.get_height()) / 2

        cr.set_source_surface(icon_buf, icon_x, icon_y)
        cr.paint()

        if self._badge_name:
            badge_icon = self._get_badge_icon()
            if badge_icon:
                badge_buf = self._get_buffer(cr, self._badge_name, badge_icon, _BADGE_SIZE)
                badge_x = (icon_x + icon.badge_x * icon_buf.get_width() -
                           badge_buf.get_width() / 2)
                badge_y = (icon_y + icon.badge_y * icon_buf.get_height() -
                           badge_buf.get_height() / 2)
                cr.set_source_surface(badge_buf, badge_x, badge_y)
                cr.paint()

    def do_get_content_width_request(self):
        icon = self._get_icon()
        [width, height] = self._get_size(icon)
        if self._badge_name is not None:
            # If the badge goes outside the bounding box, add space
            # on *both* sides (to keep the main icon centered)
            if icon.badge_x < 0.0:
                width = int(width * 2 * (1.0 - icon.badge_x))
            elif icon.badge_x + _BADGE_SIZE > 1.0:
                width = int(width * 2 * (icon.badge_x + _BADGE_SIZE - 1.0))
        return (width, width)

    def do_get_content_height_request(self, for_width):
        icon = self._get_icon()
        [width, height] = self._get_size(icon)
        if self._badge_name is not None:
            if icon.badge_y < 0.0:
                height = int(height * 2 * (1.0 - icon.badge_y))
            elif icon.badge_y + _BADGE_SIZE > 1.0:
                height = int(height * 2 * (icon.badge_y + _BADGE_SIZE - 1.0))
        return (height, height)

    def do_button_press_event(self, event):
        self.emit_activated()
        return True

    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.prelight(True)
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.prelight(False)
        return False

    def prelight(self, enter):
        """
        Override this method for adding prelighting behavior.
        """
        pass

    def get_palette(self):
        return self._palette
    
    def set_palette(self, palette):
        self._palette = palette
        if not self._palette.props.invoker:
            self._palette.props.invoker = CanvasInvoker(self)

    def set_tooltip(self, text):
        self.set_palette(Palette(text))
    
    palette = property(get_palette, set_palette)

def get_icon_state(base_name, perc):
        step = 5
        strength = round(perc / step) * step
        icon_theme = gtk.icon_theme_get_default()

        while strength <= 100:
            icon_name = '%s-%03d' % (base_name, strength)
            if icon_theme.has_icon(icon_name):
                return 'theme:' + icon_name

            strength = strength + step
