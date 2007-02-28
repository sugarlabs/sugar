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

""" Units conversions and constants

The purpose of the module is to keep Sugar independent from the
screen size, factory and DPI. There a few use cases that needs
to be considered:

  - The XO display. The screen DPI is 201 and the screen
    resolution is 1200x900. The screen factor is 4:3.
  - The Sugar emulator runned on traditional screens. Resolution
    is variable, ranging from 800x600 up to 1200x900. The DPI
    is usually but not necessarily 96. The screen factor is
    either 4:3 or 16:9
  - Other embedded devices. DPI, screen resolution and screen
    factor are variable.

To achieve the goal a few rules needs to be respected when
writing code for Sugar:

  - Never use absolute positioning. Use the layout facilities
    provided by HippoCanvas. If you need custom layouts make
    sure they adapt to different screen resolutions.
  - Never specify sizes, fonts, borders or padding using pixels.
    Instead use the device independt units provided by this
    module.

We are currently providing the following resolution independent
units:

  - Points.
  - Grid. One cell of the screen grid as specificed by the HIG.
  - Microgrid. One microcell of the screen grid as
    specificed by the HIG.
  - A set of icon sizes as specified by the HIG (standard, small,
    medium, large, xlarge).

Just scaling UI elements on the base of the screen DPI is not
enough to provide a good experience. For example on smaller
screens smaller fonts or icons might be acceptable to gain
screen aestate. For this reason a constant zoom factor is
applied to all the transformation from resolution independent
units to device units.

"""

import gtk

import _sugar

_MAX_ZOOM_FACTOR = 1.5
_ZOOM_CONSTANT   = 600.0

def _compute_zoom_factor():
    screen_width = gtk.gdk.screen_width()
    if _sugar.get_screen_dpi() == 201.0 and screen_width == 1200:
        return 1.0
    else:
        return min(_MAX_ZOOM_FACTOR, screen_width / _ZOOM_CONSTANT)

_screen_dpi = float(_sugar.get_screen_dpi())
_dpi_factor  = _screen_dpi / 201.0
_zoom_factor = _compute_zoom_factor()

STANDARD_ICON_SCALE = 1.0 * _dpi_factor * _zoom_factor
SMALL_ICON_SCALE    = 0.5 * _dpi_factor * _zoom_factor
MEDIUM_ICON_SCALE   = 1.5 * _dpi_factor * _zoom_factor
LARGE_ICON_SCALE    = 2.0 * _dpi_factor * _zoom_factor
XLARGE_ICON_SCALE   = 3.0 * _dpi_factor * _zoom_factor

def points_to_pixels(points):
    return int(points * _screen_dpi * 72.0 * _zoom_factor)

def grid_to_pixels(units):
    return int(units * 75.0 * _dpi_factor * _zoom_factor)

def microgrid_to_pixels(units):
    return int(units * 15.0 * _dpi_factor * _zoom_factor)
