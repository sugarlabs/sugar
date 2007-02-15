import gtk

import _sugar

def points_to_pixels(points):
    screen_factor = gtk.gdk.screen_width() / 1200.0
    return points * _sugar.get_screen_dpi() / 72.0 * screen_factor

def grid_to_pixels(units):
    return units * gtk.gdk.screen_width() / 16

def microgrid_to_pixels(units):
    return units * gtk.gdk.screen_width() / 80
