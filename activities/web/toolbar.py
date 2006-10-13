import gtk

class Toolbar(gtk.Toolbar):
	def __init__(self):
		gtk.Toolbar.__init__(self)
		
		self.set_style(gtk.TOOLBAR_BOTH_HORIZ)

		self._insert_spring()

		self.back = gtk.ToolButton(None, _('Back'))
		self.back.set_icon_name('stock-back')
		self.back.connect("clicked", self.__go_back_cb)
		self.insert(self.back, -1)
		self.back.show()

		self.forward = gtk.ToolButton(None, _('Forward'))
		self.forward.set_icon_name('stock-forward')
		self.forward.connect("clicked", self.__go_forward_cb)
		self.insert(self.forward, -1)
		self.forward.show()

		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)		
		self.insert(separator, -1)
		separator.show()

		self._address_item = AddressItem()
		self._address_item.connect('open-address', self.__open_address_cb)
		self.insert(self._address_item, -1)
		self._address_item.show()

		self._insert_spring()

	def _insert_spring(self):
		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)
		separator.set_expand(True)		
		self.insert(separator, -1)
		separator.show()
