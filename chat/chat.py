#!/usr/bin/python -t
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk, gobject
import gtk.glade

import sys
import os
import pwd
import gc

sys.path.append(os.getcwd())
sys.path.append('../shell/example-activity/')
import activity

import presence
import BuddyList
import network

class Chat(object):
	def __init__(self, view, label):
		self._buffer = gtk.TextBuffer()
		self._view = view
		self._label = label

	def activate(self, label):
		self._view.set_buffer(self._buffer)
		self._label.set_text(label)

	def recv_message(self, buddy, msg):
		aniter = self._buffer.get_end_iter()
		self._buffer.insert(aniter, buddy.nick() + ": " + msg + "\n")


class GroupChat(Chat):
	def __init__(self, parent, view, label):
		Chat.__init__(self, view, label)
		self._parent = parent
		self._gc_controller = network.GroupChatController('224.0.0.221', 6666, self._recv_group_message)
		self._gc_controller.start()
		self._label_prefix = "Cha"

	def activate(self):
		Chat.activate(self, "Group Chat")

	def send_message(self, text):
		if len(text) > 0:
			self._gc_controller.send_msg(text)

	def _recv_group_message(self, msg):
		buddy = self._parent.find_buddy_by_address(msg['addr'])
		if buddy:
			self.recv_message(buddy, msg['data'])

class ChatActivity(activity.Activity):
	def __init__(self):
		activity.Activity.__init__(self)
		self._act_name = "Chat"
		self._pannounce = presence.PresenceAnnounce()
		self._buddy_list = BuddyList.BuddyList()
		self._buddy_list.add_buddy_listener(self._on_buddy_presence_event)

		(self._nick, self._realname) = self._get_name()

		self._glade = gtk.glade.XML("chat.glade", "mainTable", None)

	def _ui_setup(self, plug):
		self._buddy_list_model = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
		self._buddy_list_view = self._glade.get_widget("buddyListView")
		self._buddy_list_view.set_model(self._buddy_list_model)
		self._buddy_list_view.connect("cursor-changed", self._on_buddyList_buddy_selected)
		self._buddy_list_view.connect("row-activated", self._on_buddyList_buddy_double_clicked)

		self._entry = self._glade.get_widget("entry")
		self._entry.connect("activate", self._send_chat_message)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("", renderer, text=0)
		column.set_resizable(True)
		column.set_sizing("GTK_TREE_VIEW_COLUMN_GROW_ONLY");
		column.set_expand(True);
		self._buddy_list_view.append_column(column)

		self._chat_view = self._glade.get_widget("chatView")
		self._chat_label = self._glade.get_widget("chatLabel")
		self._group_chat = GroupChat(self, self._chat_view, self._chat_label)
		aniter = self._buddy_list_model.append(None)
		self._buddy_list_model.set(aniter, 0, "Group", 1, None)
		self._group_chat.activate()
		plug.add(self._glade.get_widget("mainTable"))

	def _start(self):
		self._buddy_list.start()
		self._pannounce.register_service(self._realname, 6666, presence.OLPC_CHAT_SERVICE,
				name = self._nick, realname = self._realname)

	def activity_on_connected_to_shell(self):
		print "act %d: in activity_on_connected_to_shell" % self.activity_get_id()
		self.activity_set_tab_text(self._act_name)
		self._plug = self.activity_get_gtk_plug()
		self._ui_setup(self._plug)
		self._plug.show_all()
		self._start()

	def activity_on_disconnected_from_shell(self):
		print "act %d: in activity_on_disconnected_from_shell"%self.activity_get_id()
		print "act %d: Shell disappeared..."%self.activity_get_id()

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
		name = self._buddy_list_model.get(aniter,0)
		print "Selected %s" % name

	def _on_buddyList_buddy_double_clicked(self, widget, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = widget.get_selection().get_selected()
		chat = None
		buddy = self._buddy_list_model.get_value(aniter, 1)
		if not buddy:
			chat = self._group_chat
		else:
			chat = buddy.chat()

		if chat:
			chat.activate()
		else:
			# start a new chat with them
			pass

	def _on_buddy_presence_event(self, action, buddy):
		if action == BuddyList.ACTION_BUDDY_ADDED:
			aniter = self._buddy_list_model.append(None)
			self._buddy_list_model.set(aniter, 0, buddy.nick(), 1, buddy)
		elif action == BuddyList.ACCTION_BUDDY_REMOVED:
			aniter = self._buddy_list_model.get_iter(buddy.nick())
			if aniter:
				self._buddy_list_model.remove(iter)

	def find_buddy_by_address(self, address):
		return self._buddy_list.find_buddy_by_address(address)

	def _on_main_window_delete(self, widget, *args):
		self.quit()

	def _get_current_chat(self):
		selection = self._buddy_list_view.get_selection()
		(model, aniter) = selection.get_selected()
		buddy = None
		if aniter:
			buddy = model.get_value(aniter, 1)
		if not buddy:
			return self._group_chat
		return buddy.chat()

	def _send_chat_message(self, widget, *args):
		chat = self._get_current_chat()
		text = widget.get_text()
		chat.send_message(text)
		widget.set_text("")	

	def run(self):
		gtk.main()

def main():
	app = ChatActivity()
	app.activity_connect_to_shell()
	app.run()

if __name__ == "__main__":
	main()
