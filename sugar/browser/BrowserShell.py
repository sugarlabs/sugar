import dbus
import geckoembed
import threading
import gobject

import sugar.env

from sugar.browser.WebActivity import WebActivity
from sugar.browser.BrowserActivity import BrowserActivity

class BrowserShell(dbus.service.Object):
	instance = None
	_lock = threading.Lock()

	def get_instance():
		BrowserShell._lock.acquire()
		if not BrowserShell.instance:
			BrowserShell.instance = BrowserShell()
		BrowserShell._lock.release()
		return BrowserShell.instance
	get_instance = staticmethod(get_instance)

	def __init__(self):
		geckoembed.set_profile_path(sugar.env.get_user_dir())

		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Browser', bus=session_bus)
		object_path = '/com/redhat/Sugar/Browser'

		dbus.service.Object.__init__(self, bus_name, object_path)

		self.__browsers = []

	def open_web_activity(self):
		web_activity = WebActivity(self)
		web_activity.connect_to_shell()

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
