import gtk

import _sugar

_screen_factor = gtk.gdk.screen_width() / 1200.0

STANDARD_ICON_SCALE = 1.0 * _screen_factor
SMALL_ICON_SCALE    = 0.5 * _screen_factor
MEDIUM_ICON_SCALE   = 1.5 * _screen_factor
LARGE_ICON_SCALE    = 2.0 * _screen_factor
XLARGE_ICON_SCALE   = 3.0 * _screen_factor

def points_to_pixels(points):
    return points * _sugar.get_screen_dpi() / 72.0 * _screen_factor

def grid_to_pixels(units):
    return units * gtk.gdk.screen_width() / 16

def microgrid_to_pixels(units):
    return units * gtk.gdk.screen_width() / 80
