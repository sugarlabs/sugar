import gtk
import goocanvas
import gobject

from sugar.canvas.CanvasView import CanvasView
from sugar.canvas.CanvasBox import CanvasBox
from sugar.canvas.IconItem import IconItem

class BuddyPopup(gtk.Window):
	ACTION_MAKE_FRIEND = 0
	ACTION_INVITE = 1
	ACTION_REMOVE_FRIEND = 2

	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST,
				   gobject.TYPE_NONE, ([int])),
	}

	def __init__(self, shell, buddy):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)

		self._buddy = buddy
		self._hover = False
		self._popdown_on_leave = False
		self._width = 13
		self._shell = shell
		self._buddy = buddy

		grid = shell.get_grid()

		canvas = CanvasView()
		self.add(canvas)
		canvas.show()

		model = goocanvas.CanvasModelSimple()
		root = model.get_root_item()

		color = self._buddy.get_color()
		rect = goocanvas.Rect(fill_color=color.get_fill_color(),
							  stroke_color=color.get_stroke_color(),
							  line_width=3)
		root.add_child(rect)

		text = goocanvas.Text(text=self._buddy.get_name(), font="Sans bold 18",
							  fill_color='black', anchor=gtk.ANCHOR_SW)
		grid.set_constraints(text, 1, 3, self._width, 2)
		root.add_child(text)

		self._height = 4

		owner = shell.get_model().get_owner()
		if buddy.get_name() != owner.get_name():
			self._add_actions(grid, root)

		grid.set_constraints(canvas, 0, 0, self._width, self._height)				
		grid.set_constraints(rect, 0, 0, self._width, self._height)

		canvas.set_model(model)

	def _add_actions(self, grid, root):
		separator = goocanvas.Path(data='M 15 0 L 185 0', line_width=3,
								   fill_color='black')
		grid.set_constraints(separator, 0, 4)
		root.add_child(separator)

		box = CanvasBox(grid, CanvasBox.HORIZONTAL, 1)
		grid.set_constraints(box, 0, 5)

		friends = self._shell.get_model().get_friends()
		if friends.has_buddy(self._buddy):
			icon = IconItem(icon_name='stock-remove-friend')
			icon.connect('clicked', self._action_clicked_cb,
						 BuddyPopup.ACTION_REMOVE_FRIEND)
		else:
			icon = IconItem(icon_name='stock-make-friend')
			icon.connect('clicked', self._action_clicked_cb,
						 BuddyPopup.ACTION_MAKE_FRIEND)
		
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-chat')
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-invite')
		icon.connect('clicked', self._action_clicked_cb,
					 BuddyPopup.ACTION_INVITE)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		root.add_child(box)

		self._height = 10

	def _action_clicked_cb(self, icon, action):
		self.emit('action', action)

	def get_width(self):
		return self._width

	def get_height(self):
		return self._height
