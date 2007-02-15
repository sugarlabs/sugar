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
import math

import gtk
import pango

import _sugar

_screen_factor = gtk.gdk.screen_width() / 1200.0
_dpi_factor = _sugar.get_screen_dpi() / 201.0
_default_font_size = math.ceil(9 / _dpi_factor * _screen_factor)
print _default_font_size

_system_colors = {
    'toolbar-background'            : '#414141',
    'frame-border'                  : '#D1D1D2',
    'entry-background-focused'      : '#FFFFFF',
    'entry-background-unfocused'    : '#414141',
    'entry-selection-focused'       : '#D1D1D2',
    'entry-selection-unfocused'     : '#00FF00',
    'entry-text-focused'            : '#000000',
    'entry-text-unfocused'          : '#FFFFFF',
    'entry-border'                  : '#D1D1D2',
    'label-text'                    : '#FFFFFF',
    'desktop-background'            : '#E2E2E3'
}

def _html_to_rgb(html_color):
    """ #RRGGBB -> (r, g, b) tuple (in float format) """

    html_color = html_color.strip()
    if html_color[0] == '#':
        html_color = html_color[1:]
    if len(html_color) != 6:
        raise ValueError, "input #%s is not in #RRGGBB format" % html_color

    r, g, b = html_color[:2], html_color[2:4], html_color[4:]
    r, g, b = [int(n, 16) for n in (r, g, b)]
    r, g, b = (r / 255.0, g / 255.0, b / 255.0)

    return (r, g, b)

def _rgba_to_int(r, g, b, a):
    color = int(a * 255) + (int(b * 255) << 8) + \
            (int(g * 255) << 16) + (int(r * 255) << 24)
    return color

class RGBColor(object):
    def __init__(self, r, g, b, a=1.0):
        self._r = r
        self._g = g
        self._b = b
        self._a = a

    def get_rgba(self):
        return (self._r, self._g, self._b, self._a)

    def get_int(self):
        return _rgba_to_int(self._r, self._g, self._b, self._a)

    def get_gdk_color(self):
        return gtk.gdk.Color(int(self._r * 65535), int(self._g * 65535),
                             int(self._b * 65535))

class SystemColor(RGBColor):
    def __init__(self, color_id):
        rgb = _html_to_rgb(_system_colors[color_id])
        RGBColor.__init__(self, *rgb)

class Color(object):
    RED                = RGBColor(1.0, 0.0, 0.0)
    GREEN              = RGBColor(0.0, 1.0, 0.0)
    BLUE               = RGBColor(0.0, 0.0, 1.0)
    WHITE              = RGBColor(1.0, 1.0, 1.0)
    BLACK              = RGBColor(0.0, 0.0, 0.0)

    TOOLBAR_BACKGROUND          = SystemColor('toolbar-background')
    FRAME_BORDER                = SystemColor('frame-border')
    ENTRY_BACKGROUND_FOCUSED    = SystemColor('entry-background-focused')
    ENTRY_BACKGROUND_UNFOCUSED  = SystemColor('entry-background-unfocused')
    ENTRY_SELECTION_FOCUSED     = SystemColor('entry-selection-focused')
    ENTRY_SELECTION_UNFOCUSED   = SystemColor('entry-selection-unfocused')
    ENTRY_TEXT_FOCUSED          = SystemColor('entry-text-focused')
    ENTRY_TEXT_UNFOCUSED        = SystemColor('entry-text-unfocused')
    ENTRY_BORDER                = SystemColor('entry-border')
    LABEL_TEXT                  = SystemColor('label-text')
    DESKTOP_BACKGROUND          = SystemColor('desktop-background')

_system_fonts = {
    'default' : 'Bitstream Vera Sans %d' % _default_font_size
}

class BaseFont(object):
    def __init__(self, desc):
        self._desc = desc

    def get_desc(self):
        return self._desc

    def get_pango_desc(self):
        return pango.FontDescription(self._desc)

class SystemFont(BaseFont):
    def __init__(self, font_id):
        BaseFont.__init__(self, _system_fonts[font_id])

class Font(object):
    DEFAULT = SystemFont('default')

### Deprecated: we should drop this once we removed stylesheets ###

_styles = {}

screen_factor = gtk.gdk.screen_width() / 1200.0

space_unit = 9 * screen_factor
separator_thickness = 3 * screen_factor

standard_icon_scale = 1.0 * screen_factor
small_icon_scale    = 0.5 * screen_factor
medium_icon_scale   = 1.5 * screen_factor
large_icon_scale    = 2.0 * screen_factor
xlarge_icon_scale   = 3.0 * screen_factor

default_font_size   = 9.0 * screen_factor

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
    else:
        logging.debug('Stylesheet %s not found.' % stylesheet_name)

def get_font_description(style, relative_size):
    base_size = 18 * screen_factor
    return '%s %dpx' % (style, int(base_size * relative_size))
