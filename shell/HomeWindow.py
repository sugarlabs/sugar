from gettext import gettext as _

import gtk
import wnck

from sugar.activity import Activity

class NewActivityButton(gtk.MenuToolButton):
	def __init__(self, home):
		gtk.MenuToolButton.__init__(self, None, _('New Activity'))

		self._home = home
		
		self.set_menu(gtk.Menu())
		self.connect("show-menu", self.__show_menu_cb)
	
	def __show_menu_cb(self, button):
		menu = gtk.Menu()
		
		for module in self._home.list_activities():
			item = gtk.MenuItem(module.get_name(), False)
			activity_id = module.get_id()
			item.connect('activate', self.__menu_item_activate_cb, activity_id)
			menu.append(item)
			item.show()
		
		self.set_menu(menu)
		
	def __menu_item_activate_cb(self, item, activity_id):
		self._home.create(activity_id)

class Toolbar(gtk.Toolbar):
	def __init__(self, shell):
		gtk.Toolbar.__init__(self)
		
		new_activity_button = NewActivityButton(shell)
		self.insert(new_activity_button, -1)
		new_activity_button.show()

class ActivityGrid(gtk.VBox):
	def __init__(self, home):
		gtk.VBox.__init__(self)
		
		self._home = home
		self._buttons = {}

		screen = wnck.screen_get_default()
		for window in screen.get_windows():
			if not window.is_skip_tasklist():
				self._add(window)
		screen.connect('window_opened', self.__window_opened_cb)
		screen.connect('window_closed', self.__window_closed_cb)

	def __window_opened_cb(self, screen, window):
		if not window.is_skip_tasklist():
			self._add(window)

	def __window_closed_cb(self, screen, window):
		if not window.is_skip_tasklist():
			self._remove(window)
	
	def _remove(self, window):
		button = self._buttons[window.get_xid()]
		self.remove(button)

	def _add(self, window):
		button = gtk.Button(window.get_name())
		button.connect('clicked', self.__button_clicked_cb, window)
		self.pack_start(button, False)
		button.show()

		self._buttons[window.get_xid()] = button
	
	def __button_clicked_cb(self, button, window):
		self._home.activate(window)

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		
		self._shell = shell

		self.set_skip_taskbar_hint(True)
				
		vbox = gtk.VBox(False, 6)
		vbox.set_border_width(24)

		toolbar = Toolbar(self)
		vbox.pack_start(toolbar, False)
		toolbar.show()

		label = gtk.Label('Open activities:')
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()
		
		self._grid = ActivityGrid(self)
		vbox.pack_start(self._grid)
		self._grid.show()

		label = gtk.Label('Shared activities:')
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()

		self.add(vbox)
		vbox.show()

	def list_activities(self):
		return self._shell.get_registry().list_activities()

	def create(self, activity_name):
		Activity.create(activity_name)
		self.hide()

	def activate(self, activity_window):
		activity_window.activate(gtk.get_current_event_time())
		self.hide()
