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

_styles = {}

_screen_factor = gtk.gdk.screen_width() / 1200.0

space_unit = 9 * _screen_factor
separator_thickness = 3 * _screen_factor

standard_icon_size = int(75.0 * _screen_factor)
small_icon_size = standard_icon_size * 0.5
medium_icon_size = standard_icon_size * 1.5
large_icon_size = standard_icon_size * 2.0
xlarge_icon_size = standard_icon_size * 3.0

def load_stylesheet(module):
    for objname in dir(module):
        if not objname.startswith('_'):
            obj = getattr(module, objname)    
            if isinstance(obj, dict):
                register_stylesheet(objname.replace('_', '.'), obj)

def register_stylesheet(name, style):
    _styles[name] = style

def apply_stylesheet(item, stylesheet_name):
    if _styles.has_key(stylesheet_name):
        style_sheet = _styles[stylesheet_name]
        for name in style_sheet.keys():
            item.set_property(name, style_sheet[name])

def get_font_description(style, relative_size):
    base_size = 18 * _screen_factor
    return '%s %dpx' % (style, int(base_size * relative_size))
