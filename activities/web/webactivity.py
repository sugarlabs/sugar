from sugar.activity.Activity import Activity
from webbrowser import WebBrowser

_HOMEPAGE = 'http://www.google.com'

class WebActivity(Activity):
	def __init__(self):
		Activity.__init__(self)

		self._browser = WebBrowser()
		self.add(self._browser)
		self._browser.show()

		self._browser.load_url(_HOMEPAGE)
