import gtk

from sugar.graphics.iconcolor import IconColor

if gtk.gdk.screen_width() == 1200:
	_medium_icon_size = 75
else:
	_medium_icon_size = 50

frame_ActivityIcon = {
	'color' : IconColor('white'),
	'size'  : _medium_icon_size
}

frame_ZoomIcon = {
	'size'  : _medium_icon_size
}

menu_ActionIcon = {
	'size'  : _medium_icon_size
}
