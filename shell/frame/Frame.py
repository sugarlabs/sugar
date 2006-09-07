import gtk
import gobject
import goocanvas

from frame.BottomPanel import BottomPanel
from frame.RightPanel import RightPanel
from frame.TopPanel import TopPanel
from frame.PanelWindow import PanelWindow

from sugar.canvas.ScreenContainer import ScreenContainer
from sugar.canvas.GridLayout import GridLayout
from sugar.canvas.GridLayout import GridConstraints
from sugar.canvas.GridLayout import GridGroup

class Frame:
	def __init__(self, shell, owner):
		self._windows = []

		self._model = goocanvas.CanvasModelSimple()
		item = goocanvas.Rect(x=0, y=0, width=800, height=600,
							  line_width=0, fill_color="#4f4f4f")
		self._model.get_root_item().add_child(item)

		self._screen_layout = GridLayout()
		self._screen_container = ScreenContainer(self._windows)

		group = GridGroup()
		group.props.width = 800
		group.props.height = 600
		layout = group.get_layout()

		constraints = GridConstraints(0, 11, 16, 1)
		self._create_window(constraints)

		panel = BottomPanel(shell, owner.get_invites())
		layout.set_constraints(panel, constraints)
		group.add_child(panel)

		# Top
		constraints = GridConstraints(0, 0, 16, 1)
		self._create_window(constraints)

		# Left
		constraints = GridConstraints(0, 1, 1, 10)
		self._create_window(constraints)

		# Right
		constraints = GridConstraints(15, 1, 1, 10)
		self._create_window(constraints)

		self._model.get_root_item().add_child(group)
		self._screen_container.set_layout(self._screen_layout)

	def _create_window(self, constraints):
		layout = self._screen_layout

		window = PanelWindow(self._model)
		layout.set_constraints(window, constraints)
		self._windows.append(window)

		bounds = layout.get_bounds(self._screen_container, constraints)
		window.get_view().set_bounds(bounds[0], bounds[1],
									 bounds[2], bounds[3])

	def __hide_timeout_cb(self):
		self.hide()
		return False

	def show_and_hide(self, seconds):
		self.show()
		gobject.timeout_add(seconds * 1000, self.__hide_timeout_cb)

	def show(self):
		for panel in self._windows:
			panel.show()

	def hide(self):
		for panel in self._windows:
			panel.hide()

	def toggle_visibility(self):
		for panel in self._windows:
			if panel.props.visible:
				panel.hide()
			else:
				panel.show()
