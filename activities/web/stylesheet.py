import gtk

_screen_factor = gtk.gdk.screen_width() / 1200.0

links_Bubble = {
	'box-width'   : int(250.0 * _screen_factor)
}

links_Text = {
	'color'  : 0x000000FF,
	'font'   : '14px',
	'padding' : 6
}

links_Box = {
	'background_color' : 0x646464ff,
	'padding'          : 4
}
