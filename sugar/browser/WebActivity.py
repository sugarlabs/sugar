import pygtk
pygtk.require('2.0')
import gtk
import geckoembed

from sugar.shell import activity
from sugar.browser.AddressItem import AddressItem

class AddressToolbar(gtk.Toolbar):
	def __init__(self, shell):
		gtk.Toolbar.__init__(self)

		self._shell = shell

		address_item = AddressItem(self.__open_address_cb)		
		self.insert(address_item, 0)
		address_item.show()

	def __open_address_cb(self, address):
		self._shell.open_browser(address)

class WebActivity(activity.Activity):
	def __init__(self, shell):
		activity.Activity.__init__(self)
		self._shell = shell
	
	def activity_on_connected_to_shell(self):
		self.activity_set_tab_text("Web")
		self.activity_set_tab_icon_name("web-browser")
		self.activity_show_icon(True)

		vbox = gtk.VBox()
			
		self.embed = geckoembed.Embed()
		self.embed.connect("open-address", self.__open_address);		
		vbox.pack_start(self.embed)
		self.embed.show()

		address_toolbar = AddressToolbar(self._shell)
		vbox.pack_start(address_toolbar, False)
		address_toolbar.show()
		
		plug = self.activity_get_gtk_plug()		
		plug.add(vbox)
		plug.show()

		vbox.show()
		
		self.embed.load_address("http://www.google.com")
		
	def __open_address(self, embed, uri, data=None):
		if uri.startswith("http://www.google.com"):
			return False
		else:
			self._shell.open_browser(uri)
			return True

	def activity_on_disconnected_from_shell(self):
		gtk.main_quit()
