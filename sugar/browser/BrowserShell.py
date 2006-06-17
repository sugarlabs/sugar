import dbus
import geckoembed
import pygtk
pygtk.require('2.0')
import gtk
import gobject

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

	def _start_browser_cb(self, browser, activity_id):
		if activity_id:
			browser.connect_to_shell(activity_id)
		else:
			browser.connect_to_shell()

	@dbus.service.method('com.redhat.Sugar.BrowserShell')
	def open_browser(self, uri):
		browser = BrowserActivity(uri)
		self.__browsers.append(browser)
		gobject.idle_add(self._start_browser_cb, browser, None)

	@dbus.service.method('com.redhat.Sugar.BrowserShell')
	def open_browser_with_id(self, uri, activity_id):
		browser = BrowserActivity(uri)
		self.__browsers.append(browser)
		gobject.idle_add(self._start_browser_cb, browser, activity_id)
