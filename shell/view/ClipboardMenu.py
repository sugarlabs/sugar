import gtk
import gobject
import hippo

from sugar.graphics.menu import Menu
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.ClipboardBubble import ClipboardBubble
from sugar.graphics import style

clipboard_bubble = {
	'fill-color'	: 0x646464FF,
	'stroke-color'	: 0x646464FF,
	'progress-color': 0x333333FF,
	'spacing'		: style.space_unit,
	'padding'		: style.space_unit * 1.5
}

clipboard_menu_item_title = {
	'xalign': hippo.ALIGNMENT_START,
	'padding-left': 5,
	'color'	 : 0xFFFFFFFF,
	'font'	 : style.get_font_description('Bold', 1.2)
}

style.register_stylesheet("clipboard.Bubble", clipboard_bubble)
style.register_stylesheet("clipboard.MenuItem.Title", clipboard_menu_item_title)

class ClipboardMenuItem(ClipboardBubble):

	def __init__(self, percent = 0, stylesheet="clipboard.Bubble"):
		ClipboardBubble.__init__(self, percent = percent)
		style.apply_stylesheet(self, stylesheet)

class ClipboardMenu(Menu):

	ACTION_DELETE = 0
	ACTION_SHARE = 1
	ACTION_STOP_DOWNLOAD = 2
	
	def __init__(self, file_name, percent):
		Menu.__init__(self, file_name)
		
		self._progress_bar = ClipboardMenuItem(percent)
		self._root.append(self._progress_bar)
				
		icon = CanvasIcon(icon_name='stock-share-mesh')
		self.add_action(icon, ClipboardMenu.ACTION_SHARE)
		
		if percent == 100:
			icon = CanvasIcon(icon_name='stock-remove')
			self.add_action(icon, ClipboardMenu.ACTION_DELETE)
		else:
			icon = CanvasIcon(icon_name='stock-close')
			self.add_action(icon, ClipboardMenu.ACTION_STOP_DOWNLOAD)

	def set_percent(self, percent):
		self._progress_bar.set_property('percent', percent)
		
