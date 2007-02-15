import gtk

import _sugar

def points_to_pixels(points):
    return points * _sugar.get_screen_dpi() / 72.0

def grid_to_pixels(units):
    return units * gtk.gdk.screen_width() / 16

def microgrid_to_pixels(units):
    return units * gtk.gdk.screen_width() / 80
