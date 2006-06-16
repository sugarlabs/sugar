import pygtk
pygtk.require('2.0')
import gtk
import pango
import dbus
import cgi
import urllib
import re

import google
from sugar.presence.PresenceService import PresenceService
from sugar.presence import Service
from sugar.browser import BrowserActivity

class ActivitiesModel(gtk.ListStore):
	def __init__(self):
		gtk.ListStore.__init__(self, str, str, str, str)

	def add_web_page(self, title, address):
		self.append([ title, address, None, None ])
	
	def add_activity(self, buddy, service):
		(uid, stype) = service.get_activity_uid()
		title = urllib.unquote(service.get_one_property('Title'))
		address = urllib.unquote(service.get_one_property('URI'))
		subtitle = 'Shared by %s' % buddy.get_nick_name()
		self.append([ title, address, subtitle, uid ])

class ActivitiesView(gtk.TreeView):
	def __init__(self):
		gtk.TreeView.__init__(self, model = ActivitiesModel())
		
		self.set_headers_visible(False)
		
		column = gtk.TreeViewColumn('')
		self.append_column(column)

		cell = gtk.CellRendererText()
		column.pack_start(cell, True)
		column.set_cell_data_func(cell, self._cell_data_func)
		
		self.connect('row-activated', self._row_activated_cb)
	
	def _cell_data_func(self, column, cell, model, it):
		title = model.get_value(it, 0)
		subtitle = model.get_value(it, 2)
		if subtitle is None:
			subtitle = model.get_value(it, 1)
				
		markup = '<big><b>' + cgi.escape(title) + '</b></big>' 
		markup += '\n' + cgi.escape(subtitle)
		
		cell.set_property('markup', markup)
		cell.set_property('ellipsize', pango.ELLIPSIZE_END)
			
	def _row_activated_cb(self, treeview, path, column):	
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Browser', '/com/redhat/Sugar/Browser')
		browser_shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.BrowserShell')

		model = self.get_model() 
		address = model.get_value(model.get_iter(path), 1)
		activity_id = model.get_value(model.get_iter(path), 3)

		print 'Activated row %s %s' % (address, activity_id)

		if activity_id is None:
			browser_shell.open_browser(address, ignore_reply=True)
		else:
			browser_shell.open_browser_with_id(address, activity_id, ignore_reply=True)
			
class StartPage(gtk.HBox):
	def __init__(self):
		gtk.HBox.__init__(self)

		self._pservice = PresenceService.get_instance()
		self._pservice.connect("activity-announced", self._on_activity_announced_cb)
		self._pservice.connect("new-service-adv", self._on_new_service_adv_cb)
		self._pservice.start()
		self._pservice.track_service_type(BrowserActivity._BROWSER_ACTIVITY_TYPE)

		vbox = gtk.VBox()

		search_box = gtk.HBox(False, 6)
		search_box.set_border_width(24)
		
		self._search_entry = gtk.Entry()
		self._search_entry.connect('activate', self._search_entry_activate_cb)
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

		sw = gtk.ScrolledWindow()
		sw.set_size_request(320, -1)
		sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

		self._activities = ActivitiesView()
		sw.add(self._activities)
		self._activities.show()

		self.pack_start(sw)	
		sw.show()

	def _on_new_service_adv_cb(self, pservice, uid, stype):
		if uid is not None:
			real_stype = Service.compose_service_type(stype, uid)
			print "Will ask to track uid=%s, stype=%s" % (uid, stype)
			self._pservice.track_service_type(real_stype)

	def _on_activity_announced_cb(self, pservice, service, buddy):
		self._activities.get_model().add_activity(buddy, service)

	def _search_entry_activate_cb(self, entry):
		self._search()
		
	def _search_button_clicked_cb(self, button):
		self._search()
	
	def _search(self):
		text = self._search_entry.get_text()
		self._search_entry.set_text('')
	
		google.LICENSE_KEY = '1As9KaJQFHIJ1L0W5EZPl6vBOFvh/Vaf'
		data = google.doGoogleSearch(text)
		
		model = ActivitiesModel()
		for result in data.results:
			title = result.title
			
			# FIXME what tags should we actually strip?
			title = title.replace('<b>', '') 
			title = title.replace('</b>', '')

			# FIXME I'm sure there is a better way to
			# unescape these.
			title = title.replace('&quot;', '"')
			title = title.replace('&amp;', '&')

			model.add_web_page(title, result.URL)
		self._activities.set_model(model)
