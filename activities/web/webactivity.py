from gettext import gettext as _
import gtk
import gtkmozembed

from sugar.activity.Activity import Activity
from sugar import env
from webbrowser import WebBrowser
from toolbar import Toolbar

_HOMEPAGE = 'http://www.google.com'

class WebActivity(Activity):
	def __init__(self):
		Activity.__init__(self)

		self.set_title(_('Web Activity'))

		vbox = gtk.VBox()

		self._browser = WebBrowser()
		self._browser.connect('notify::title', self._title_changed_cb)

		toolbar = Toolbar(self._browser)
		vbox.pack_start(toolbar, False)
		toolbar.show()

		vbox.pack_start(self._browser)
		self._browser.show()

		self.add(vbox)
		vbox.show()

		self._browser.load_url(_HOMEPAGE)

	def join(self, activity_ps):
		Activity.join(self, activity_ps)

		url = self._service.get_published_value('URL')
		if url:
			self._browser.load_url(url)

	def share(self):
		Activity.share(self)

		url = self._browser.get_location()
		if url:
			self._service.set_published_value('URL', url)

	def _title_changed_cb(self, embed, pspec):
		self.set_title(embed.props.title)

def start():
	gtkmozembed.set_profile_path(env.get_profile_path(), 'gecko')
