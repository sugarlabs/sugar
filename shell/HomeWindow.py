from gettext import gettext as _

import gtk
import wnck

from sugar.activity import ActivityFactory
from ActivitiesModel import ActivitiesModel
from sugar.presence.PresenceService import PresenceService

class NewActivityButton(gtk.MenuToolButton):
	def __init__(self, home):
		gtk.MenuToolButton.__init__(self, None, _('New Activity'))

		self._home = home
		
		self.set_menu(gtk.Menu())
		self.connect("show-menu", self.__show_menu_cb)
	
	def __show_menu_cb(self, button):
		menu = gtk.Menu()
		
		for module in self._home.list_activities():
			if module.get_show_launcher():
				item = gtk.MenuItem(module.get_name(), False)
				activity_id = module.get_id()
				item.connect('activate',
							 self.__menu_item_activate_cb, activity_id)
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

class ActivitiesGrid(gtk.VBox):
	def __init__(self, shell, model):
		gtk.VBox.__init__(self, shell)
		
		self._shell = shell
		self._buttons = {}

		for activity in model:
			self._add(activity)
		model.connect('activity-added', self.__activity_added_cb)
		model.connect('activity-removed', self.__activity_removed_cb)

	def __activity_added_cb(self, model, activity):
		self._add(activity)

	def __activity_removed_cb(self, model, activity):
		self._remove(window)
	
	def _remove(self, activity):
		button = self._buttons[activity.get_id()]
		self.remove(button)

	def _add(self, activity):
		button = gtk.Button(activity.get_title())
		button.connect('clicked', self.__button_clicked_cb, activity)
		self.pack_start(button, False)
		button.show()

		self._buttons[activity.get_id()] = button
	
	def __button_clicked_cb(self, button, info):
		activity = self._shell.get_registry().get_activity(info.get_type())
		
		activity_id = info.get_service().get_activity_id()
		pservice = PresenceService()
		activity_ps = pservice.get_activity(activity_id)

		if activity_ps:
			ActivityFactory.create(activity.get_id(), activity_ps)
		else:
			print 'Cannot start activity.'

class TasksGrid(gtk.VBox):
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

	def __window_name_changed_cb(self, window, button):
		button.set_label(window.get_name())

	def _add(self, window):
		button = gtk.Button(window.get_name())
		window.connect('name-changed', self.__window_name_changed_cb, button)
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

		self.connect('realize', self.__realize_cb)
				
		vbox = gtk.VBox(False, 6)
		vbox.set_border_width(24)

		toolbar = Toolbar(self)
		vbox.pack_start(toolbar, False)
		toolbar.show()

		label = gtk.Label('Open activities:')
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()
		
		grid = TasksGrid(self)
		vbox.pack_start(grid)
		grid.show()

		label = gtk.Label('Shared activities:')
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()

		model = ActivitiesModel(shell.get_registry())
		grid = ActivitiesGrid(shell, model)
		vbox.pack_start(grid)
		grid.show()

		self.add(vbox)
		vbox.show()

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

	def list_activities(self):
		return self._shell.get_registry().list_activities()

	def create(self, activity_name):
		ActivityFactory.create(activity_name)

	def activate(self, activity_window):
		activity_window.activate(gtk.get_current_event_time())
