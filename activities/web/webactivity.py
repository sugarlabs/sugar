# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _
import gtk
import gtkmozembed
import logging

import _sugar
from sugar.activity import ActivityFactory
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
	def __init__(self, browser=None):
		Activity.__init__(self)

		logging.debug('Starting the web activity')

		self.set_title(_('Web Activity'))

		vbox = gtk.VBox()

		if browser:
			self._browser = browser
		else:
			self._browser = WebBrowser()
		self._browser.connect('notify::title', self._title_changed_cb)

		self._links_model = LinksModel()
		links_view = LinksView(self._links_model, self._browser)

		self._toolbar = Toolbar(self._browser)
		vbox.pack_start(self._toolbar, False)
		self._toolbar.show()

		hbox = gtk.HBox()

		hbox.pack_start(links_view, False)
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

	gtkmozembed.push_startup()
	if not _sugar.startup_browser():
		raise "Error when initializising the web activity."

	style.load_stylesheet(web.stylesheet)
	
	chandler = _sugar.get_browser_chandler()
	chandler.connect('handle-content', handle_content_cb)

def stop():
	gtkmozembed.pop_startup()

def handle_content_cb(chandler, url, mimeType, tmpFileName):
	activity = ActivityFactory.create("org.laptop.sugar.Xbook")
	activity.execute("open_document", [tmpFileName])
