import dbus
import geckoembed
import pygtk
pygtk.require('2.0')
import gtk

import sugar.env

from sugar.browser.BrowserActivity import BrowserActivity

class BrowserShell(dbus.service.Object):
	def __init__(self, bus_name, object_path = '/com/redhat/Sugar/Browser'):
		dbus.service.Object.__init__(self, bus_name, object_path)
		
		geckoembed.set_profile_path(sugar.env.get_user_dir())
		self.__browsers = []

	def start(self):
		gtk.main()

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
		browser = BrowserActivity(None, uri)
		self.__browsers.append(browser)
		browser.connect_to_shell()
