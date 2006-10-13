from gettext import gettext as _
import gtk
import gtkmozembed

from sugar.activity.Activity import Activity
from sugar import env
from sugar.graphics import style
import web.stylesheet
from webbrowser import WebBrowser
from toolbar import Toolbar
from linksmodel import LinksModel
from linksview import LinksView
from linkscontroller import LinksController

_HOMEPAGE = 'http://www.google.com'

class WebActivity(Activity):
	def __init__(self):
		Activity.__init__(self)

		self.set_title(_('Web Activity'))

		vbox = gtk.VBox()

		self._browser = WebBrowser()
		self._browser.connect('notify::title', self._title_changed_cb)

		self._links_model = LinksModel()
		links_view = LinksView(self._links_model, self._browser)

		self._toolbar = Toolbar(self._browser)
		vbox.pack_start(self._toolbar, False)
		self._toolbar.show()

		hbox = gtk.HBox()

		hbox.pack_start(links_view, False)
		links_view.show()
		
		hbox.pack_start(self._browser)
		self._browser.show()

		vbox.pack_start(hbox)
		hbox.show()

		self.add(vbox)
		vbox.show()

		self._browser.load_url(_HOMEPAGE)

	def _setup_links_controller(self):
		links_controller = LinksController(self._service, self._links_model)
		self._toolbar.set_links_controller(links_controller)

	def join(self, activity_ps):
		Activity.join(self, activity_ps)

		self._setup_links_controller()

		url = self._service.get_published_value('URL')
		if url:
			self._browser.load_url(url)

	def share(self):
		Activity.share(self)

		self._setup_links_controller()

		url = self._browser.get_location()
		if url:
			self._service.set_published_value('URL', url)

	def _title_changed_cb(self, embed, pspec):
		self.set_title(embed.props.title)

def start():
	gtkmozembed.set_profile_path(env.get_profile_path(), 'gecko')
	style.load_stylesheet(web.stylesheet)
