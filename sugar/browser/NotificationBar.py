import pygtk
pygtk.require('2.0')
import gtk
import gobject

class NotificationBar(gtk.HBox):
	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
				  ([gobject.TYPE_STRING]))
	}

	def __init__(self):
		gtk.HBox.__init__(self)
		self._text_label = gtk.Label()
		self.pack_start(self._text_label)
		self._text_label.show()
		
		self._action_button = gtk.Button()
		self._action_button.connect('clicked', self.__button_clicked)
		self.pack_start(self._action_button, False)
		self._action_button.show()
	
	def set_text(self, text):
		self._text_label.set_text(text)
	
	def set_action(self, action_id, action_text):
		self._action_id = action_id
		self._action_button.set_label(action_text)
		
	def __button_clicked(self):
		self.emit("action", self._action_id)
