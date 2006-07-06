import pygtk
pygtk.require('2.0')
import gtk
import pango
import cgi
import xml.sax.saxutils
import gobject
import socket

from google import google
from sugar.presence.PresenceService import PresenceService
from sugar.activity import Activity

from gettext import gettext as _

_BROWSER_ACTIVITY_TYPE = "_web_olpc._udp"

_COLUMN_TITLE = 0
_COLUMN_ADDRESS = 1
_COLUMN_SUBTITLE = 2
_COLUMN_SERVICE = 3

class SearchHelper(object):
	def __init__(self, activity_id):
		self.search_id = activity_id
		self.found = False

class SearchModel(gtk.ListStore):
	def __init__(self, activities_model, search_text):
		gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING,
				gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
		success = False

		for row in activities_model:
			title = row[_COLUMN_TITLE]
			address = row[_COLUMN_ADDRESS]
			if title.find(search_text) >= 0 or address.find(search_text) >= 0:
				self.append([ title, address, row[_COLUMN_SUBTITLE], row[_COLUMN_SERVICE] ])

		google.LICENSE_KEY = '1As9KaJQFHIJ1L0W5EZPl6vBOFvh/Vaf'
		try:
			data = google.doGoogleSearch(search_text)
			success = True
		except socket.gaierror, exc:
			if exc[0] == -3:	# Temporary failure in name resolution
				errdlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
					gtk.BUTTONS_OK, "There appears to be no network connection.")
				errdlg.connect("response", lambda d, e: d.destroy())
				errdlg.connect("close", lambda d, e: d.destroy())
				errdlg.show()

		if success == True:
			for result in data.results:
				title = result.title
				
				# FIXME what tags should we actually strip?
				title = title.replace('<b>', '') 
				title = title.replace('</b>', '')

				# FIXME I'm sure there is a better way to
				# unescape these.
				title = title.replace('&quot;', '"')
				title = title.replace('&amp;', '&')
				
				self.append([ title, result.URL, None, None ])

class ActivitiesModel(gtk.ListStore):
	def __init__(self):
		gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING,
				gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)

	def _filter_dupe_activities(self, model, path, it, user_data):
		"""Search the list of list rows for an existing service that
		has the activity ID we're looking for."""
		helper = user_data
		(service, ) = model.get(it, _COLUMN_SERVICE)
		if not service:
			return False
		if service.get_activity_id() == helper.search_id:
			helper.found = True
			return True
		return False
	
	def add_activity(self, buddy, service):
		# Web Activity check
		activity_id = service.get_activity_id()
		if activity_id is None:
			return
		# Don't show dupes
		helper = SearchHelper(activity_id)
		self.foreach(self._filter_dupe_activities, helper)
		if helper.found == True:
			return

		# Only accept browser activities for now
		if service.get_type() == _BROWSER_ACTIVITY_TYPE:
			escaped_title = service.get_one_property('Title')
			escaped_uri = service.get_one_property('URI')
			if escaped_title and escaped_uri:
				title = xml.sax.saxutils.unescape(escaped_title)
				address = xml.sax.saxutils.unescape(escaped_uri)
				subtitle = 'Shared by %s' % buddy.get_nick_name()
				self.append([ title, address, subtitle, service ])

class ActivitiesView(gtk.TreeView):
	def __init__(self, model):
		gtk.TreeView.__init__(self, model)

		self._owner = None
		
		self.set_headers_visible(False)
		
		theme = gtk.icon_theme_get_default()
		size = 48
		self._web_pixbuf = theme.load_icon('emblem-web', size, 0)
		self._share_pixbuf = theme.load_icon('emblem-people', size, 0)

		column = gtk.TreeViewColumn('')
		self.append_column(column)

		cell = gtk.CellRendererPixbuf()
		column.pack_start(cell, False)
		column.set_cell_data_func(cell, self._icon_cell_data_func)

		cell = gtk.CellRendererText()
		column.pack_start(cell)
		column.set_cell_data_func(cell, self._cell_data_func)
		
		self.connect('row-activated', self._row_activated_cb)
		
	def _icon_cell_data_func(self, column, cell, model, it):
		if model.get_value(it, _COLUMN_SERVICE) == None:
			cell.set_property('pixbuf', self._web_pixbuf)
		else:
			cell.set_property('pixbuf', self._share_pixbuf)
	
	def _cell_data_func(self, column, cell, model, it):
		title = model.get_value(it, _COLUMN_TITLE)
		subtitle = model.get_value(it, _COLUMN_SUBTITLE)
		if subtitle is None:
			subtitle = model.get_value(it, _COLUMN_ADDRESS)

		markup = '<big><b>' + cgi.escape(title) + '</b></big>' 
		markup += '\n' + cgi.escape(subtitle)
		
		cell.set_property('markup', markup)
		cell.set_property('ellipsize', pango.ELLIPSIZE_END)

	def set_owner(self, owner):
		self._owner = owner

	def _row_activated_cb(self, treeview, path, column):	
		model = self.get_model() 
		address = model.get_value(model.get_iter(path), _COLUMN_ADDRESS)
		service = model.get_value(model.get_iter(path), _COLUMN_SERVICE)

		Activity.create('com.redhat.Sugar.BrowserActivity', service, [ address ])
				
class StartPage(gtk.HBox):
	def __init__(self, ac_signal_object):
		gtk.HBox.__init__(self)

		self._ac_signal_object = ac_signal_object
		self._ac_signal_object.connect("local-activity-started",
				self._on_local_activity_started_cb)
		self._ac_signal_object.connect("local-activity-ended",
				self._on_local_activity_ended_cb)

		self._pservice = PresenceService.get_instance()
		self._pservice.connect("activity-announced", self._on_activity_announced_cb)
		self._pservice.connect("new-service-adv", self._on_new_service_adv_cb)
		self._pservice.connect("buddy-appeared", self._on_buddy_appeared_cb)
		self._pservice.connect("buddy-disappeared", self._on_buddy_disappeared_cb)
		self._pservice.start()
		self._pservice.track_service_type(_BROWSER_ACTIVITY_TYPE)
		if self._pservice.get_owner():
			self._on_buddy_appeared_cb(self._pservice, self._pservice.get_owner())

		vbox = gtk.VBox()

		search_box = gtk.HBox(False, 6)
		search_box.set_border_width(24)
		
		self._search_entry = gtk.Entry()
		self._search_entry.connect('activate', self._search_entry_activate_cb)
		search_box.pack_start(self._search_entry)
		self._search_entry.show()
		
		search_button = gtk.Button(_("Search"))
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

		vbox = gtk.VBox()

		self._search_close_box = gtk.HBox()
		
		self._search_close_label = gtk.Label()
		self._search_close_label.set_alignment(0.0, 0.5)
		self._search_close_box.pack_start(self._search_close_label)
		self._search_close_label.show()

		close_image = gtk.Image()
		close_image.set_from_stock (gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
		close_image.show()

		search_close_button = gtk.Button()
		rcstyle = gtk.RcStyle();
		rcstyle.xthickness = rcstyle.ythickness = 0;
		search_close_button.modify_style (rcstyle);
		search_close_button.add(close_image)
		search_close_button.set_relief(gtk.RELIEF_NONE)
		search_close_button.set_focus_on_click(False)
		search_close_button.connect("clicked", self.__search_close_button_clicked_cb)

		self._search_close_box.pack_start(search_close_button, False)
		search_close_button.show()
		
		vbox.pack_start(self._search_close_box, False)

		sw = gtk.ScrolledWindow()
		sw.set_size_request(320, -1)
		sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

		self._activities_model = ActivitiesModel()

		owner = self._pservice.get_owner()
		self._activities = ActivitiesView(self._activities_model)
		sw.add(self._activities)
		self._activities.show()

		vbox.pack_start(sw)
		sw.show()
		
		self.pack_start(vbox)
		vbox.show()
		
	def __search_close_button_clicked_cb(self, button):
		self._search(None)

	def _on_local_activity_started_cb(self, helper, activity_container, activity_id):
		print "new local activity %s" % activity_id

	def _on_local_activity_ended_cb(self, helper, activity_container, activity_id):
		print "local activity %s disappeared" % activity_id

	def _on_new_service_adv_cb(self, pservice, activity_id, short_stype):
		if activity_id:
			self._pservice.track_service_type(short_stype)

	def _on_buddy_appeared_cb(self, pservice, buddy):
		if buddy.is_owner():
			self._activities.set_owner(buddy)

	def _on_buddy_disappeared_cb(self, pservice, buddy):	
		if buddy.is_owner():
			self._activities.set_owner(None)

	def _on_activity_announced_cb(self, pservice, service, buddy):
		print "Found new activity service (activity %s of type %s)" % (service.get_activity_id(), service.get_type())
		self._activities_model.add_activity(buddy, service)
		if self._activities.get_model() != self._activities_model:
			self._search(self._last_search)

	def _search_entry_activate_cb(self, entry):
		self._search()
		self._search_entry.set_text('')
		
	def _search_button_clicked_cb(self, button):
		self._search()
		self._search_entry.set_text('')

	def _search(self, text = None):
		if text == None:
			text = self._search_entry.get_text()

		if text == None or len(text) == 0:
			self._activities.set_model(self._activities_model)
			self._search_close_box.hide()
		else:
			search_model = SearchModel(self._activities_model, text)
			self._activities.set_model(search_model)

			self._search_close_label.set_text('Search for %s' % (text))
			self._search_close_box.show()

		self._last_search = text
