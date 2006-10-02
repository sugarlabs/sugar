import gtk

from sugar.graphics import style
from sugar.canvas.IconColor import IconColor

if gtk.gdk.screen_width() == 1200:
	_medium_icon_size = 75
else:
	_medium_icon_size = 50

_stylesheet = {
	'color' : IconColor('white'),
	'size'  : _medium_icon_size
}
style.register_stylesheet('frame-activity-icon', _stylesheet)

_stylesheet = {
	'size'  : _medium_icon_size
}
style.register_stylesheet('frame-zoom-icon', _stylesheet)

_stylesheet = {
	'size'  : _medium_icon_size
}
style.register_stylesheet('menu-action-icon', _stylesheet)
