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

		self._root = hippo.CanvasBox()
		style.apply_stylesheet(self._root, 'menu')
		canvas.set_root(self._root)

		text = hippo.CanvasText(text=title)
		style.apply_stylesheet(text, 'menu.Title')
		self._root.append(text)

		if content_box:
			separator = self._create_separator()
			self._root.append(separator)
			self._root.append(content_box)

		self._action_box = None

	def _create_separator(self):
		separator = hippo.CanvasBox()
		style.apply_stylesheet(separator, 'menu.Separator')
		return separator

	def _create_action_box(self):
		separator = self._create_separator()
		self._root.append(separator)

		self._action_box = hippo.CanvasBox(
						orientation=hippo.ORIENTATION_HORIZONTAL)
		self._root.append(self._action_box)

	def add_action(self, icon, action_id):
		if not self._action_box:
			self._create_action_box()

		style.apply_stylesheet(icon, 'menu.ActionIcon')
		icon.connect('activated', self._action_clicked_cb, action_id)
		self._action_box.append(icon)

	def _action_clicked_cb(self, icon, action):
		self.emit('action', action)
