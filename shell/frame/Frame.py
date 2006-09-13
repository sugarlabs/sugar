import gtk
import gobject
import goocanvas

from frame.BottomPanel import BottomPanel
from frame.RightPanel import RightPanel
from frame.TopPanel import TopPanel
from frame.PanelWindow import PanelWindow
from sugar.canvas.Grid import Grid

class Frame:
	def __init__(self, shell, owner):
		self._windows = []

		model = goocanvas.CanvasModelSimple()
		root = model.get_root_item()

		grid = Grid()

		bg = goocanvas.Rect(fill_color="#4f4f4f")
		grid.set_constraints(bg, 0, 0, 80, 60)
		root.add_child(bg)

		panel = BottomPanel(grid, shell, owner.get_invites())
		grid.set_constraints(panel, 5, 55)
		root.add_child(panel)

		panel_window = PanelWindow(grid, model, 0, 55, 80, 5)
		self._windows.append(panel_window)

		panel = TopPanel(grid, shell)
		root.add_child(panel)

		panel_window = PanelWindow(grid, model, 0, 0, 80, 5)
		self._windows.append(panel_window)
		
		panel = RightPanel(grid, shell, owner.get_friends())
		grid.set_constraints(panel, 75, 5)
		root.add_child(panel)

		panel_window = PanelWindow(grid, model, 75, 5, 5, 50)
		self._windows.append(panel_window)

		panel_window = PanelWindow(grid, model, 0, 5, 5, 50)
		self._windows.append(panel_window)

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
