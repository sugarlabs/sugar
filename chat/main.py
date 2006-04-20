#!/usr/bin/python -t

import os, sys, pwd
sys.path.append(os.getcwd())
import gtk, gobject

from SimpleGladeApp import SimpleGladeApp
import presence
import network
import avahi

glade_dir = os.getcwd()

class ChatApp(SimpleGladeApp):
	def __init__(self, glade_file="chat.glade", root="mainWindow", domain=None, **kwargs):

		self._pdiscovery = presence.PresenceDiscovery()
		self._pannounce = presence.PresenceAnnounce()

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

	def new_service(self, action, interface, protocol, name, stype, domain, flags):
		if action != 'added' or stype != presence.OLPC_CHAT_SERVICE:
			return
		self._pdiscovery.resolve_service(interface, protocol, name, stype, domain, self.service_resolved)

	def on_buddyList_buddy_selected(self, widget, *args):
		(model, aniter) = widget.get_selection().get_selected()
		name = self.treemodel.get(aniter,0)
		print "Selected %s" % name

	def on_buddyList_buddy_double_clicked(self, widget, *args):
		(model, aniter) = widget.get_selection().get_selected()
		name = self.treemodel.get(aniter,0)
		print "Double-clicked %s" % name

	def on_main_window_delete(self, widget, *args):
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

	def _pair_to_dict(self, l):
		res = {}
		for el in l:
			tmp = el.split('=', 1)
			if len(tmp) > 1:
				res[tmp[0]] = tmp[1]
			else:
				res[tmp[0]] = ''
		return res

	def service_resolved(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		data = self._pair_to_dict(avahi.txt_array_to_string_array(txt))
		if len(data) > 0 and 'name' in data.keys():
			aniter = self.treemodel.insert_after(None,None)
			self.treemodel.set(aniter, 0, data['name'])

	def new(self):
		self._group_chat_buffer = gtk.TextBuffer()
		self.chatView.set_buffer(self._group_chat_buffer)

		self.treemodel = gtk.TreeStore(gobject.TYPE_STRING)
		self.buddyList.set_model(self.treemodel)
		self.buddyList.connect("cursor-changed", self.on_buddyList_buddy_selected)
		self.buddyList.connect("row-activated", self.on_buddyList_buddy_double_clicked)
		self.mainWindow.connect("delete-event", self.on_main_window_delete)
		self.entry.connect("activate", self._send_group_message)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("", renderer, text=0)
		column.set_resizable(True)
		column.set_sizing("GTK_TREE_VIEW_COLUMN_GROW_ONLY");
		column.set_expand(True);
		self.buddyList.append_column(column)

		self._pannounce.register_service(self._realname, 6666, presence.OLPC_CHAT_SERVICE, name=self._nick)
		self._pdiscovery.add_service_listener(self.new_service)
		self._pdiscovery.start()

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
