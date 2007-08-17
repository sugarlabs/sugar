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
import gobject
import gtk
import re

from sugar.graphics.style import Color

class Icon(gtk.Image):
    __gtype_name__ = 'SugarIcon'

    __gproperties__ = {
        'xo-color'      : (object, None, None,
                           gobject.PARAM_WRITABLE),
        'fill-color'    : (object, None, None,
                           gobject.PARAM_READWRITE),
        'stroke-color'  : (object, None, None,
                           gobject.PARAM_READWRITE)
    }

    def __init__(self, name, **kwargs):
        self._constructed = False
        self._fill_color = None
        self._stroke_color = None
        self._icon_name = name
        self._theme = gtk.icon_theme_get_default()
        self._data = None

        gobject.GObject.__init__(self, **kwargs)

        self._constructed = True
        self._update_icon()

    def _get_pixbuf(self, data, width, height):
         loader = gtk.gdk.PixbufLoader('svg')
         loader.set_size(width, height)
         loader.write(data, len(data))
         loader.close()
         return loader.get_pixbuf()

    def _read_icon_data(self, icon_name):
        filename = self._get_real_name(icon_name)
        icon_file = open(filename, 'r')
        data = icon_file.read()
        icon_file.close()

        return data

    def _update_normal_icon(self):
        icon_theme = gtk.icon_theme_get_for_screen(self.get_screen())
        icon_set = gtk.IconSet()

        if icon_theme.has_icon(self._icon_name):
            source = gtk.IconSource()
            source.set_icon_name(self._icon_name)
            icon_set.add_source(source)

        inactive_name = self._icon_name + '-inactive'
        if icon_theme.has_icon(inactive_name):
            source = gtk.IconSource()
            source.set_icon_name(inactive_name)
            source.set_state(gtk.STATE_INSENSITIVE)
            icon_set.add_source(source)

        self.props.icon_set = icon_set

    def _update_icon(self):
        if not self._constructed:
            return

        if not self._fill_color and not self._stroke_color:
            self._update_normal_icon()
            return

        if not self._data:
            data = self._read_icon_data(self._icon_name)
        else:
            data = self._data
        
        if self._fill_color:
            entity = '<!ENTITY fill_color "%s">' % self._fill_color
            data = re.sub('<!ENTITY fill_color .*>', entity, data)

        if self._stroke_color:
            entity = '<!ENTITY stroke_color "%s">' % self._stroke_color
            data = re.sub('<!ENTITY stroke_color .*>', entity, data)

        self._data = data

        # Redraw pixbuf
        [w, h] = gtk.icon_size_lookup(self.props.icon_size)
        pixbuf = self._get_pixbuf(self._data, w, h)
        self.set_from_pixbuf(pixbuf)

    def _get_real_name(self, name):
        info = self._theme.lookup_icon(name, self.props.icon_size, 0)
        if not info:
            raise ValueError("Icon '" + name + "' not found.")
        fname = info.get_filename()
        del info
        return fname

    def do_set_property(self, pspec, value):
        if pspec.name == 'xo-color':
            self.props.fill_color = value.get_fill_color()
            self.props.stroke_color = value.get_stroke_color()
        elif pspec.name == 'fill-color':
            self._fill_color = value
            self._update_icon()
        elif pspec.name == 'stroke-color':
            self._stroke_color = value
            self._update_icon()
        else:
            gtk.Image.do_set_property(self, pspec, value)

        if pspec.name == 'icon-size':
            self._update_icon()

    def do_get_property(self, pspec):
        if pspec.name == 'fill-color':
            return self._fill_color
        elif pspec.name == 'stroke-color':
            return self._stroke_color
        else:
            return gtk.Image.do_get_property(self, pspec)
