import gobject
import gtk

class AddressItem(gtk.ToolItem):
	__gsignals__ = {
		'open-address':  (gobject.SIGNAL_RUN_FIRST,
						  gobject.TYPE_NONE, ([str])),
	}

	def __init__(self):
		gtk.ToolItem.__init__(self)
	
		entry = gtk.Entry()
		width = int(gtk.gdk.screen_width() / 2)
		entry.set_size_request(width, -1)
		entry.connect("activate", self.__activate_cb)
		self.add(entry)
		entry.show()

	def __activate_cb(self, entry):
		self.emit('open-address', entry.get_text())
