import dbus
import pygtk
pygtk.require('2.0')
import gtk
import geckoembed
import urllib

from sugar.shell import activity
from sugar.browser import NotificationBar
from sugar.browser import NavigationToolbar
from sugar.presence.PresenceService import PresenceService
from sugar.p2p.model.LocalModel import LocalModel
from sugar.p2p.model.RemoteModel import RemoteModel

_BROWSER_ACTIVITY_TYPE = "_web_olpc._udp"
_SERVICE_URI_TAG = "URI"
_SERVICE_TITLE_TAG = "Title"

class BrowserActivity(activity.Activity):
	SOLO = 1
	FOLLOWING = 2
	LEADING = 3

	def __init__(self, uri):
		activity.Activity.__init__(self)
		self.uri = uri
		self._mode = BrowserActivity.SOLO
		self._pservice = PresenceService.get_instance()
		self._pservice.start()
		self._pservice.track_service_type(_BROWSER_ACTIVITY_TYPE)
		self._share_service = None
		self._model = None
	
	def get_default_type(self):
		return _BROWSER_ACTIVITY_TYPE
	
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

	def _setup_shared(self, service, no):
		self._model = RemoteModel(service, notification_service)
	
	def on_connected_to_shell(self):
		self.set_ellipsize_tab(True)
		self.set_can_close(True)
		self.set_tab_text("Web Page")
		self.set_tab_icon(name="web-browser")
		self.set_show_tab_icon(True)

		vbox = gtk.VBox()

		self._notif_bar = NotificationBar.NotificationBar()
		vbox.pack_start(self._notif_bar, False)
		self._notif_bar.connect('action', self.__notif_bar_action_cb)

		self.embed = geckoembed.Embed()
		self.embed.connect("title", self.__title_cb)
		vbox.pack_start(self.embed)
		
		self.embed.show()
		self.embed.load_address(self.uri)
		
		nav_toolbar = NavigationToolbar.NavigationToolbar(self)
		vbox.pack_start(nav_toolbar, False)
		nav_toolbar.show()

		plug = self.gtk_plug()		
		plug.add(vbox)
		plug.show()

		vbox.show()
		
		self._setup_shared(self.uri)
	
	def get_embed(self):
		return self.embed
	
	def publish(self):
		escaped_title = urllib.quote(self.embed.get_title())
		escaped_url = urllib.quote(self.embed.get_address())

		# Publish ourselves on the network
		properties = {_SERVICE_URI_TAG: escaped_url, _SERVICE_TITLE_TAG: escaped_title}
		self._share_service = self._pservice.share_activity(self,
				stype=_BROWSER_ACTIVITY_TYPE, properties=properties)

		# Create our activity-specific browser sharing service
		self._model = LocalModel(self, self._pservice, self._share_service)
		self._model.set_value('owner', self._pservice.get_owner().get_nick_name())
		self._update_shared_location()
		
		self.set_mode(BrowserActivity.LEADING)

	def __title_cb(self, embed):
		self.set_tab_text(embed.get_title())

	def __shared_location_changed_cb(self, model, key):
		self.set_has_changes(True)
		self._notify_shared_location_change()

	def _notify_shared_location_change(self):
		owner = self._model.get_value('owner')
		title = self._model.get_value('title')
		
		text = '<b>' + owner + '</b> is reading <i>' + title + '</i>'
		self._notif_bar.set_text(text)
		self._notif_bar.set_action('goto_shared_location', 'Go There')
		self._notif_bar.set_icon('stock_right')
		self._notif_bar.show()
