import dbus
import geckoembed
import pygtk
pygtk.require('2.0')
import gtk
import gobject

import sugar.env

from sugar.browser.BrowserActivity import BrowserActivity
from sugar.presence import Service

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

	def _start_browser_cb(self, browser, service):
		browser.connect_to_shell(service)

	@dbus.service.method('com.redhat.Sugar.BrowserShell')
	def open_browser(self, uri, serialized_service=None):
		service = None
		if serialized_service is not None:
			serivce = Service.deserialize(serialized_service)
		browser = BrowserActivity(uri)
		self.__browsers.append(browser)
		gobject.idle_add(self._start_browser_cb, browser, service)

	@dbus.service.method('com.redhat.Sugar.BrowserShell')
	def open_browser_from_service_foobar(self, uri, serialized_service):
		serivce = Service.deserialize(serialized_service)
		browser = BrowserActivity(uri)
		self.__browsers.append(browser)
		gobject.idle_add(self._start_browser_cb, browser, service)
