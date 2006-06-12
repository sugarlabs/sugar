import pygtk
pygtk.require('2.0')
import gtk
import gobject

from sugar.p2p.Stream import Stream
from sugar.presence.PresenceService import PresenceService

class PresenceWindow(gtk.Window):
	_MODEL_COL_NICK = 0
	_MODEL_COL_ICON = 1
	_MODEL_COL_BUDDY = 2
	
	def __init__(self):
		gtk.Window.__init__(self)

		self._pservice = PresenceService.get_instance()
		self._pservice.connect("buddy-appeared", self._on_buddy_appeared_cb)
		self._pservice.connect("buddy-disappeared", self._on_buddy_disappeared_cb)
		self._pservice.set_debug(True)
		self._pservice.start()
		
		self._setup_ui()

	def _setup_ui(self):
		vbox = gtk.VBox(False, 6)
		
		label = gtk.Label("Who's around:")
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()

		self._buddy_list_model = gtk.ListStore(gobject.TYPE_STRING,
											   gtk.gdk.Pixbuf,
											   gobject.TYPE_PYOBJECT)

		sw = gtk.ScrolledWindow()
		sw.set_shadow_type(gtk.SHADOW_IN)
		sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		self._buddy_list_view = gtk.TreeView(self._buddy_list_model)
		self._buddy_list_view.set_headers_visible(False)
		self._buddy_list_view.connect("cursor-changed", self._on_buddyList_buddy_selected)
		self._buddy_list_view.connect("row-activated", self._on_buddyList_buddy_double_clicked)

		sw.set_size_request(120, -1)
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

		self.add(vbox)
		vbox.show()
	
	def _on_buddyList_buddy_selected(self, widget, *args):
		(model, aniter) = widget.get_selection().get_selected()
		name = self._buddy_list_model.get(aniter, self._MODEL_COL_NICK)

	def _on_buddyList_buddy_double_clicked(self, widget, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = widget.get_selection().get_selected()
		chat = None
		buddy = self._buddy_list_model.get_value(aniter, self._MODEL_COL_BUDDY)
		if buddy and not self._chats.has_key(buddy):
			chat = BuddyChat(self, buddy)
			self._chats[buddy] = chat
			chat.connect_to_shell()

	def __buddy_icon_changed_cb(self, buddy):
		it = self._get_iter_for_buddy(buddy)
		self._buddy_list_model.set(it, self._MODEL_COL_ICON, buddy.get_icon_pixbuf())

	def _on_buddy_appeared_cb(self, pservice, buddy):
		if buddy.is_owner():
			# Do not show ourself in the buddy list
			return

		aniter = self._buddy_list_model.append(None)
		self._buddy_list_model.set(aniter,
								   self._MODEL_COL_NICK, buddy.get_nick_name(),
								   self._MODEL_COL_BUDDY, buddy)
		buddy.connect('icon-changed', self.__buddy_icon_changed_cb)

	def _on_buddy_disappeared_cb(self, pservice, buddy):
		aniter = self._get_iter_for_buddy(buddy)
		if aniter:
			self._buddy_list_model.remove(aniter)

	def _get_iter_for_buddy(self, buddy):
		aniter = self._buddy_list_model.get_iter_first()
		while aniter:
			list_buddy = self._buddy_list_model.get_value(aniter, self._MODEL_COL_BUDDY)
			if buddy == list_buddy:
				return aniter
			aniter = self._buddy_list_model.iter_next(aniter)
