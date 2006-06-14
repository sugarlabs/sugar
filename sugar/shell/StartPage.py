import pygtk
pygtk.require('2.0')
import gtk
import dbus

import google

class ActivitiesModel(gtk.ListStore):
	def __init__(self):
		gtk.ListStore.__init__(self, str, str)

	def add_web_page(self, title, address):
		self.append([ title, address ])

class ActivitiesView(gtk.TreeView):
	def __init__(self, model):
		gtk.TreeView.__init__(self, model)
		
		self.set_headers_visible(False)
		
		column = gtk.TreeViewColumn('')
		self.append_column(column)

		cell = gtk.CellRendererText()
		column.pack_start(cell, True)
		column.add_attribute(cell, 'text', 0)
		
		self.connect('row-activated', self._row_activated_cb)
	
	def _row_activated_cb(self, treeview, path, column):
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Browser', '/com/redhat/Sugar/Browser')
		browser_shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.BrowserShell')

		model = self.get_model() 
		address = model.get_value(model.get_iter(path), 1)
		browser_shell.open_browser(address, ignore_reply=True)

class StartPage(gtk.HBox):
	def __init__(self):
		gtk.HBox.__init__(self)

		vbox = gtk.VBox()

		search_box = gtk.HBox(False, 6)
		search_box.set_border_width(24)
		
		self._search_entry = gtk.Entry()
		search_box.pack_start(self._search_entry)
		self._search_entry.show()
		
		search_button = gtk.Button("Search")
		search_button.connect('clicked', self._search_button_clicked_cb)
		search_box.pack_start(search_button, False)
		search_button.show()

		vbox.pack_start(search_box, False, True)
		search_box.show()

		exp_space = gtk.Label('')
		vbox.pack_start(exp_space)
		exp_space.show()
				
		self.pack_start(vbox)
		vbox.show()

		self._activities_model = ActivitiesModel()

		activities = ActivitiesView(self._activities_model)
		self.pack_start(activities)
		activities.show()
		
	def _search_button_clicked_cb(self, button):
		self.search(self._search_entry.get_text())
	
	def search(self, text):
		google.LICENSE_KEY = '1As9KaJQFHIJ1L0W5EZPl6vBOFvh/Vaf'
		data = google.doGoogleSearch(text)
		for result in data.results:
			self._activities_model.add_web_page(result.title, result.URL)
