# Copyright (C) 2006, Red Hat, Inc.
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

def _grab_pixbuf(window=None):
    if not window:
        screen = gtk.gdk.screen_get_default()
        window = screen.get_root_window()
    color_map = gtk.gdk.colormap_get_system()
    (x, y, w, h, bpp) = window.get_geometry()
    return gtk.gdk.pixbuf_get_from_drawable(None, window, color_map, x, y, 0, 0, w, h)

class OverlayWindow(gtk.Window):
    def __init__(self, lower_window):
        gtk.Window.__init__(self)
        self._lower_window = lower_window

        self._img = gtk.Image()
        self.add(self._img)

        self.realize()

        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(False)
        self.window.set_transient_for(lower_window)

        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.set_default_size(gtk.gdk.screen_width(), gtk.gdk.screen_height())
        self.set_app_paintable(True)

#        self.connect('expose-event', self._expose_cb)

    def appear(self):
        pbuf = _grab_pixbuf(self._lower_window)
        #pbuf.saturate_and_pixelate(pbuf, 0.5, False)
        w = pbuf.get_width()
        h = pbuf.get_height()
        pbuf2 = pbuf.composite_color_simple(w, h, gtk.gdk.INTERP_NEAREST, 100, 1024, 0, 0)
        self._img.set_from_pixbuf(pbuf2)
        self.show_all()

    def disappear(self):
        self._img.set_from_pixbuf(None)
        self.hide()

    def _expose_cb(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.4) # Transparent
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

