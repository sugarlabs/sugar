import gtk

from sugar.activity.Activity import Activity
from webbrowser import WebBrowser
from toolbar import Toolbar

_HOMEPAGE = 'http://www.google.com'

class WebActivity(Activity):
	def __init__(self):
		Activity.__init__(self)

		vbox = gtk.VBox()

		self._browser = WebBrowser()

		toolbar = Toolbar(self._browser)
		vbox.pack_start(toolbar, False)
		toolbar.show()

		vbox.pack_start(self._browser)
		self._browser.show()

		self.add(vbox)
		vbox.show()

		self._browser.load_url(_HOMEPAGE)
