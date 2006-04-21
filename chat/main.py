#!/usr/bin/python -t
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import os, sys, pwd
sys.path.append(os.getcwd())
import gtk, gobject

from SimpleGladeApp import SimpleGladeApp
import presence
import network
import avahi
import BuddyList

glade_dir = os.getcwd()


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


class ChatApp(SimpleGladeApp):
	def __init__(self, glade_file="chat.glade", root="mainWindow", domain=None, **kwargs):
		self._pannounce = presence.PresenceAnnounce()
		self._buddy_list = BuddyList.BuddyList()
		self._buddy_list.add_buddy_listener(self._on_buddy_presence_event)

		(self._nick, self._realname) = self._get_name()

		path = os.path.join(glade_dir, glade_file)
		gtk.window_set_default_icon_name("config-users")
		SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

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
		name = self.treemodel.get(aniter,0)
		print "Selected %s" % name

	def _on_buddyList_buddy_double_clicked(self, widget, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = widget.get_selection().get_selected()
		chat = None
		buddy = self.treemodel.get_value(aniter, 1)
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
			aniter = self.treemodel.append(None)
			self.treemodel.set(aniter, 0, buddy.nick(), 1, buddy)
		elif action == BuddyList.ACCTION_BUDDY_REMOVED:
			aniter = self.treemodel.get_iter(buddy.nick())
			if aniter:
				self.treemodel.remove(iter)

	def find_buddy_by_address(self, address):
		return self._buddy_list.find_buddy_by_address(address)

	def _on_main_window_delete(self, widget, *args):
		self.quit()

	def _get_current_chat(self):
		selection = self.buddyListView.get_selection()
		(model, aniter) = selection.get_selected()
		buddy = model.get_value(aniter, 1)
		if not buddy:
			return self._group_chat
		return buddy.chat()

	def _send_chat_message(self, widget, *args):
		chat = self._get_current_chat()
		text = widget.get_text()
		chat.send_message(text)
		widget.set_text("")	

	def new(self):
		self.treemodel = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
		self.buddyListView.set_model(self.treemodel)
		self.buddyListView.connect("cursor-changed", self._on_buddyList_buddy_selected)
		self.buddyListView.connect("row-activated", self._on_buddyList_buddy_double_clicked)
		self.mainWindow.connect("delete-event", self._on_main_window_delete)
		self.entry.connect("activate", self._send_chat_message)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("", renderer, text=0)
		column.set_resizable(True)
		column.set_sizing("GTK_TREE_VIEW_COLUMN_GROW_ONLY");
		column.set_expand(True);
		self.buddyListView.append_column(column)

		self._group_chat = GroupChat(self, self.chatView, self.chatLabel)
		aniter = self.treemodel.append(None)
		self.treemodel.set(aniter, 0, "Group", 1, None)
		self._group_chat.activate()

		self._pannounce.register_service(self._realname, 6666, presence.OLPC_CHAT_SERVICE,
				name = self._nick, realname = self._realname)

	def cleanup(self):
		pass

def main():
	app = ChatApp()
	app.run()
	app.cleanup()

if __name__ == "__main__":
	main()
