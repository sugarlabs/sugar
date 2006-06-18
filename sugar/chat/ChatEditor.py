import pygtk
pygtk.require('2.0')
import gtk

from sugar.chat.sketchpad.SketchPad import SketchPad
import richtext

class ChatEditor(gtk.Notebook):
	TEXT_MODE = 0
	SKETCH_MODE = 1

	def __init__(self, chat, mode):
		gtk.Notebook.__init__(self)

		self._chat = chat

		self.set_show_tabs(False)
		self.set_show_border(False)
		self.set_size_request(-1, 70)
	
		chat_view_sw = gtk.ScrolledWindow()
		chat_view_sw.set_shadow_type(gtk.SHADOW_IN)
		chat_view_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self._text_view = richtext.RichTextView()
		self._text_view.connect("key-press-event", self.__key_press_event_cb)
		chat_view_sw.add(self._text_view)
		self._text_view.show()
		
		self.append_page(chat_view_sw)
		chat_view_sw.show()
		
		self._sketchpad = SketchPad()
		self.append_page(self._sketchpad)
		self._sketchpad.show()
		
		self.set_mode(mode)

	def set_mode(self, mode):
		self._mode = mode
		if self._mode == ChatEditor.SKETCH_MODE:
			self.set_current_page(1)
		elif self._mode == ChatEditor.TEXT_MODE:
			self.set_current_page(0)
			
	def get_buffer(self):
		return self._text_view.get_buffer()

	def __key_press_event_cb(self, text_view, event):
		if event.keyval == gtk.keysyms.Return:
			buf = text_view.get_buffer()
			text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
			if len(text.strip()) > 0:
				serializer = richtext.RichTextSerializer()
				text = serializer.serialize(buf)
				self._chat.send_text_message(text)

			buf.set_text("")
			buf.place_cursor(buf.get_start_iter())

			return True
