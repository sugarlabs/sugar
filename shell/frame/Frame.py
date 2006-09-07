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
from sugar.canvas.GridModel import GridModel

class Frame:
	def __init__(self, shell, owner):
		self._windows = []

		self._model = GridModel("#4f4f4f")
		layout = self._model.get_layout()

		self._screen_layout = GridLayout()
		self._screen_container = ScreenContainer(self._windows)

		constraints = GridConstraints(0, 0, 16, 1)
		self._create_window(constraints)

		panel = TopPanel(shell)
		layout.set_constraints(panel, constraints)
		self._model.add(panel)

		constraints = GridConstraints(15, 1, 1, 10)
		self._create_window(constraints)

		panel = RightPanel(shell, owner.get_friends())
		layout.set_constraints(panel, constraints)
		self._model.add(panel)

		constraints = GridConstraints(0, 11, 16, 1)
		self._create_window(constraints)

		panel = BottomPanel(shell, owner.get_invites())
		layout.set_constraints(panel, constraints)
		self._model.add(panel)

		# Left
		constraints = GridConstraints(0, 1, 1, 10)
		self._create_window(constraints)

		self._screen_container.set_layout(self._screen_layout)

	def _create_window(self, constraints):
		window = PanelWindow(self._model)
		self._screen_layout.set_constraints(window, constraints)
		self._windows.append(window)

		bounds = self._model.get_layout().get_bounds(self._model._root, constraints)
		window.scale_to_screen()
		window.set_bounds(constraints)

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
