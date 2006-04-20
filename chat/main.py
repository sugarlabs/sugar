#!/usr/bin/python -t

import os, sys, pwd
sys.path.append(os.getcwd())
import gtk, gobject

from SimpleGladeApp import SimpleGladeApp
import presence
import network
import avahi
import BuddyList

glade_dir = os.getcwd()

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
		(model, aniter) = widget.get_selection().get_selected()
		name = self.treemodel.get(aniter,0)
		print "Double-clicked %s" % name

	def _on_buddy_presence_event(self, action, buddy):
		if action == BuddyList.ACTION_BUDDY_ADDED:
			aniter = self.treemodel.insert_after(None,None)
			self.treemodel.set(aniter, 0, buddy.nick())
		elif action == BuddyList.ACCTION_BUDDY_REMOVED:
			aniter = self.treemodel.get_iter(buddy.nick())
			if aniter:
				self.treemodel.remove(iter)

	def _on_main_window_delete(self, widget, *args):
		self.quit()

	def _recv_group_message(self, msg):
		aniter = self._group_chat_buffer.get_end_iter()
		self._group_chat_buffer.insert(aniter, msg['data'] + "\n")
#		print "Message: %s" % msg['data']

	def _send_group_message(self, widget, *args):
		text = widget.get_text()
		if len(text) > 0:
			self._gc_controller.send_msg(text)
		widget.set_text("")	

	def new(self):
		self._group_chat_buffer = gtk.TextBuffer()
		self.chatView.set_buffer(self._group_chat_buffer)

		self.treemodel = gtk.TreeStore(gobject.TYPE_STRING)
		self.buddyListView.set_model(self.treemodel)
		self.buddyListView.connect("cursor-changed", self._on_buddyList_buddy_selected)
		self.buddyListView.connect("row-activated", self._on_buddyList_buddy_double_clicked)
		self.mainWindow.connect("delete-event", self._on_main_window_delete)
		self.entry.connect("activate", self._send_group_message)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("", renderer, text=0)
		column.set_resizable(True)
		column.set_sizing("GTK_TREE_VIEW_COLUMN_GROW_ONLY");
		column.set_expand(True);
		self.buddyListView.append_column(column)

		self._pannounce.register_service(self._realname, 6666, presence.OLPC_CHAT_SERVICE,
				name = self._nick, realname = self._realname)

		self._gc_controller = network.GroupChatController('224.0.0.221', 6666, self._recv_group_message)
		self._gc_controller.start()

	def cleanup(self):
		pass

def main():
	app = ChatApp()
	app.run()
	app.cleanup()

if __name__ == "__main__":
	main()
