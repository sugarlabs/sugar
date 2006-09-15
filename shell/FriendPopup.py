import gtk
import goocanvas
import gobject

from sugar.canvas.CanvasView import CanvasView
from sugar.canvas.CanvasBox import CanvasBox
from sugar.canvas.IconItem import IconItem

class FriendPopup(gtk.Window):
	ACTION_MAKE_FRIEND = 0
	ACTION_INVITE = 0

	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST,
				   gobject.TYPE_NONE, ([int])),
	}

	def __init__(self, grid, friend):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)

		self._friend = friend
		self._hover = False
		self._popdown_on_leave = False
		self._width = 13
		self._height = 10

		canvas = CanvasView()
		self.add(canvas)
		canvas.show()

		grid.set_constraints(canvas, 0, 0, self._width, self._height)				

		model = goocanvas.CanvasModelSimple()
		root = model.get_root_item()

		color = friend.get_color()
		rect = goocanvas.Rect(fill_color=color.get_fill_color(),
							  stroke_color=color.get_stroke_color(),
							  line_width=3)
		grid.set_constraints(rect, 0, 0, self._width, self._height)
		root.add_child(rect)

		text = goocanvas.Text(text=friend.get_name(), font="Sans bold 18",
							  fill_color='black', anchor=gtk.ANCHOR_SW)
		grid.set_constraints(text, 1, 3, self._width, self._height)
		root.add_child(text)

		separator = goocanvas.Path(data='M 15 0 L 185 0', line_width=3,
								   fill_color='black')
		grid.set_constraints(separator, 0, 4)
		root.add_child(separator)

		box = CanvasBox(grid, CanvasBox.HORIZONTAL, 1)
		grid.set_constraints(box, 0, 5)

		icon = IconItem(icon_name='stock-make-friend')
		icon.connect('clicked', self._action_clicked_cb,
					 FriendPopup.ACTION_MAKE_FRIEND)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-chat')
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-invite')
		icon.connect('clicked', self._action_clicked_cb,
					 FriendPopup.ACTION_INVITE)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		root.add_child(box)

		canvas.set_model(model)

	def _action_clicked_cb(self, icon, action):
		self.emit('action', action)

	def get_width(self):
		return self._width

	def get_height(self):
		return self._height
