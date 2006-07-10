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
		
		for activity_info in self._home.list_activities():
			item = gtk.MenuItem(activity_info.get_title(), False)
			name = activity_info.get_name()
			item.connect('activate', self.__menu_item_activate_cb, name)
			menu.append(item)
			item.show()
		
		self.set_menu(menu)
		
	def __menu_item_activate_cb(self, item, name):
		self._home.create(name)

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
		self.update()

	def _add_all(self):		
		screen = wnck.screen_get_default()
		for window in screen.get_windows():
			if not window.is_skip_tasklist():
				self.add(window)
	
	def _remove_all(self):
		for child in self.get_children():
			self.remove(child)

	def add(self, window):
		button = gtk.Button(window.get_name())
		button.connect('clicked', self.__button_clicked_cb, window)
		self.pack_start(button, False)
		button.show()
	
	def update(self):
		self._remove_all()
		self._add_all()
	
	def __button_clicked_cb(self, button, window):
		self._home.activate(window)

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		
		self._shell = shell
		
		vbox = gtk.VBox()

		toolbar = Toolbar(self)
		vbox.pack_start(toolbar, False)
		toolbar.show()
		
		self._grid = ActivityGrid(self)
		vbox.pack_start(self._grid)
		self._grid.show()
		
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

	def show(self):
		self._grid.update()
		gtk.Window.show(self)
