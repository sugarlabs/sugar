from gettext import gettext as _

import gtk

from sugar.activity import Activity

class NewActivityButton(gtk.MenuToolButton):
	def __init__(self, shell):
		gtk.MenuToolButton.__init__(self, None, _('New Activity'))

		self._shell = shell
		
		self.set_menu(gtk.Menu())
		self.connect("show-menu", self.__show_menu_cb)
	
	def __show_menu_cb(self, button):
		menu = gtk.Menu()
		
		for activity_info in self._shell.get_registry().list_activities():
			item = gtk.MenuItem(activity_info.get_title(), False)
			name = activity_info.get_name()
			item.connect('activate', self.__menu_item_activate_cb, name)
			menu.append(item)
			item.show()
		
		self.set_menu(menu)
		
	def __menu_item_activate_cb(self, item, name):
		Activity.create(name)

class Toolbar(gtk.Toolbar):
	def __init__(self, shell):
		gtk.Toolbar.__init__(self)
		
		new_activity_button = NewActivityButton(shell)
		self.insert(new_activity_button, -1)
		new_activity_button.show()

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		
		vbox = gtk.VBox()

		toolbar = Toolbar(shell)
		vbox.pack_start(toolbar, False)
		toolbar.show()
		
		self.add(vbox)
		vbox.show()
