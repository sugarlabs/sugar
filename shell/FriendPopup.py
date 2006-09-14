import gtk
import goocanvas

from sugar.canvas.CanvasView import CanvasView
from sugar.canvas.CanvasBox import CanvasBox
from sugar.canvas.IconItem import IconItem

class FriendPopup(gtk.Window):
	def __init__(self, shell, grid, friend):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)

		self._shell = shell
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
		icon.connect('clicked', self._make_friend_clicked_cb)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-chat')
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-invite')
		icon.connect('clicked', self._invite_clicked_cb)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		root.add_child(box)

		canvas.set_model(model)

		self.connect('enter-notify-event', self._enter_notify_event_cb)
		self.connect('leave-notify-event', self._leave_notify_event_cb)

	def _invite_clicked_cb(self, icon):
		activity = self._shell.get_current_activity()
		buddy = self._friend.get_buddy()
		if buddy != None:
			activity.invite(buddy)
		else:
			print 'Friend not online'

	def _make_friend_clicked_cb(self, icon):
		pass

	def _enter_notify_event_cb(self, widget, event):
		self._hover = True

	def _leave_notify_event_cb(self, widget, event):
		self._hover = False
		if self._popdown_on_leave:
			self.popdown()

	def popdown(self):
		if not self._hover:
			self.destroy()
		else:
			self._popdown_on_leave = True

	def get_width(self):
		return self._width

	def get_height(self):
		return self._height
