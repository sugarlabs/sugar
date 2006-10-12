import gtk

from gettext import gettext as _

from AddressItem import AddressItem

class NavigationToolbar(gtk.Toolbar):
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

	def set_embed(self, embed):
		self._embed = embed

		self._embed.connect("location", self.__location_changed)
		self._update_sensitivity()

		self._embed.connect("notify::progress", self._progress_changed_cb)

	def _update_sensitivity(self):
		self.back.set_sensitive(self._embed.can_go_back())
		self.forward.set_sensitive(self._embed.can_go_forward())

	def _progress_changed_cb(self, embed, pspec):
		self._address_item.set_progress(embed.props.progress)

	def __go_back_cb(self, button):
		self._embed.go_back()
	
	def __go_forward_cb(self, button):
		self._embed.go_forward()
		
	def __location_changed(self, embed):
		self._update_sensitivity()

	def __open_address_cb(self, item, address):
		self._embed.load_url(address)
