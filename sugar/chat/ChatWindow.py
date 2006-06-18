import pygtk
pygtk.require('2.0')
import gtk

from sugar.chat.Chat import Chat

class ChatWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
		self._chat = None
		self.connect("key-press-event", self.__key_press_event_cb)
	
	def set_chat(self, chat):
		if self._chat != None:
			self.remove(self._chat)

		self._chat = chat
		self.add(self._chat)
		self._chat.show()

	def __key_press_event_cb(self, window, event):
		if event.keyval == gtk.keysyms.s and \
		   event.state & gtk.gdk.CONTROL_MASK:
			if self._chat.get_mode() == Chat.SKETCH_MODE:
			   self._chat.set_mode(Chat.TEXT_MODE)
			elif self._chat.get_mode() == Chat.TEXT_MODE:
			   self._chat.set_mode(Chat.SKETCH_MODE)			

