#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import geckoembed

class AddressToolbar(gtk.Toolbar):
	def __init__(self):
		gtk.Toolbar.__init__(self)

		address_item = AddressItem(self.__open_address_cb)		
		self.insert(address_item, 0)
		address_item.show()

	def __open_address_cb(self, address):
		browser = BrowserWindow(address)
		browser.show()

class AddressItem(gtk.ToolItem):
	def __init__(self, callback):
		gtk.ToolItem.__init__(self)
	
		address_entry = AddressEntry(callback)
		self.add(address_entry)
		address_entry.show()

class AddressEntry(gtk.HBox):
	def __init__(self, callback):
		gtk.HBox.__init__(self)

		self.callback = callback
		self.folded = True
		
		label = gtk.Label("Open")
		self.pack_start(label, False)
		label.show()
		
		self.button = gtk.Button()
		self.button.set_relief(gtk.RELIEF_NONE)
		self.button.connect("clicked", self.__button_clicked_cb)
		self.pack_start(self.button, False)
		self.button.show()
		
		self.entry = gtk.Entry()
		self.entry.connect("activate", self.__activate_cb)
		self.pack_start(self.entry, False)
		self.entry.show()

		self._update_folded_state()
	
	def _update_folded_state(self):
		if self.folded:
			image = gtk.Image()
			image.set_from_file("unfold.png")
			self.button.set_image(image)
			image.show()

			self.entry.hide()
		else:
			image = gtk.Image()
			image.set_from_file("fold.png")
			self.button.set_image(image)
			image.show()

			self.entry.show()
			
	def __button_clicked_cb(self, button):
		self.folded = not self.folded
		self._update_folded_state()

	def __activate_cb(self, entry):
		self.callback(entry.get_text())

class NavigationToolbar(gtk.Toolbar):
	def __init__(self, embed):
		gtk.Toolbar.__init__(self)
		self.embed = embed
		
		self.set_style(gtk.TOOLBAR_ICONS)
		
		self.back = gtk.ToolButton(gtk.STOCK_GO_BACK)
		self.back.connect("clicked", self.__go_back_cb)
		self.insert(self.back, -1)
		self.back.show()

		self.forward = gtk.ToolButton(gtk.STOCK_GO_FORWARD)
		self.forward.connect("clicked", self.__go_forward_cb)
		self.insert(self.forward, -1)
		self.forward.show()

		self.reload = gtk.ToolButton(gtk.STOCK_REFRESH)
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

		self.embed.connect("location", self.__location_changed)

	def _update_sensitivity(self):
		self.back.set_sensitive(self.embed.can_go_back())
		self.forward.set_sensitive(self.embed.can_go_forward())
		
	def __go_back_cb(self, button):
		self.embed.go_back()
	
	def __go_forward_cb(self, button):
		self.embed.go_forward()
		
	def __reload_cb(self, button):
		self.embed.reload()
		
	def __location_changed(self, embed):
		self._update_sensitivity()

	def __open_address_cb(self, address):
		self.embed.load_url(address)
		
class BrowserWindow(gtk.Window):
	def __init__(self, uri):
		gtk.Window.__init__(self)
		self.set_default_size(640, 480);

		vbox = gtk.VBox()

		self.embed = geckoembed.Embed()
		vbox.pack_start(self.embed)
		self.embed.show()
		self.embed.load_url(uri)
		
		nav_toolbar = NavigationToolbar(self.embed)
		vbox.pack_start(nav_toolbar, False)
		nav_toolbar.show()

		self.add(vbox)
		vbox.show()

class SearchWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
	
		self.set_default_size(640, 480);
		self.connect("delete-event", self.__delete_event);

		vbox = gtk.VBox()

		self.embed = geckoembed.Embed()
		self.embed.connect("open-address", self.__open_address);
		
		vbox.pack_start(self.embed)
		self.embed.show()

		address_toolbar = AddressToolbar()
		vbox.pack_start(address_toolbar, False)
		address_toolbar.show()
		
		self.add(vbox)
		vbox.show()

		self.embed.load_url("http://www.google.com")

	def __delete_event(self, widget, event, data=None):
		return True;

	def __open_address(self, embed, uri, data=None):
		if uri.startswith("http://www.google.com"):
			return False
		else:
			browser = BrowserWindow(uri)
			browser.show()
			return True

window = SearchWindow()
window.show()
gtk.main()
