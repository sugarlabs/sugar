#!/usr/bin/env python
import sys

from xml.sax import saxutils

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk

import geckoembed

from sugar.session.LogWriter import LogWriter
from sugar.shell import activity
from sugar.p2p.Group import LocalGroup
from sugar.browser.NotificationBar import NotificationBar
import sugar.env

class AddressToolbar(gtk.Toolbar):
	def __init__(self):
		gtk.Toolbar.__init__(self)

		address_item = AddressItem(self.__open_address_cb)		
		self.insert(address_item, 0)
		address_item.show()

	def __open_address_cb(self, address):
		BrowserShell.get_instance().open_browser(address)

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
			image.set_from_file(sugar.env.get_data_file('unfold.png'))
			self.button.set_image(image)
			image.show()

			self.entry.hide()
		else:
			image = gtk.Image()
			image.set_from_file(sugar.env.get_data_file('fold.png'))
			self.button.set_image(image)
			image.show()

			self.entry.show()
			self.entry.grab_focus()
	
	def get_folded(self):
		return self.folded
	
	def set_folded(self, folded):
		self.folded = folded
		self._update_folded_state()		
	
	def __button_clicked_cb(self, button):
		self.set_folded(not self.get_folded())

	def __activate_cb(self, entry):
		self.callback(entry.get_text())
		self.set_folded(True)

class NavigationToolbar(gtk.Toolbar):
	def __init__(self, browser):
		gtk.Toolbar.__init__(self)
		self._browser = browser
		self._embed = self._browser.get_embed()
		
		self.set_style(gtk.TOOLBAR_BOTH_HORIZ)
		
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

		share = gtk.ToolButton(None, "Share")
		share.set_icon_name('stock_shared-by-me')
		share.set_is_important(True)
		share.connect("clicked", self.__share_cb)
		self.insert(share, -1)
		share.show()

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

	def __share_cb(self, button):
		self._browser.share()

	def __location_changed(self, embed):
		self._update_sensitivity()

	def __open_address_cb(self, address):
		self._embed.load_address(address)

class BrowserActivity(activity.Activity):
	SOLO = 1
	FOLLOWING = 2
	LEADING = 3

	def __init__(self, group, uri):
		activity.Activity.__init__(self)

		self.uri = uri
		self._group = group
		self._mode = BrowserActivity.SOLO

	def _update_shared_location(self):
		address = self.embed.get_address()
		self._model.set_value('address', address)
		title = self.embed.get_title()
		self._model.set_value('title', title)
		
	def __notif_bar_action_cb(self, bar, action_id):
		print action_id
		if action_id == 'set_shared_location':
			self._update_shared_location()
		elif action_id == 'goto_shared_location':
			address = self._model.get_value("address")
			print address
			self.embed.load_address(address)
			self._notif_bar.hide()

	def set_mode(self, mode):
		self._mode = mode
		if mode == BrowserActivity.LEADING:
			self._notif_bar.set_text('Share this page with the group.')
			self._notif_bar.set_action('set_shared_location', 'Share')
			self._notif_bar.set_icon('stock_shared-by-me')
			self._notif_bar.show()

	def _setup_shared(self, uri):
		self._model = self._group.get_store().get_model(uri)
		if self._model:
			self.set_mode(BrowserActivity.FOLLOWING)
			self._model.add_listener(self.__shared_location_changed_cb)
	
	def activity_on_connected_to_shell(self):
		self.activity_set_ellipsize_tab(True)
		self.activity_set_can_close(True)
		self.activity_set_tab_text("Web Page")
		self.activity_set_tab_icon_name("web-browser")
		self.activity_show_icon(True)

		vbox = gtk.VBox()

		self._notif_bar = NotificationBar()
		vbox.pack_start(self._notif_bar, False)
		self._notif_bar.connect('action', self.__notif_bar_action_cb)

		self.embed = geckoembed.Embed()
		self.embed.connect("title", self.__title_cb)
		vbox.pack_start(self.embed)
		
		self.embed.show()
		self.embed.load_address(self.uri)
		
		nav_toolbar = NavigationToolbar(self)
		vbox.pack_start(nav_toolbar, False)
		nav_toolbar.show()

		plug = self.activity_get_gtk_plug()		
		plug.add(vbox)
		plug.show()

		vbox.show()
		
		self._setup_shared(self.uri)
	
	def get_embed(self):
		return self.embed
	
	def share(self):
		address = self.embed.get_address()
		self._model = self._group.get_store().create_model(address)
		self._model.set_value('owner', self._group.get_owner().get_nick_name())
		self._update_shared_location()
		self.set_mode(BrowserActivity.LEADING)
	
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Chat', '/com/redhat/Sugar/Chat')
		chat_shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.ChatShell')
		
		escaped_title = saxutils.escape(self.embed.get_title())
		escaped_address = saxutils.escape(address)
		chat_shell.send_text_message('<richtext><link href="' + escaped_address +
								'">' + escaped_title + '</link></richtext>')
	
	def __title_cb(self, embed):
		self.activity_set_tab_text(embed.get_title())

	def __shared_location_changed_cb(self, model, key):
		self.activity_set_has_changes(True)
		self._notify_shared_location_change()

	def _notify_shared_location_change(self):
		owner = self._model.get_value('owner')
		title = self._model.get_value('title')
		
		text = '<b>' + owner + '</b> is reading <i>' + title + '</i>'
		self._notif_bar.set_text(text)
		self._notif_bar.set_action('goto_shared_location', 'Go There')
		self._notif_bar.set_icon('stock_right')
		self._notif_bar.show()

	def activity_on_close_from_user(self):
		self.activity_shutdown()

class WebActivity(activity.Activity):
	def __init__(self):
		activity.Activity.__init__(self)
	
	def activity_on_connected_to_shell(self):
		self.activity_set_tab_text("Web")
		self.activity_set_tab_icon_name("web-browser")
		self.activity_show_icon(True)

		vbox = gtk.VBox()
			
		self.embed = geckoembed.Embed()
		self.embed.connect("open-address", self.__open_address);		
		vbox.pack_start(self.embed)
		self.embed.show()

		address_toolbar = AddressToolbar()
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
			BrowserShell.get_instance().open_browser(uri)
			return True

	def activity_on_disconnected_from_shell(self):
		gtk.main_quit()

class BrowserShell(dbus.service.Object):
	instance = None

	def get_instance():
		if not BrowserShell.instance:
			BrowserShell.instance = BrowserShell()
		return BrowserShell.instance
		
	get_instance = staticmethod(get_instance)

	def __init__(self):
		geckoembed.set_profile_path(sugar.env.get_user_dir())

		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Browser', bus=session_bus)
		object_path = '/com/redhat/Sugar/Browser'

		dbus.service.Object.__init__(self, bus_name, object_path)

		self.__browsers = []
		self._group = LocalGroup()

	def open_web_activity(self):
		web_activity = WebActivity()
		web_activity.activity_connect_to_shell()

	@dbus.service.method('com.redhat.Sugar.BrowserShell')
	def get_links(self):
		links = []
		for browser in self.__browsers:
			embed = browser.get_embed()
			link = {}
			link['title'] = embed.get_title()
			link['address'] = embed.get_address()
			links.append(link)
		return links

	@dbus.service.method('com.redhat.Sugar.BrowserShell')
	def open_browser(self, uri):
		browser = BrowserActivity(self._group, uri)
		self.__browsers.append(browser)
		browser.activity_connect_to_shell()

log_writer = LogWriter("Web")
log_writer.start()

gtk.rc_parse(sugar.env.get_data_file('browser.rc'))

BrowserShell.get_instance().open_web_activity()

gtk.main()
