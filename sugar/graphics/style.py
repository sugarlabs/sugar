# Copyright (C) 2007, Red Hat, Inc.
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

def _compute_zoom_factor():
    return gtk.gdk.screen_width() / 1200.0

def _zoom(units):
    return int(ZOOM_FACTOR * units)

def _compute_font_height(font):
    widget = gtk.Label('')

    context = widget.get_pango_context()
    font = context.load_font(font.get_pango_desc())
    metrics = font.get_metrics()
    
    return pango.PIXELS(metrics.get_ascent() + metrics.get_descent())

class Font(object):
    def __init__(self, desc):
        self._desc = desc

    def __str__(self):
        return self._desc

    def get_pango_desc(self):
        return pango.FontDescription(self._desc)

_FOCUS_LINE_WIDTH = 2

ZOOM_FACTOR = _compute_zoom_factor()

FONT_SIZE = _zoom(7 * 200 / 72.0)
FONT_NORMAL = Font('Bitstream Vera Sans %d' % FONT_SIZE)
FONT_BOLD = Font('Bitstream Vera Sans bold %d' % FONT_SIZE)

TOOLBOX_SEPARATOR_HEIGHT = _zoom(9)
TOOLBOX_HORIZONTAL_PADDING = _zoom(75)
TOOLBOX_TAB_VBORDER = int((_zoom(36) - FONT_SIZE - _FOCUS_LINE_WIDTH) / 2)
