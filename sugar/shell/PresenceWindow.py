import pygtk
pygtk.require('2.0')
import gtk
import gobject

from sugar.presence.PresenceService import PresenceService

class PresenceWindow(gtk.Window):
	_MODEL_COL_NICK = 0
	_MODEL_COL_ICON = 1
	_MODEL_COL_BUDDY = 2
	_MODEL_COL_VISIBLE = 3
		
	def __init__(self, activity_container):
		gtk.Window.__init__(self)
		
		self._activity_container = activity_container
		self._activity = None

		self._pservice = PresenceService.get_instance()
		self._pservice.connect("buddy-appeared", self._on_buddy_appeared_cb)
		self._pservice.connect("buddy-disappeared", self._on_buddy_disappeared_cb)
		self._pservice.set_debug(True)
		self._pservice.start()
		
		self._setup_ui()

	def _is_buddy_visible(self, buddy):
		if self._activity:
			activity_type = self._activity.get_default_type()
			service = buddy.get_service_of_type(activity_type, self._activity)
			return service is not None
		else:
			return True

	def _update_buddies_visibility(self):
		for row in self._buddy_store:
			row[self._MODEL_COL_VISIBLE] = self._is_buddy_visible(row[self._MODEL_COL_BUDDY])

	def set_activity(self, activity):
		self._activity = activity
		self._update_buddies_visibility()

	def _setup_ui(self):
		vbox = gtk.VBox(False, 6)
		vbox.set_border_width(12)
		
		label = gtk.Label("Who's around:")
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()

		self._buddy_store = gtk.ListStore(gobject.TYPE_STRING,
					 	 		  		  gtk.gdk.Pixbuf,
					  			  		  gobject.TYPE_PYOBJECT,
					  			  		  bool)
		buddy_list_model = self._buddy_store.filter_new()
		buddy_list_model.set_visible_column(self._MODEL_COL_VISIBLE)

		sw = gtk.ScrolledWindow()
		sw.set_shadow_type(gtk.SHADOW_IN)
		sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		self._buddy_list_view = gtk.TreeView(buddy_list_model)
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

		vbox.pack_start(sw)
		sw.show()

		button_box = gtk.HButtonBox()

		share_button = gtk.Button('Share')
		share_button.connect('clicked', self._share_button_clicked_cb)
		button_box.pack_start(share_button)
		share_button.show()

		vbox.pack_start(button_box, False)
		button_box.show()

		self.add(vbox)
		vbox.show()
	
	def _share_button_clicked_cb(self, button):
		self._activity_container.current_activity.publish()
	
	def _on_buddyList_buddy_selected(self, view, *args):
		(model, aniter) = view.get_selection().get_selected()
		name = model.get(aniter, self._MODEL_COL_NICK)

	def _on_buddyList_buddy_double_clicked(self, view, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = widget.get_selection().get_selected()
		chat = None
		buddy = view.get_model().get_value(aniter, self._MODEL_COL_BUDDY)
		if buddy and not self._chats.has_key(buddy):
			#chat = BuddyChat(self, buddy)
			#self._chats[buddy] = chat
			#chat.connect_to_shell()
			pass

	def __buddy_icon_changed_cb(self, buddy):
		it = self._get_iter_for_buddy(buddy)
		self._buddy_store.set(it, self._MODEL_COL_ICON, buddy.get_icon_pixbuf())

	def _on_buddy_appeared_cb(self, pservice, buddy):
		if buddy.is_owner():
			# Do not show ourself in the buddy list
			return

		aniter = self._buddy_store.append(None)
		self._buddy_store.set(aniter,
						  self._MODEL_COL_NICK, buddy.get_nick_name(),
						  self._MODEL_COL_BUDDY, buddy,
						  self._MODEL_COL_VISIBLE, self._is_buddy_visible(buddy))
		buddy.connect('icon-changed', self.__buddy_icon_changed_cb)
		buddy.connect('service-added', self.__buddy_service_added_cb)
		buddy.connect('service-removed', self.__buddy_service_removed_cb)

	def __buddy_service_added_cb(self, buddy, service):
		self._update_buddies_visibility()

	def __buddy_service_removed_cb(self, buddy, service):
		self._update_buddies_visibility()
		
	def _on_buddy_disappeared_cb(self, pservice, buddy):
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
