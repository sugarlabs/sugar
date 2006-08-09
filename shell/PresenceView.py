import gtk
import gobject
import dbus

from sugar.presence.PresenceService import PresenceService
from sugar.presence.Service import Service
from sugar.chat.BuddyChat import BuddyChat

from gettext import gettext as _

class PresenceView(gtk.VBox):
	_MODEL_COL_NICK = 0
	_MODEL_COL_ICON = 1
	_MODEL_COL_BUDDY = 2
		
	def __init__(self, shell, activity):
		gtk.VBox.__init__(self, False, 6)
		
		self._activity = activity
		self._activity_ps = None
		self._shell = shell

		self._pservice = PresenceService()
		self._pservice.connect("activity-appeared", self._activity_appeared_cb)
		
		self._setup_ui()

		activity_ps = self._pservice.get_activity(activity.get_id())
		if activity_ps:
			self._set_activity_ps(activity_ps)

		if activity:
			if self._activity.get_shared():
				self._share_button.set_sensitive(False)
			else:
				self._share_button.set_sensitive(True)
		else:
			self._share_button.set_sensitive(False)

	def _set_activity_ps(self, activity_ps):
		self._activity_ps = activity_ps
		self._activity_ps.connect('buddy-joined', self._buddy_joined_cb)
		self._activity_ps.connect('buddy-left', self._buddy_left_cb)
		for buddy in activity_ps.get_joined_buddies():
			self._add_buddy(buddy)

	def _setup_ui(self):
		self.set_size_request(120, -1)

		label = gtk.Label(_("Who's around:"))
		label.set_alignment(0.0, 0.5)
		self.pack_start(label, False)
		label.show()

		self._buddy_store = gtk.ListStore(gobject.TYPE_STRING,
					 	 		  		  gtk.gdk.Pixbuf,
					  			  		  gobject.TYPE_PYOBJECT,
					  			  		  bool)

		sw = gtk.ScrolledWindow()
		sw.set_shadow_type(gtk.SHADOW_IN)
		sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		self._buddy_list_view = gtk.TreeView(self._buddy_store)
		self._buddy_list_view.set_headers_visible(False)
		self._buddy_list_view.connect("cursor-changed", self._on_buddyList_buddy_selected)
		self._buddy_list_view.connect("row-activated", self._on_buddyList_buddy_double_clicked)

		sw.add(self._buddy_list_view)
		self._buddy_list_view.show()

		renderer = gtk.CellRendererPixbuf()
		column = gtk.TreeViewColumn("", renderer, pixbuf=self._MODEL_COL_ICON)
		column.set_resizable(False)
		column.set_expand(False);
		self._buddy_list_view.append_column(column)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("", renderer, text=self._MODEL_COL_NICK)
		column.set_resizable(True)
		column.set_sizing("GTK_TREE_VIEW_COLUMN_GROW_ONLY");
		column.set_expand(True);
		self._buddy_list_view.append_column(column)

		self.pack_start(sw)
		sw.show()

		button_box = gtk.HButtonBox()

		self._share_button = gtk.Button(_('Share'))
		self._share_button.connect('clicked', self._share_button_clicked_cb)
		button_box.pack_start(self._share_button)
		self._share_button.show()

		self.pack_start(button_box, False)
		button_box.show()
	
	def _share_button_clicked_cb(self, button):
		self._activity.share()
		self._share_button.set_sensitive(False)

	def _on_buddyList_buddy_selected(self, view, *args):
		(model, aniter) = view.get_selection().get_selected()
		name = model.get(aniter, self._MODEL_COL_NICK)

	def _on_buddyList_buddy_double_clicked(self, view, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = view.get_selection().get_selected()
		chat = None
		buddy = view.get_model().get_value(aniter, self._MODEL_COL_BUDDY)
		if buddy:
			chat_service = buddy.get_service_of_type(BuddyChat.SERVICE_TYPE)
			activity = self._shell.start_activity('com.redhat.Sugar.ChatActivity')
			#activity.execute('start', [chat_service.object_path()])

	def __buddy_icon_changed_cb(self, buddy):
		it = self._get_iter_for_buddy(buddy)
		self._buddy_store.set(it, self._MODEL_COL_ICON, buddy.get_icon_pixbuf())

	def _activity_appeared_cb(self, pservice, activity):
		if self._activity_ps:
			return
		if activity.get_id() == self._activity.get_id():
			self._set_activity_ps(activity)

	def _buddy_joined_cb(self, pservice, buddy):
		self._add_buddy(buddy)

	def _add_buddy(self, buddy):
		if buddy.is_owner():
			# Do not show ourself in the buddy list
			return

		aniter = self._buddy_store.append(None)
		self._buddy_store.set(aniter,
						  self._MODEL_COL_NICK, buddy.get_name(),
						  self._MODEL_COL_BUDDY, buddy)
		buddy.connect('icon-changed', self.__buddy_icon_changed_cb)

	def _buddy_left_cb(self, pservice, buddy):
		aniter = self._get_iter_for_buddy(buddy)
		if aniter:
			self._buddy_store.remove(aniter)

	def _get_iter_for_buddy(self, buddy):
		aniter = self._buddy_store.get_iter_first()
		while aniter:
			list_buddy = self._buddy_store.get_value(aniter, self._MODEL_COL_BUDDY)
			if buddy == list_buddy:
				return aniter
			aniter = self._buddy_store.iter_next(aniter)
