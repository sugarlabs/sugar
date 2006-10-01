import goocanvas
import hippo

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.menuicon import MenuIcon
from sugar.graphics import style
from sugar.canvas.Menu import Menu
from sugar.canvas.IconItem import IconItem
from view.frame.MenuStrategy import MenuStrategy
import sugar

class ActivityMenu(Menu):
	ACTION_SHARE = 1
	ACTION_CLOSE = 2

	def __init__(self, grid, activity_host):
		title = activity_host.get_title()
		Menu.__init__(self, grid, title)

		icon = IconItem(icon_name='stock-share-mesh')
		self.add_action(icon, ActivityMenu.ACTION_SHARE) 

		icon = IconItem(icon_name='stock-close')
		self.add_action(icon, ActivityMenu.ACTION_CLOSE) 

class ActivityIcon(MenuIcon):
	def __init__(self, shell, menu_shell, activity_host):
		self._shell = shell
		self._activity_host = activity_host

		icon_name = activity_host.get_icon_name()
		icon_color = activity_host.get_icon_color()

		MenuIcon.__init__(self, menu_shell, icon_name=icon_name,
						  color=icon_color)

		self.set_menu_strategy(MenuStrategy())

	def create_menu(self):
		menu = ActivityMenu(self._shell.get_grid(), self._activity_host)
		menu.connect('action', self._action_cb)
		return menu

	def _action_cb(self, menu, action):
		self.popdown()

		activity = self._shell.get_current_activity()
		if activity == None:
			return

		if action == ActivityMenu.ACTION_SHARE:
			activity.share()
		if action == ActivityMenu.ACTION_CLOSE:
			activity.close()

class ZoomBox(hippo.CanvasBox):
	def __init__(self, shell, menu_shell):
		hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

		self._shell = shell
		self._menu_shell = menu_shell
		self._activity_icon = None

		icon = CanvasIcon(icon_name='stock-zoom-mesh')
		style.apply_stylesheet(icon, 'frame-zoom-icon')
		icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_MESH)
		self.append(icon, 0)

		icon = CanvasIcon(icon_name='stock-zoom-friends')
		style.apply_stylesheet(icon, 'frame-zoom-icon')
		icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_FRIENDS)
		self.append(icon, 0)

		icon = CanvasIcon(icon_name='stock-zoom-home')
		style.apply_stylesheet(icon, 'frame-zoom-icon')
		icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_HOME)
		self.append(icon, 0)

		icon = CanvasIcon(icon_name='stock-zoom-activity')
		style.apply_stylesheet(icon, 'frame-zoom-icon')
		icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_ACTIVITY)
		self.append(icon, 0)

		shell.connect('activity-changed', self._activity_changed_cb)
		self._set_current_activity(shell.get_current_activity())

	def _set_current_activity(self, activity):
		if self._activity_icon:
			self.remove(self._activity_icon)

		if activity:
			icon = ActivityIcon(self._shell, self._menu_shell, activity)
			style.apply_stylesheet(icon, 'frame-zoom-icon')
			self.append(icon, 0)
			self._activity_icon = icon
		else:
			self._activity_icon = None

	def _activity_changed_cb(self, shell_model, activity):
		self._set_current_activity(activity)

	def _level_clicked_cb(self, item, level):
		self._shell.set_zoom_level(level)
