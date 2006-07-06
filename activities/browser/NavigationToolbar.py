import pygtk
pygtk.require('2.0')
import gtk

from gettext import gettext as _

from AddressItem import AddressItem

class NavigationToolbar(gtk.Toolbar):
	def __init__(self, browser):
		gtk.Toolbar.__init__(self)
		self._browser = browser
		self._embed = self._browser.get_embed()
		
		self.set_style(gtk.TOOLBAR_BOTH_HORIZ)
		
		self.back = gtk.ToolButton(None, _('Back'))
		self.back.set_icon_name('back')
		self.back.connect("clicked", self.__go_back_cb)
		self.insert(self.back, -1)
		self.back.show()

		self.forward = gtk.ToolButton(None, _('Forward'))
		self.forward.set_icon_name('forward')
		self.forward.connect("clicked", self.__go_forward_cb)
		self.insert(self.forward, -1)
		self.forward.show()

		self.reload = gtk.ToolButton(None, _('Reload'))
		self.reload.set_icon_name('reload')
		self.reload.connect("clicked", self.__reload_cb)
		self.insert(self.reload, -1)
		self.reload.show()

		separator = gtk.SeparatorToolItem()
		self.insert(separator, -1)
		separator.show()
		
		address_item = AddressItem(self.__open_address_cb)		
		self.insert(address_item, -1)
		address_item.show()

		self._update_sensitivity()

		self._embed.connect("location", self.__location_changed)

	def _update_sensitivity(self):
		self.back.set_sensitive(self._embed.can_go_back())
		self.forward.set_sensitive(self._embed.can_go_forward())
		
	def __go_back_cb(self, button):
		self._embed.go_back()
	
	def __go_forward_cb(self, button):
		self._embed.go_forward()
		
	def __reload_cb(self, button):
		self._embed.reload()

	def __location_changed(self, embed):
		self._update_sensitivity()

	def __open_address_cb(self, address):
		self._embed.load_address(address)
