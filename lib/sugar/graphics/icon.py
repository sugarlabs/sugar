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
import math
import time
import logging

import gobject
import gtk
import hippo
import cairo

from sugar.graphics.style import Color
from sugar.graphics.xocolor import XoColor
from sugar.graphics import style
from sugar.graphics.palette import Palette, CanvasInvoker
from sugar.util import LRU

_BADGE_SIZE = 0.45

class _SVGLoader(object):
    def __init__(self):
        self._cache = LRU(50)

    def load(self, file_name, entities, cache):
        if file_name in self._cache:
            icon = self._cache[file_name]
        else:
            icon_file = open(file_name, 'r')
            icon = icon_file.read()
            icon_file.close()

            if cache:
                self._cache[file_name] = icon

        for entity, value in entities.items():
            if isinstance(value, basestring):
                xml = '<!ENTITY %s "%s">' % (entity, value)
                icon = re.sub('<!ENTITY %s .*>' % entity, xml, icon)
            else:
                logging.error(
                    'Icon %s, entity %s is invalid.', file_name, entity)

        import rsvg # XXX this is very slow!  why?
        return rsvg.Handle(data=icon)

class _IconInfo(object):
    def __init__(self):
        self.file_name = None
        self.attach_x = 0
        self.attach_y = 0

class _BadgeInfo(object):
    def __init__(self):
        self.attach_x = 0
        self.attach_y = 0
        self.size = 0
        self.icon_padding = 0

class _IconBuffer(object):
    _surface_cache = LRU(50)
    _loader = _SVGLoader()

    def __init__(self):
        self.icon_name = None
        self.file_name = None
        self.fill_color = None
        self.stroke_color = None
        self.badge_name = None
        self.width = None
        self.height = None
        self.cache = False
        self.scale = 1.0

    def _get_cache_key(self):
        return (self.icon_name, self.file_name, self.fill_color,
                self.stroke_color, self.badge_name, self.width, self.height)

    def _load_svg(self, file_name):
        entities = {}
        if self.fill_color:
            entities['fill_color'] = self.fill_color
        if self.stroke_color:
            entities['stroke_color'] = self.stroke_color

        return self._loader.load(file_name, entities, self.cache)

    def _get_attach_points(self, info, size_request):
        attach_points = info.get_attach_points()

        if attach_points:
            attach_x = float(attach_points[0][0]) / size_request
            attach_y = float(attach_points[0][1]) / size_request
        else:
            attach_x = attach_y = 0

        return attach_x, attach_y

    def _get_icon_info(self):
        icon_info = _IconInfo()

        if self.file_name:
            icon_info.file_name = self.file_name
        elif self.icon_name:
            theme = gtk.icon_theme_get_default()

            size = 50
            if self.width != None:
                size = self.width

            info = theme.lookup_icon(self.icon_name, size, 0)
            if info:
                attach_x, attach_y = self._get_attach_points(info, size)

                icon_info.file_name = info.get_filename()
                icon_info.attach_x = attach_x
                icon_info.attach_y = attach_y

                del info
            else:
                logging.warning('No icon with the name %s '
                                'was found in the theme.' % self.icon_name)

        return icon_info

    def _draw_badge(self, context, size):
        theme = gtk.icon_theme_get_default()
        badge_info = theme.lookup_icon(self.badge_name, size, 0)
        if badge_info:
            badge_file_name = badge_info.get_filename()
            if badge_file_name.endswith('.svg'):
                handle = self._loader.load(badge_file_name, {}, self.cache)
                handle.render_cairo(context)
            else:
                pixbuf = gtk.gdk.pixbuf_new_from_file(badge_file_name)
                surface = hippo.cairo_surface_from_gdk_pixbuf(pixbuf)
                context.set_source_surface(surface, 0, 0)
                context.paint()

    def _get_size(self, icon_width, icon_height, padding):
        if self.width is not None and self.height is not None:
            width = self.width + padding
            height = self.height + padding
        else:
            width = icon_width + padding
            height = icon_height + padding

        return width, height

    def _get_badge_info(self, icon_info, icon_width, icon_height):
        info = _BadgeInfo()
        if self.badge_name is None:
            return info

        info.size = int(_BADGE_SIZE * icon_width)
        info.attach_x = int(icon_info.attach_x * icon_width - info.size / 2)
        info.attach_y = int(icon_info.attach_y * icon_height - info.size / 2)

        if info.attach_x < 0 or info.attach_y < 0:
            info.icon_padding = max(-info.attach_x, -info.attach_y)
        elif info.attach_x + info.size > icon_width or \
             info.attach_y + info.size > icon_height:
            x_padding = info.attach_x + info.size - icon_width
            y_padding = info.attach_y + info.size - icon_height
            info.icon_padding = max(x_padding, y_padding)

        return info

    def _get_xo_color(self):
        if self.stroke_color and self.fill_color:
            return XoColor('%s,%s' % (self.stroke_color, self.fill_color))
        else:
            return None

    def _set_xo_color(self, xo_color):
        if xo_color:
            self.stroke_color = xo_color.get_stroke_color()
            self.fill_color = xo_color.get_fill_color()
        else:
            self.stroke_color = None
            self.fill_color = None

    def get_surface(self):
        cache_key = self._get_cache_key()
        if cache_key in self._surface_cache:
            return self._surface_cache[cache_key]

        icon_info = self._get_icon_info()
        if icon_info.file_name is None:
            return None

        is_svg = icon_info.file_name.endswith('.svg')

        if is_svg:
            handle = self._load_svg(icon_info.file_name)
            dimensions = handle.get_dimension_data()
            icon_width = int(dimensions[0])
            icon_height = int(dimensions[1])
        else:
            pixbuf = gtk.gdk.pixbuf_new_from_file(icon_info.file_name)
            icon_width = pixbuf.get_width()
            icon_height = pixbuf.get_height()

        badge_info = self._get_badge_info(icon_info, icon_width, icon_height)

        padding = badge_info.icon_padding
        width, height = self._get_size(icon_width, icon_height, padding)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        context = cairo.Context(surface)
        context.scale(float(width) / (icon_width + padding * 2),
                      float(height) / (icon_height + padding * 2))
        context.save()

        context.translate(padding, padding)
        if is_svg:
            handle.render_cairo(context)
        else:
            pixbuf_surface = hippo.cairo_surface_from_gdk_pixbuf(pixbuf)
            context.set_source_surface(pixbuf_surface, 0, 0)
            context.paint()

        if self.badge_name:
            context.restore()
            context.translate(badge_info.attach_x, badge_info.attach_y)
            self._draw_badge(context, badge_info.size)

        self._surface_cache[cache_key] = surface

        return surface

    xo_color = property(_get_xo_color, _set_xo_color)

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

        if self._buffer.file_name != self.props.file:
            self._buffer.file_name = self.props.file

        width, height = gtk.icon_size_lookup(self.props.icon_size)
        if self._buffer.width != width or self._buffer.height != height:
            self._buffer.width = width
            self._buffer.height = height

    def _icon_size_changed_cb(self, image, pspec):
        self._buffer.icon_size = self.props.icon_size

    def _icon_name_changed_cb(self, image, pspec):
        self._buffer.icon_name = self.props.icon_name

    def _file_changed_cb(self, image, pspec):
        self._buffer.file_name = self.props.file

    def _update_buffer_size(self):
        width, height = gtk.icon_size_lookup(self.props.icon_size)

        self._buffer.width = width
        self._buffer.height = height

    def do_size_request(self, requisition):
        self._sync_image_properties()
        surface = self._buffer.get_surface()
        if surface:
            requisition[0] = surface.get_width()
            requisition[1] = surface.get_height()
        elif self._buffer.width and self._buffer.height:
            requisition[0] = self._buffer.width
            requisition[1] = self._buffer.width
        else:
            requisition[0] = requisition[1] = 0

    def do_expose_event(self, event):
        self._sync_image_properties()
        surface = self._buffer.get_surface()
        if surface is None:
            return

        xpad, ypad = self.get_padding()
        xalign, yalign = self.get_alignment()
        requisition = self.get_child_requisition()
        if self.get_direction() != gtk.TEXT_DIR_LTR:
            xalign = 1.0 - xalign

        x = math.floor(self.allocation.x + xpad +
            (self.allocation.width - requisition[0]) * xalign)
        y = math.floor(self.allocation.y + ypad +
            (self.allocation.height - requisition[1]) * yalign)

        cr = self.window.cairo_create()
        cr.set_source_surface(surface, x, y)
        cr.paint()

    def do_set_property(self, pspec, value):
        if pspec.name == 'xo-color':
            if self._buffer.xo_color != value:
                self._buffer.xo_color = value
                self.queue_draw()
        elif pspec.name == 'fill-color':
            if self._buffer.fill_color != value:
                self._buffer.fill_color = value
                self.queue_draw()
        elif pspec.name == 'stroke-color':
            if self._buffer.stroke_color != value:
                self._buffer.stroke_color = value
                self.queue_draw()
        elif pspec.name == 'badge-name':
            if self._buffer.badge_name != value:
                self._buffer.badge_name = value
                self.queue_resize()
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

class CanvasIcon(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'CanvasIcon'

    __gproperties__ = {
        'file-name'     : (str, None, None, None,
                           gobject.PARAM_READWRITE),
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
        'scale'         : (float, None, None, -1024.0, 1024.0, 1.0,
                           gobject.PARAM_READWRITE),
        'cache'         : (bool, None, None, False,
                           gobject.PARAM_READWRITE),
        'badge-name'    : (str, None, None, None,
                           gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs):
        self._buffer = _IconBuffer()

        hippo.CanvasBox.__init__(self, **kwargs)

        self._palette = None

    def do_set_property(self, pspec, value):
        if pspec.name == 'file-name':
            if self._buffer.file_name != value:
                self._buffer.file_name = value
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'icon-name':
            if self._buffer.icon_name != value:
                self._buffer.icon_name = value
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'xo-color':
            if self._buffer.xo_color != value:
                self._buffer.xo_color = value
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'fill-color':
            if self._buffer.fill_color != value:
                self._buffer.fill_color = value
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'stroke-color':
            if self._buffer.stroke_color != value:
                self._buffer.stroke_color = value
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'size':
            if self._buffer.width != value:
                self._buffer.width = value
                self._buffer.height = value
                self.emit_request_changed()
        elif pspec.name == 'scale':
            logging.warning('CanvasIcon: the scale parameter is currently unsupported')
            if self._buffer.scale != value:
                self._buffer.scale = value
                self.emit_request_changed()
        elif pspec.name == 'cache':
            self._buffer.cache = value
        elif pspec.name == 'badge-name':
            if self._buffer.badge_name != value:
                self._buffer.badge_name = value
                self.emit_paint_needed(0, 0, -1, -1)

    def do_get_property(self, pspec):
        if pspec.name == 'size':
            return self._buffer.width
        elif pspec.name == 'file-name':
            return self._buffer.file_name
        elif pspec.name == 'icon-name':
            return self._buffer.icon_name
        elif pspec.name == 'fill-color':
            return self._buffer.fill_color
        elif pspec.name == 'stroke-color':
            return self._buffer.stroke_color
        elif pspec.name == 'cache':
            return self._buffer.cache
        elif pspec.name == 'badge-name':
            return self._buffer.badge_name
        elif pspec.name == 'scale':
            return self._buffer.scale

    def do_paint_below_children(self, cr, damaged_box):
        surface = self._buffer.get_surface()
        if surface:
            width, height = self.get_allocation()

            x = (width - surface.get_width()) / 2
            y = (height - surface.get_height()) / 2

            cr.set_source_surface(surface, x, y)
            cr.paint()

    def do_get_content_width_request(self):
        surface = self._buffer.get_surface()
        if surface:
            size = surface.get_width()
        elif self._buffer.width:
            size = self._buffer.width
        else:
            size = 0

        return size, size

    def do_get_content_height_request(self, for_width):
        surface = self._buffer.get_surface()
        if surface:
            size = surface.get_height()
        elif self._buffer.height:
            size = self._buffer.height
        else:
            size = 0

        return size, size

    def do_button_press_event(self, event):
        self.emit_activated()
        return True

    def get_palette(self):
        return self._palette
    
    def set_palette(self, palette):
        if self._palette is not None:        
            self._palette.props.invoker = None
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
                return icon_name

            strength = strength + step
