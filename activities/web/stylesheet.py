import gtk

_screen_factor = gtk.gdk.screen_width() / 1200.0

bubble_Bubble = {
	'box-width'   : int(250.0 * _screen_factor)
}

bubble_Text = {
	'color'  : 0x000000FF,
	'font'   : '14px',
	'padding' : 5
}
