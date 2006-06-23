import pygtk
pygtk.require('2.0')
import gtk

from sugar.chat.Chat import Chat

class ChatWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
		self._chat = None
	
	def set_chat(self, chat):
		if self._chat != None:
			self.remove(self._chat)

		self._chat = chat
		self.add(self._chat)
		self._chat.show()
