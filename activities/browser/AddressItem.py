import gobject
import gtk

from _sugar import AddressEntry

class AddressItem(gtk.ToolItem):
	__gsignals__ = {
		'open-address':  (gobject.SIGNAL_RUN_FIRST,
						  gobject.TYPE_NONE, ([str])),
	}

	def __init__(self):
		gtk.ToolItem.__init__(self)
	
		entry = AddressEntry()
		width = int(gtk.gdk.screen_width() / 3 * 2)
		entry.set_size_request(width, -1)
		entry.connect("activate", self.__activate_cb)
		self.add(entry)
		entry.show()

		self._entry = entry

	def __activate_cb(self, entry):
		self.emit('open-address', entry.get_text())

	def set_progress(self, progress):
		self._entry.set_property('progress', progress)

	def set_address(self, address):
		self._entry.set_text(address)
