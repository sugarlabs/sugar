import gtk

from sugar.graphics.grid import Grid

settings = gtk.settings_get_default()

grid = Grid()
sizes = 'gtk-large-toolbar=%d, %d' % (grid.dimension(1), grid.dimension(1))
settings.set_string_property('gtk-icon-sizes', sizes, '')
