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

import gtk
import gobject

class ColorButton(gtk.RadioButton):
    def __init__(self, group, rgb):
        gtk.RadioButton.__init__(self, group)
        
        self._rgb = rgb
        
        self.set_mode(False)
        self.set_relief(gtk.RELIEF_NONE)
        
        drawing_area = gtk.DrawingArea()
        drawing_area.set_size_request(24, 24)
        drawing_area.connect_after('expose_event', self.expose)
        self.add(drawing_area)
        drawing_area.show()

    def color(self):
        return self._rgb

    def expose(self, widget, event):
        rect = widget.get_allocation()
        ctx = widget.window.cairo_create()

        ctx.set_source_rgb(self._rgb[0], self._rgb[1] , self._rgb[2])
        ctx.rectangle(4, 4, rect.width - 8, rect.height - 8)
        ctx.fill()
        
        return False

class Toolbox(gtk.HBox):
    __gsignals__ = {
        'color-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gtk.HBox.__init__(self, False, 6)
    
        self._colors_group = None
        
        self._add_color([0, 0, 0])
        self._add_color([1, 0, 0])
        self._add_color([0, 1, 0])
        self._add_color([0, 0, 1])
                
    def _add_color(self, rgb):
        color = ColorButton(self._colors_group, rgb)
        color.unset_flags(gtk.CAN_FOCUS)
        color.connect('clicked', self.__color_clicked_cb, rgb)
        self.pack_start(color, False)

        if self._colors_group == None:
            self._colors_group = color

        color.show()

    def __color_clicked_cb(self, button, rgb):
        self.emit("color-selected", button.color())
