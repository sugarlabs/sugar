import pygtk
pygtk.require('2.0')
import gtk
import gobject
import cairo

class NotificationBar(gtk.HBox):
	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
				  ([gobject.TYPE_STRING]))
	}

	def __init__(self):
		gtk.HBox.__init__(self)

		self.set_name("notif bar")
		self.set_border_width(3)
		
		self._text_label = gtk.Label()
		self._text_label.set_alignment(0.0, 0.5)
		self.pack_start(self._text_label)
		self._text_label.show()

		self._action_button = gtk.Button()
		self._action_button.connect('clicked', self.__button_clicked)
		self.pack_start(self._action_button, False)
		self._action_button.show()

		self.connect('expose_event', self.expose)

	def expose(self, widget, event):
		rect = self.get_allocation()
		ctx = widget.window.cairo_create()
		
		ctx.new_path()
		ctx.rectangle(rect.x, rect.y, rect.width, rect.height)
		ctx.set_source_rgb(0.56 , 0.75 , 1)
		ctx.fill_preserve()
		ctx.set_source_rgb(0.16 , 0.35 , 0.6)
		ctx.stroke()
		
		return False
	
	def set_text(self, text):
		self._text_label.set_markup('<b>' + text + '</b>')
	
	def set_action(self, action_id, action_text):
		self._action_id = action_id
		self._action_button.set_label(action_text)
		
	def __button_clicked(self, button):
		self.emit("action", self._action_id)
