import gtk

from sugar.graphics.iconcolor import IconColor

_screen_factor = gtk.gdk.screen_width() / 1200.0

_standard_icon_size = int(75.0 * _screen_factor)
_small_icon_size = _standard_icon_size * 0.5
_medium_icon_size = _standard_icon_size * 1.5
_large_icon_size = _standard_icon_size * 2.0
_xlarge_icon_size = _standard_icon_size * 3.0

frame_ActivityIcon = {
	'color' : IconColor('white'),
	'size'  : _standard_icon_size
}

ring_ActivityIcon = {
	'size'  : _medium_icon_size
}

frame_ZoomIcon = {
	'size' : _standard_icon_size
}

menu_ActionIcon = {
	'size' : _standard_icon_size
}

home_MyIcon = {
	'size' : _xlarge_icon_size
}

friends_MyIcon = {
	'size' : _large_icon_size
}

friends_FriendIcon = {
	'size' : _large_icon_size
}

friends_ActivityIcon = {
	'size' : _standard_icon_size
}
