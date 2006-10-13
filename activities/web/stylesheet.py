import gtk

_screen_factor = gtk.gdk.screen_width() / 1200.0

bubble_Box = {
	'box-width'   : int(150.0 * _screen_factor),
	'box-height'  : int(50.0 * _screen_factor)
}
