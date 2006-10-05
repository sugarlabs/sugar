import gtk
import hippo
import gobject

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import style

class Menu(gtk.Window):
	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST,
				   gobject.TYPE_NONE, ([int])),
	}

	def __init__(self, title, content_box=None):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)

		canvas = hippo.Canvas()
		self.add(canvas)
		canvas.show()

		self._root = hippo.CanvasBox(background_color=0x000000FF,
									 spacing=6)
		canvas.set_root(self._root)

		text = hippo.CanvasText(text=title, color=0xFFFFFFFF)
		self._root.append(text)

		if content_box:
			separator = self._create_separator()
			self._root.append(separator)
			self._root.append(content_box)

		separator = self._create_separator()
		self._root.append(separator)

		self._action_box = hippo.CanvasBox(
						orientation=hippo.ORIENTATION_HORIZONTAL)
		self._root.append(self._action_box)

	def _create_separator(self):
		separator = hippo.CanvasBox(background_color=0xFFFFFFFF,
									border_left=6, border_right=6,
								    box_height=2)
		return separator

	def add_action(self, icon, action_id):
		style.apply_stylesheet(icon, 'menu.ActionIcon')
		icon.connect('activated', self._action_clicked_cb, action_id)
		self._action_box.append(icon)

	def _action_clicked_cb(self, icon, action):
		self.emit('action', action)
