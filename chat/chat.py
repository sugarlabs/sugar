#!/usr/bin/python -t
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk, gobject

import sys
import os
import pwd
import gc
import socket

sys.path.append(os.getcwd())
sys.path.append('../shell/example-activity/')
import activity

import presence
import BuddyList
import network
import richtext
import xmlrpclib

class Chat(object):
	def __init__(self, parent, view, label):
		self._parent = parent
		self._buffer = richtext.RichTextBuffer()
		self._view = view
		self._label = label

	def activate(self, label):
		self._view.set_buffer(self._buffer)
		self._label.set_text(label)

	def recv_message(self, buddy, msg):
		self._insert_rich_message(buddy.nick(), msg)
		self._parent.notify_new_message(self, buddy)

	def _insert_rich_message(self, nick, msg):
		aniter = self._buffer.get_end_iter()
		self._buffer.insert(aniter, nick + ": ")
		
		serializer = richtext.RichTextSerializer()
		serializer.deserialize(msg, self._buffer)

		aniter = self._buffer.get_end_iter()
		self._buffer.insert(aniter, "\n")

	def _local_message(self, success, text):
		if not success:
			message = "Error: %s\n" % text
			aniter = self._buffer.get_end_iter()
			self._buffer.insert(aniter, message)
		else:
			(nick, realname) = self._parent.local_name()
			self._insert_rich_message(nick, text)

class BuddyChat(Chat):
	def __init__(self, parent, buddy, view, label):
		self._buddy = buddy
		Chat.__init__(self, parent, view, label)

	def activate(self):
		Chat.activate(self, self._buddy.nick())

	def recv_message(self, msg):
		Chat.recv_message(self, self._buddy, msg)

	def send_message(self, text):
		if len(text) <= 0:
			return
		addr = "http://%s:%d" % (self._buddy.address(), self._buddy.port())
		peer = xmlrpclib.ServerProxy(addr)
		msg = text
		success = True
		try:
			peer.message(text)
		except (socket.error, xmlrpclib.Fault), e:
			msg = str(e)
			success = False
		self._local_message(success, msg)

class GroupChat(Chat):
	def __init__(self, parent, view, label):
		Chat.__init__(self, parent, view, label)
		self._gc_controller = network.GroupChatController('224.0.0.221', 6666, self._recv_group_message)
		self._gc_controller.start()

	def activate(self):
		Chat.activate(self, "Group Chat")

	def send_message(self, text):
		if len(text) > 0:
			self._gc_controller.send_msg(text)
		self._local_message(True, text)

	def recv_message(self, buddy, msg):
		self._insert_rich_message(buddy.nick(), msg)
		self._parent.notify_new_message(self, None)

	def _recv_group_message(self, msg):
		buddy = self._parent.find_buddy_by_address(msg['addr'])
		if buddy:
			self.recv_message(buddy, msg['data'])


class ChatRequestHandler(object):
	def __init__(self, parent, chat_view, chat_label):
		self._parent = parent
		self._chat_view = chat_view
		self._chat_label = chat_label

	def message(self, message):
		client_address = network.get_authinfo()
		buddy = self._parent.find_buddy_by_address(client_address[0])
		if buddy:
			chat = buddy.chat()
			if not chat:
				chat = BuddyChat(self._parent, buddy, self._chat_view, self._chat_label)
				buddy.set_chat(chat)
			chat.recv_message(message)
		return True

class ChatActivity(activity.Activity):

	_MODEL_COL_NICK = 0
	_MODEL_COL_ICON = 1
	_MODEL_COL_BUDDY = 2

	def __init__(self):
		activity.Activity.__init__(self)
		self._act_name = "Chat"
		self._active_chat_buddy = None
		self._pannounce = presence.PresenceAnnounce()

		(self._nick, self._realname) = self._get_name()

		self._buddy_list = BuddyList.BuddyList(self._realname)
		self._buddy_list.add_buddy_listener(self._on_buddy_presence_event)

	def _create_chat(self):
		chat_vbox = gtk.VBox()
		chat_vbox.set_spacing(6)

		self._chat_label = gtk.Label()
		chat_vbox.pack_start(self._chat_label, False)
		# Do we actually need this label?
		# self._chat_label.show()
		
		sw = gtk.ScrolledWindow()
		sw.set_shadow_type(gtk.SHADOW_IN)
		sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
		self._chat_view = gtk.TextView()
		sw.add(self._chat_view)
		self._chat_view.show()
		chat_vbox.pack_start(sw)
		sw.show()

		rich_buf = richtext.RichTextBuffer()		
		chat_view_sw = gtk.ScrolledWindow()
		chat_view_sw.set_shadow_type(gtk.SHADOW_IN)
		chat_view_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self._editor = gtk.TextView(rich_buf)
		self._editor.connect("key-press-event", self.__key_press_event_cb)
		self._editor.set_size_request(-1, 50)
		chat_view_sw.add(self._editor)
		self._editor.show()

		chat_vbox.pack_start(chat_view_sw, False)
		chat_view_sw.show()
		
		return chat_vbox, rich_buf

	def _create_sidebar(self):
		vbox = gtk.VBox(False, 6)
		
		label = gtk.Label("Who's around:")
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()
	
		self._buddy_list_model = gtk.ListStore(gobject.TYPE_STRING, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT)

		self._pixbuf_active_chat = gtk.gdk.pixbuf_new_from_file("bubbleOutline.png")
		self._pixbuf_new_message = gtk.gdk.pixbuf_new_from_file("bubble.png")

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

		button_box = gtk.VButtonBox()
		button_box.set_border_width(18)
		
		talk_alone_button = gtk.Button("Talk alone")
		button_box.pack_start(talk_alone_button)
		talk_alone_button.show()
		
		vbox.pack_start(button_box, False)
		button_box.show()
		
		return vbox

	def _ui_setup(self, plug):
		vbox = gtk.VBox(False, 6)

		hbox = gtk.HBox(False, 12)
		hbox.set_border_width(12)

		[chat, rich_buf] = self._create_chat()
		hbox.pack_start(chat)
		chat.show()
		
		sidebar = self._create_sidebar()
		hbox.pack_start(sidebar, False)
		sidebar.show()

		vbox.pack_start(hbox)
		hbox.show()

		toolbar = richtext.RichTextToolbar(rich_buf)
		vbox.pack_start(toolbar, False);
		toolbar.show()		
		
		self._group_chat = GroupChat(self, self._chat_view, self._chat_label)
		aniter = self._buddy_list_model.append(None)
		self._buddy_list_model.set(aniter, self._MODEL_COL_NICK, "Group",
				self._MODEL_COL_ICON, self._pixbuf_active_chat, self._MODEL_COL_BUDDY, None)
		self._activate_chat_for_buddy(None)

		plug.add(vbox)
		vbox.show()
		
	def __key_press_event_cb(self, text_view, event):
		if event.keyval == gtk.keysyms.Return:
			buf = text_view.get_buffer()
			chat = self._get_active_chat()
			
			serializer = richtext.RichTextSerializer()
			text = serializer.serialize(buf)
			chat.send_message(text)

			buf.set_text("")
			buf.place_cursor(buf.get_start_iter())

			return True

	def _start(self):
		self._buddy_list.start()
		self._pannounce.register_service(self._realname, 6666, presence.OLPC_CHAT_SERVICE,
				name = self._nick, realname = self._realname)

		# Create the P2P chat XMLRPC server
		self._p2p_req_handler = ChatRequestHandler(self, self._chat_view, self._chat_label)
		self._p2p_server = network.GlibXMLRPCServer(("", 6666))
		self._p2p_server.register_instance(self._p2p_req_handler)

	def activity_on_connected_to_shell(self):
		print "act %d: in activity_on_connected_to_shell" % self.activity_get_id()
		self.activity_set_tab_text(self._act_name)
		self._plug = self.activity_get_gtk_plug()
		self._ui_setup(self._plug)
		self._plug.show()
		self._start()

	def activity_on_disconnected_from_shell(self):
		print "act %d: in activity_on_disconnected_from_shell"%self.activity_get_id()
		print "act %d: Shell disappeared..."%self.activity_get_id()
		gtk.main_quit()
		gc.collect()

	def activity_on_close_from_user(self):
		print "act %d: in activity_on_close_from_user"%self.activity_get_id()
		self.activity_shutdown()

	def activity_on_lost_focus(self):
		print "act %d: in activity_on_lost_focus"%self.activity_get_id()

	def activity_on_got_focus(self):
		print "act %d: in activity_on_got_focus"%self.activity_get_id()

	def _get_name(self):
		ent = pwd.getpwuid(os.getuid())
		nick = ent[0]
		if not nick or not len(nick):
			nick = "n00b"
		realname = ent[4]
		if not realname or not len(realname):
			realname = "Some Clueless User"
		return (nick, realname)

	def _on_buddyList_buddy_selected(self, widget, *args):
		(model, aniter) = widget.get_selection().get_selected()
		name = self._buddy_list_model.get(aniter, self._MODEL_COL_NICK)
		print "Selected %s" % name

	def _on_buddyList_buddy_double_clicked(self, widget, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = widget.get_selection().get_selected()
		chat = None
		buddy = self._buddy_list_model.get_value(aniter, self._MODEL_COL_BUDDY)
		if buddy and not buddy.chat():
			chat = BuddyChat(self, buddy, self._chat_view, self._chat_label)
			buddy.set_chat(chat)
		self._activate_chat_for_buddy(buddy)

	def _on_buddy_presence_event(self, action, buddy):
		if action == BuddyList.ACTION_BUDDY_ADDED:
			aniter = self._buddy_list_model.append(None)
			self._buddy_list_model.set(aniter, self._MODEL_COL_NICK, buddy.nick(),
					self._MODEL_COL_ICON, None, self._MODEL_COL_BUDDY, buddy)
		elif action == BuddyList.ACTION_BUDDY_REMOVED:
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
		if chat != self._get_active_chat():
			aniter = self._get_iter_for_buddy(buddy)
			self._buddy_list_model.set(aniter, self._MODEL_COL_ICON, self._pixbuf_new_message)

	def find_buddy_by_address(self, address):
		return self._buddy_list.find_buddy_by_address(address)

	def local_name(self):
		return (self._nick, self._realname)

	def _activate_chat_for_buddy(self, buddy):
		self._active_chat_buddy = buddy

		# Clear the "new message" icon when the user activates the chat
		aniter = self._get_iter_for_buddy(buddy)
		# Select the row in the list
		if aniter:
			selection = self._buddy_list_view.get_selection()
			selection.select_iter(aniter)
		icon = self._buddy_list_model.get_value(aniter, self._MODEL_COL_ICON)
		if icon == self._pixbuf_new_message:
			self._buddy_list_model.set_value(aniter, self._MODEL_COL_ICON, self._pixbuf_active_chat)

		# Actually activate the chat
		chat = self._group_chat
		if self._active_chat_buddy:
			chat = buddy.chat()
		chat.activate()

	def _on_main_window_delete(self, widget, *args):
		self.quit()

	def _get_active_chat(self):
		chat = self._group_chat
		if self._active_chat_buddy:
			chat = self._active_chat_buddy.chat()
		return chat

	def run(self):
		try:
			gtk.main()
		except KeyboardInterrupt:
			pass

def main():
	app = ChatActivity()
	app.activity_connect_to_shell()
	app.run()

if __name__ == "__main__":
	main()
