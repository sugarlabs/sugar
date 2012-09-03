# Copyright (C) 2012, One Laptop Per Child
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
from gi.repository import GObject
from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import _IconBuffer
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettewindow import Invoker


class CursorInvoker(Invoker):

    def __init__(self, parent=None):
        Invoker.__init__(self)

        self._position_hint = self.AT_CURSOR
        self._enter_hid = None
        self._leave_hid = None
        self._release_hid = None
        self._item = None

        if parent:
            self.attach(parent)

    def attach(self, parent):
        Invoker.attach(self, parent)

        self._item = parent
        self._enter_hid = self._item.connect('enter-notify-event',
                                             self.__enter_notify_event_cb)
        self._leave_hid = self._item.connect('leave-notify-event',
                                             self.__leave_notify_event_cb)
        self._release_hid = self._item.connect('button-release-event',
                                               self.__button_release_event_cb)

    def detach(self):
        Invoker.detach(self)
        self._item.disconnect(self._enter_hid)
        self._item.disconnect(self._leave_hid)
        self._item.disconnect(self._release_hid)

    def get_default_position(self):
        return self.AT_CURSOR

    def get_rect(self):
        window = self._item.get_window()
        allocation = self._item.get_allocation()
        rect = ()
        rect.x, rect.y = window.get_root_coords(allocation.x, allocation.y)
        rect.width = allocation.width
        rect.height = allocation.height
        return rect

    def __enter_notify_event_cb(self, button, event):
        self.notify_mouse_enter()
        return False

    def __leave_notify_event_cb(self, button, event):
        self.notify_mouse_leave()
        return False

    def __button_release_event_cb(self, button, event):
        if event.button == 3:
            self.notify_right_click()
            return True
        else:
            return False

    def get_toplevel(self):
        return self._item.get_toplevel()


class EventIcon(Gtk.EventBox):

    __gtype_name__ = 'SugarEventIcon'

    def __init__(self, **kwargs):
        self._buffer = _IconBuffer()
        self._alpha = 1.0

        GObject.GObject.__init__(self)
        self.set_visible_window(False)
        for key, value in kwargs.iteritems():
            self.set_property(key, value)

        self._palette_invoker = CursorInvoker()
        self._palette_invoker.attach(self)

        self.connect('destroy', self.__destroy_cb)

    def do_expose_event(self, event):
        surface = self._buffer.get_surface()
        if surface:
            allocation = self.get_allocation()

            x = allocation.x + (allocation.width - surface.get_width()) / 2
            y = allocation.y + (allocation.height - surface.get_height()) / 2

            cr = self.window.cairo_create()
            cr.set_source_surface(surface, x, y)
            if self._alpha == 1.0:
                cr.paint()
            else:
                cr.paint_with_alpha(self._alpha)

    def do_size_request(self, req):
        surface = self._buffer.get_surface()
        if surface:
            req.width = surface.get_width()
            req.height = surface.get_height()
        elif self._buffer.width:
            req.width = self._buffer.width
            req.height = self._buffer.height
        else:
            req.width = 0
            req.height = 0

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def set_file_name(self, value):
        if self._buffer.file_name != value:
            self._buffer.file_name = value
            self.queue_draw()

    def get_file_name(self):
        return self._buffer.file_name

    file_name = GObject.property(
        type=object, getter=get_file_name, setter=set_file_name)

    def set_icon_name(self, value):
        if self._buffer.icon_name != value:
            self._buffer.icon_name = value
            self.queue_draw()

    def get_icon_name(self):
        return self._buffer.icon_name

    icon_name = GObject.property(
        type=object, getter=get_icon_name, setter=set_icon_name)

    def set_xo_color(self, value):
        if self._buffer.xo_color != value:
            self._buffer.xo_color = value
            self.queue_draw()

    xo_color = GObject.property(
        type=object, getter=None, setter=set_xo_color)

    def set_fill_color(self, value):
        if self._buffer.fill_color != value:
            self._buffer.fill_color = value
            self.queue_draw()

    def get_fill_color(self):
        return self._buffer.fill_color

    fill_color = GObject.property(
        type=object, getter=get_fill_color, setter=set_fill_color)

    def set_stroke_color(self, value):
        if self._buffer.stroke_color != value:
            self._buffer.stroke_color = value
            self.queue_draw()

    def get_stroke_color(self):
        return self._buffer.stroke_color

    stroke_color = GObject.property(
        type=object, getter=get_stroke_color, setter=set_stroke_color)

    def set_background_color(self, value):
        if self._buffer.background_color != value:
            self._buffer.background_color = value
            self.queue_draw()

    def get_background_color(self):
        return self._buffer.background_color

    background_color = GObject.property(
        type=object, getter=get_background_color, setter=set_background_color)

    def set_size(self, value):
        if self._buffer.width != value:
            self._buffer.width = value
            self._buffer.height = value
            self.queue_resize()

    def get_size(self):
        return self._buffer.width

    pixel_size = GObject.property(
        type=object, getter=get_size, setter=set_size)

    def set_scale(self, value):
        if self._buffer.scale != value:
            self._buffer.scale = value
            self.queue_resize()

    def get_scale(self):
        return self._buffer.scale

    scale = GObject.property(
        type=float, getter=get_scale, setter=set_scale)

    def set_alpha(self, alpha):
        if self._alpha != alpha:
            self._alpha = alpha
            self.queue_draw()

    alpha = GObject.property(
        type=float, setter=set_alpha)

    def set_cache(self, value):
        self._buffer.cache = value

    def get_cache(self):
        return self._buffer.cache

    cache = GObject.property(
        type=bool, default=False, getter=get_cache, setter=set_cache)

    def set_badge_name(self, value):
        if self._buffer.badge_name != value:
            self._buffer.badge_name = value
            self.queue_draw()

    def get_badge_name(self):
        return self._buffer.badge_name

    badge_name = GObject.property(
        type=object, getter=get_badge_name, setter=set_badge_name)

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_tooltip(self, text):
        self.set_palette(Palette(text))
