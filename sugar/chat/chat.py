#!/usr/bin/python -t
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk, gobject

from sugar.shell import activity
from sugar.p2p.Group import Group
from sugar.p2p.Group import LocalGroup
from sugar.p2p.Service import Service
from sugar.p2p.StreamReader import StreamReader
from sugar.p2p.StreamWriter import StreamWriter
import sugar.env

import richtext

CHAT_SERVICE_TYPE = "_olpc_chat._tcp"
CHAT_SERVICE_PORT = 6100

GROUP_CHAT_SERVICE_TYPE = "_olpc_group_chat._udp"
GROUP_CHAT_SERVICE_ADDRESS = "224.0.0.221"
GROUP_CHAT_SERVICE_PORT = 6200

class Chat(activity.Activity):
	def __init__(self, controller):
		self._controller = controller
		activity.Activity.__init__(self)

	def activity_on_connected_to_shell(self):
		self.activity_set_tab_text(self._act_name)
		self._plug = self.activity_get_gtk_plug()
		self._ui_setup(self._plug)
		self._plug.show_all()
		
	def _create_chat(self):
		chat_vbox = gtk.VBox()
		chat_vbox.set_spacing(6)

		sw = gtk.ScrolledWindow()
		sw.set_shadow_type(gtk.SHADOW_IN)
		sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
		self._chat_view = richtext.RichTextView()
		self._chat_view.connect("link-clicked", self.__link_clicked_cb)
		self._chat_view.set_editable(False)
		self._chat_view.set_cursor_visible(False)
		sw.add(self._chat_view)
		self._chat_view.show()
		chat_vbox.pack_start(sw)
		sw.show()

		chat_view_sw = gtk.ScrolledWindow()
		chat_view_sw.set_shadow_type(gtk.SHADOW_IN)
		chat_view_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self._editor = richtext.RichTextView()
		self._editor.connect("key-press-event", self.__key_press_event_cb)
		self._editor.set_size_request(-1, 50)
		chat_view_sw.add(self._editor)
		self._editor.show()

		chat_vbox.pack_start(chat_view_sw, False)
		chat_view_sw.show()
		
		return chat_vbox, self._editor.get_buffer()

	def _ui_setup(self, base):
		vbox = gtk.VBox(False, 6)

		self._hbox = gtk.HBox(False, 12)
		self._hbox.set_border_width(12)

		[chat_vbox, buf] = self._create_chat()
		self._hbox.pack_start(chat_vbox)
		chat_vbox.show()
		
		vbox.pack_start(self._hbox)
		self._hbox.show()

		toolbar = self._create_toolbar(buf)
		vbox.pack_start(toolbar, False)
		toolbar.show()

		base.add(vbox)
		vbox.show()

	def __link_clicked_cb(self, view, address):
		self._browser_shell.open_browser(address)

	def __key_press_event_cb(self, text_view, event):
		if event.keyval == gtk.keysyms.Return:
			buf = text_view.get_buffer()
			
			serializer = richtext.RichTextSerializer()
			text = serializer.serialize(buf)
			self.send_message(text)

			buf.set_text("")
			buf.place_cursor(buf.get_start_iter())

			return True

	def _create_toolbar(self, rich_buf):
		toolbar = richtext.RichTextToolbar(rich_buf)

		item = gtk.MenuToolButton(None, "Links")
		item.set_menu(gtk.Menu())
		item.connect("show-menu", self.__show_link_menu_cb)
		toolbar.insert(item, -1)
		item.show()
		
		return toolbar

	def __link_activate_cb(self, item, link):
		buf = self._editor.get_buffer()
		buf.append_link(link['title'], link['address'])

	def __show_link_menu_cb(self, button):
		menu = gtk.Menu()
		
		links = self._browser_shell.get_links()

		for link in links:
			item = gtk.MenuItem(link['title'], False)
			item.connect("activate", self.__link_activate_cb, link)
			menu.append(item)
			item.show()
		
		button.set_menu(menu)
		
	def activity_on_close_from_user(self):
		print "act %d: in activity_on_close_from_user" % self.activity_get_id()
		self.activity_shutdown()

	def activity_on_lost_focus(self):
		print "act %d: in activity_on_lost_focus" % self.activity_get_id()

	def activity_on_got_focus(self):
		print "act %d: in activity_on_got_focus" % self.activity_get_id()
		# FIXME self._controller.notify_activate(self)

	def recv_message(self, buddy, msg):
		self._insert_rich_message(buddy.get_nick_name(), msg)
		self._controller.notify_new_message(self, buddy)

	def _insert_rich_message(self, nick, msg):
		buf = self._chat_view.get_buffer()
		aniter = buf.get_end_iter()
		buf.insert(aniter, nick + ": ")
		
		serializer = richtext.RichTextSerializer()
		serializer.deserialize(msg, buf)

		aniter = buf.get_end_iter()
		buf.insert(aniter, "\n")

	def _local_message(self, success, text):
		if not success:
			message = "Error: %s\n" % text
			buf = self._chat_view.get_buffer()
			aniter = buf.get_end_iter()
			buf.insert(aniter, message)
		else:
			owner = self._controller.get_group().get_owner()
			self._insert_rich_message(owner.get_nick_name(), text)

class BuddyChat(Chat):
	def __init__(self, controller, buddy):
		self._buddy = buddy
		self._act_name = "Chat: %s" % buddy.get_nick_name()
		Chat.__init__(self, controller)

	def _start(self):
		group = self._controller.get_group()
		buddy_name = self._buddy.get_service_name()
		service = group.get_service(buddy_name, CHAT_SERVICE_TYPE)
		self._stream_writer = StreamWriter(group, service)

	def activity_on_connected_to_shell(self):
		Chat.activity_on_connected_to_shell(self)
		self.activity_set_can_close(True)
		self.activity_set_tab_icon_name("im")
		self.activity_show_icon(True)
		self._start()
		
	def recv_message(self, sender, msg):
		Chat.recv_message(self, self._buddy, msg)

	def send_message(self, text):
		if len(text) > 0:
			self._stream_writer.write(text)
			self._local_message(True, text)

	def activity_on_close_from_user(self):
		Chat.activity_on_close_from_user(self)
		del self._chats[self._buddy]
			
class GroupChat(Chat):

	_MODEL_COL_NICK = 0
	_MODEL_COL_ICON = 1
	_MODEL_COL_BUDDY = 2
	
	def __init__(self):
		self._act_name = "Chat"
		self._chats = {}
		
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Browser', '/com/redhat/Sugar/Browser')
		self._browser_shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.BrowserShell')

		Chat.__init__(self, self)

	def get_group(self):
		return self._group

	def _start(self):
		self._group = LocalGroup()
		self._group.add_presence_listener(self._on_group_event)
		self._group.join()
		
		name = self._group.get_owner().get_service_name()
		service = Service(name, CHAT_SERVICE_TYPE, '', CHAT_SERVICE_PORT)
		self._buddy_reader = StreamReader(self._group, service)
		self._buddy_reader.set_listener(self._buddy_recv_message)
		service.register(self._group)

		service = Service(name, GROUP_CHAT_SERVICE_TYPE,
						  GROUP_CHAT_SERVICE_ADDRESS,
						  GROUP_CHAT_SERVICE_PORT, True)
		self._group.add_service(service)				  
		
		self._buddy_reader = StreamReader(self._group, service)
		self._buddy_reader.set_listener(self.recv_message)
		
		self._stream_writer = StreamWriter(self._group, service)

	def _create_sidebar(self):
		vbox = gtk.VBox(False, 6)
		
		label = gtk.Label("Who's around:")
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()

		self._buddy_list_model = gtk.ListStore(gobject.TYPE_STRING, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT)

		image_path = sugar.env.get_data_file('bubbleOutline.png')
		self._pixbuf_active_chat = gtk.gdk.pixbuf_new_from_file(image_path)
		
		image_path = sugar.env.get_data_file('bubble.png')
		self._pixbuf_new_message = gtk.gdk.pixbuf_new_from_file(image_path)

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

		return vbox

	def _ui_setup(self, base):
		Chat._ui_setup(self, base)

		sidebar = self._create_sidebar()
		self._hbox.pack_start(sidebar, False)
		sidebar.show()
		self._plug.show_all()

	def activity_on_connected_to_shell(self):
		Chat.activity_on_connected_to_shell(self)
		
		self.activity_set_tab_icon_name("stock_help-chat")
		self.activity_show_icon(True)

		aniter = self._buddy_list_model.append(None)
		self._buddy_list_model.set(aniter, self._MODEL_COL_NICK, "Group",
				self._MODEL_COL_ICON, self._pixbuf_active_chat, self._MODEL_COL_BUDDY, None)
		self._start()

	def activity_on_disconnected_from_shell(self):
		Chat.activity_on_disconnected_from_shell(self)
		gtk.main_quit()

	def _on_buddyList_buddy_selected(self, widget, *args):
		(model, aniter) = widget.get_selection().get_selected()
		name = self._buddy_list_model.get(aniter, self._MODEL_COL_NICK)
		print "Selected %s" % name

	def _on_buddyList_buddy_double_clicked(self, widget, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = widget.get_selection().get_selected()
		chat = None
		buddy = self._buddy_list_model.get_value(aniter, self._MODEL_COL_BUDDY)
		if buddy and not self._chats.has_key(buddy):
			chat = BuddyChat(self, buddy)
			self._chats[buddy] = chat
			chat.activity_connect_to_shell()

	def _on_group_event(self, action, buddy):
		if buddy.get_nick_name() == self._group.get_owner().get_nick_name():
			# Do not show ourself in the buddy list
			pass
		elif action == Group.BUDDY_JOIN:
			aniter = self._buddy_list_model.append(None)
			self._buddy_list_model.set(aniter, self._MODEL_COL_NICK, buddy.get_nick_name(),
					self._MODEL_COL_ICON, None, self._MODEL_COL_BUDDY, buddy)
		elif action == Group.BUDDY_LEAVE:
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

	def notify_new_message(self, chat, buddy):
		aniter = self._get_iter_for_buddy(buddy)
		self._buddy_list_model.set(aniter, self._MODEL_COL_ICON, self._pixbuf_new_message)

	def notify_activate(self, chat, buddy):
		aniter = self._get_iter_for_buddy(buddy)
		self._buddy_list_model.set(aniter, self._MODEL_COL_ICON, self._pixbuf_active_chat)

	def send_message(self, text):
		if len(text) > 0:
			self._stream_writer.write(text)
		self._local_message(True, text)

	def recv_message(self, buddy, msg):
		if buddy:
			self._insert_rich_message(buddy.get_nick_name(), msg)
			self._controller.notify_new_message(self, None)

	def _buddy_recv_message(self, sender, msg):
		if not self._chats.has_key(sender):
			chat = BuddyChat(self, sender)
			self._chats[sender] = chat
			chat.activity_connect_to_shell()
		else:
			chat = self._chats[sender]
		chat.recv_message(sender, msg)

class ChatShell(dbus.service.Object):
	instance = None

	def get_instance():
		if not ChatShell.instance:
			ChatShell.instance = ChatShell()
		return ChatShell.instance
		
	get_instance = staticmethod(get_instance)

	def __init__(self):
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Chat', bus=session_bus)
		object_path = '/com/redhat/Sugar/Chat'

		dbus.service.Object.__init__(self, bus_name, object_path)

	def open_group_chat(self):
		self._group_chat = GroupChat()
		self._group_chat.activity_connect_to_shell()

	@dbus.service.method('com.redhat.Sugar.ChatShell')
	def send_message(self, message):
		self._group_chat.send_message(message)
		
def main():
	ChatShell.get_instance().open_group_chat()
	gtk.main()

if __name__ == "__main__":
	main()
