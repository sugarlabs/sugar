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

import logging
import re

import gobject
import gtk
import hippo
import rsvg
import cairo
import time

from sugar.graphics.popup import Popup
from sugar.graphics import color
from sugar.graphics.xocolor import XoColor
from sugar.graphics import font
from sugar.graphics import units
from sugar.graphics import animator

class _PopupAnimation(animator.Animation):
    def __init__(self, icon):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._icon = icon

    def next_frame(self, current):
        if current == 1.0:
            self._icon.show_popup()

class _PopdownAnimation(animator.Animation):
    def __init__(self, icon):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._icon = icon

    def next_frame(self, current):
        if current == 1.0:
            self._icon.hide_popup()

class _IconCacheIcon:
    def __init__(self, name, fill_color, stroke_color, now):
        self.data_size = None
        self.handle = self._read_icon_data(name, fill_color, stroke_color)
        self.last_used = now
        self.usage_count = 1

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
        self._theme = gtk.icon_theme_get_default()
        self._cache_size = 0

    def _get_real_name_from_theme(self, name):
        info = self._theme.lookup_icon(name, 50, 0)
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

    def get_handle(self, name, fill_color, stroke_color):
        if name == None:
            return None

        if name[0:6] == "theme:": 
            name = self._get_real_name_from_theme(name[6:])

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
        return icon.handle


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
        'scale'         : (float, None, None,
                           0.0, 1024.0, units.STANDARD_ICON_SCALE,
                           gobject.PARAM_READWRITE),
        'cache'         : (bool, None, None, False,
                           gobject.PARAM_READWRITE),
        'tooltip'       : (str, None, None, None,
                           gobject.PARAM_READWRITE),
        'active'        : (bool, None, None, True,
                           gobject.PARAM_READWRITE)
    }

    _cache = _IconCache()

    def __init__(self, **kwargs):
        self._buffers = {}
        self._cur_buffer = None
        self._scale = units.STANDARD_ICON_SCALE
        self._fill_color = None
        self._stroke_color = None
        self._icon_name = None
        self._cache = False
        self._handle = None
        self._popup = None
        self._hover_icon = False
        self._hover_popup = False
        self._tooltip = False
        self._active = True
        self._popup_anim = None
        self._enter_or_leave_sid = 0
        
        hippo.CanvasBox.__init__(self, **kwargs)

        self.connect_after('motion-notify-event', self._motion_notify_event_cb)

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
            self._handle = None
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'xo-color':
            self.props.fill_color = color.HTMLColor(value.get_fill_color())
            self.props.stroke_color = color.HTMLColor(value.get_stroke_color())
        elif pspec.name == 'fill-color':
            if self._fill_color != value:
                if not self._cache:
                    self._clear_buffers()
                self._fill_color = value
                self._handle = None
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'stroke-color':
            if self._stroke_color != value:
                if not self._cache:
                    self._clear_buffers()
                self._stroke_color = value
                self._handle = None
                self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'scale':
            if self._scale != value and not self._cache:
                self._clear_buffers()
            self._scale = value
            self.emit_request_changed()
        elif pspec.name == 'cache':
            self._cache = value
        elif pspec.name == 'tooltip':
            self._tooltip = value
        elif pspec.name == 'active':
            if self._active != value:
                if not self._cache:
                    self._clear_buffers()
                self._active = value
                self._handle = None
                self.emit_paint_needed(0, 0, -1, -1)

    def _choose_colors(self):
        fill_color = None
        stroke_color = None
        if self._active:
            if self._fill_color:
                fill_color = self._fill_color.get_html()
            if self._stroke_color:
                stroke_color = self._stroke_color.get_html()
        else:
            stroke_color = color.ICON_STROKE_INACTIVE.get_html()
            if self._fill_color:
                fill_color = self._fill_color.get_html()
        return [fill_color, stroke_color]

    def _get_handle(self):
        if not self._handle:
            cache = CanvasIcon._cache

            [fill_color, stroke_color] = self._choose_colors()

            self._handle = cache.get_handle(self._icon_name, fill_color,
                                            stroke_color)
        return self._handle

    def _get_current_buffer_key(self):
        [fill_color, stroke_color] = self._choose_colors()
        return (self._icon_name, fill_color, stroke_color, self._scale)

    def do_get_property(self, pspec):
        if pspec.name == 'scale':
            return self._scale
        elif pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'fill-color':
            return self._fill_color
        elif pspec.name == 'stroke-color':
            return self._stroke_color
        elif pspec.name == 'cache':
            return self._cache
        elif pspec.name == 'tooltip':
            return self._tooltip
        elif pspec.name == 'active':
            return self._active

    def _get_icon_size(self):
        handle = self._get_handle()
        if handle:
            dimensions = handle.get_dimension_data()

            width  = int(dimensions[0] * self._scale) + 1
            height = int(dimensions[1] * self._scale) + 1

            return [width, height]

        return [0, 0]

    def _get_buffer(self, cr, handle):
        key = self._get_current_buffer_key()
        buf = None

        if self._buffers.has_key(key):
            buf = self._buffers[key]
        else:
            target = cr.get_target()

            [w, h] = self._get_icon_size()
            buf = target.create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)

            ctx = cairo.Context(buf)
            ctx.scale(self._scale, self._scale)
            handle.render_cairo(ctx)
            del ctx
            self._buffers[key] = buf

        return buf

    def do_paint_below_children(self, cr, damaged_box):
        handle = self._get_handle()
        if handle == None:
            return

        buf = self._get_buffer(cr, handle)

        [width, height] = self.get_allocation()
        [icon_width, icon_height] = self._get_icon_size()
        x = (width - icon_width) / 2
        y = (height - icon_height) / 2
        
        cr.set_source_surface(buf, x, y)
        cr.paint()

    def do_get_content_width_request(self):
        [width, height] = self._get_icon_size()
        return (width, width)

    def do_get_content_height_request(self, for_width):
        [width, height] = self._get_icon_size()
        return (height, height)

    def do_button_press_event(self, event):
        self.emit_activated()
        return True

    def get_popup(self):
        if self._tooltip:
            tooltip_popup = Popup()
            text = hippo.CanvasText(text=self._tooltip)
            text.props.background_color = color.MENU_BACKGROUND.get_int()
            text.props.color = color.LABEL_TEXT.get_int()
            text.props.font_desc = font.DEFAULT.get_pango_desc()
            text.props.padding = units.points_to_pixels(5)
            tooltip_popup.append(text)
            
            return tooltip_popup
        else:
            return None

    def get_popup_context(self):
        return None

    def show_popup(self):
        if not self._popup:
            self._popup = self.get_popup()
            if not self._popup:
                return

        popup_context = self.get_popup_context()
        
        [x, y] = [None, None]
        if popup_context:
            try:
                [x, y] = popup_context.get_position(self, self._popup)
            except NotImplementedError:
                pass

        if [x, y] == [None, None]:
            context = self.get_context()
            [x, y] = context.translate_to_screen(self)
        
            # TODO: Any better place to do this?
            [min_width, natural_width] = self.get_width_request()
            [pop_min_width, pop_natural_width] = self._popup.get_width_request()
            self._popup.props.box_width = max(pop_min_width, min_width)

            [width, height] = self.get_allocation()
            y += height
            position = [x, y]

        self._popup.popup(x, y)
        self._popup.connect('motion-notify-event',
                            self.popup_motion_notify_event_cb)
        self._popup.connect('action-completed',
                            self._popup_action_completed_cb)

        if popup_context:
            popup_context.popped_up(self._popup)

    def hide_popup(self):
        if self._popup:
            self._popup.popdown()

            popup_context = self.get_popup_context()
            if popup_context:
                popup_context.popped_down(self._popup)

            self._popup = None

    def _enter(self):
        self._popup_anim = animator.Animator(0.2, 10)
        self._popup_anim.add(_PopupAnimation(self))
        self._popup_anim.start()

        self.prelight(enter=True)

    def _leave(self):
        # FIXME: This is a hack for taking out the popdown delay for tooltips and
        # increasing the rest of rollovers. We need a better way for specifiying
        # different behaviors for the different kinds of popups.
        if type(self._popup) == Popup:
            self.hide_popup()
        else:
            self._popup_anim = animator.Animator(0.5, 10)
            self._popup_anim.add(_PopdownAnimation(self))
            self._popup_anim.start()

        self.prelight(enter=False)

    def _enter_or_leave_cb(self):
        if self._popup_anim:
            self._popup_anim.stop()

        if self._hover_icon or self._hover_popup:
            self._enter()
        else:
            self._leave()

        self._enter_or_leave_sid = 0

        return False

    def _schedule_enter_or_leave(self):
        if self._enter_or_leave_sid == 0:
            sid = gobject.idle_add(self._enter_or_leave_cb)
            self._enter_or_leave_sid = sid

    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self._hover_icon = True
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self._hover_icon = False

        self._schedule_enter_or_leave()

        return False

    def popup_motion_notify_event_cb(self, popup, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self._hover_popup = True
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self._hover_popup = False

        self._schedule_enter_or_leave()

        return False

    def _popup_action_completed_cb(self, popup):
        self.hide_popup()

    def prelight(self, enter):
        """
        Override this method for adding prelighting behavior.
        """
        pass

def get_icon_state(base_name, perc):
        step = 5
        strength = round(perc / step) * step
        icon_theme = gtk.icon_theme_get_default()

        while strength <= 100:
            icon_name = '%s-%03d' % (base_name, strength)
            if icon_theme.has_icon(icon_name):
                return 'theme:' + icon_name

            strength = strength + step
