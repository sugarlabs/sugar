# Copyright (C) 2013 Kalpa Welivitigoda
# Copyright (C) 2015-2016 Sam Parkinson
# Copyright (C) 2016 James Cameron <quozl@laptop.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

import gi
gi.require_version('WebKit', '3.0')
gi.require_version('SoupGNOME', '2.4')

from gi.repository import WebKit
from gi.repository import SoupGNOME

from sugar3 import env


def _get_current_language():
    locale = os.environ.get('LANG')
    return locale.split('.')[0].split('_')[0].lower()


class Browser():

    def __init__(self, toolbar):
        self._toolbar = toolbar

        session = WebKit.get_default_session()
        cookie_jar = SoupGNOME.CookieJarSqlite(
            filename=os.path.join(env.get_profile_path(),
                                  'social-help.cookies'),
            read_only=False)
        session.add_feature(cookie_jar)

        self._webview = WebKit.WebView()
        self._webview.set_full_content_zoom(True)
        self._webview.connect('resource-request-starting',
                              self.__resource_request_starting_cb)

        self._webview.connect('notify::uri', self.__load_changed_cb)
        toolbar.update_back_forward(False, False)
        toolbar.connect('back-clicked', self.__back_cb)
        toolbar.connect('forward-clicked', self.__forward_cb)
        self._webview.show()

    def __resource_request_starting_cb(self, webview, web_frame, web_resource,
                                       request, response):
        uri = web_resource.get_uri()
        if uri.startswith('file://') and uri.find('_images') > -1:
            if uri.find('/%s/_images/' % _get_current_language()) > -1:
                new_uri = uri.replace('/html/%s/_images/' %
                                      _get_current_language(),
                                      '/images/')
            else:
                new_uri = uri.replace('/html/_images/', '/images/')
            request.set_uri(new_uri)

    def __load_changed_cb(self, widget, event):
        self._toolbar.update_back_forward(self._webview.can_go_back(),
                                          self._webview.can_go_forward())

    def __back_cb(self, widget):
        self._webview.go_back()

    def __forward_cb(self, widget):
        self._webview.go_forward()

    def save_state(self):
        back_forward_list = self._webview.get_back_forward_list()
        items_list = self._items_history_as_list(back_forward_list)
        curr = back_forward_list.get_current_item()

        return ([item.get_uri() for item in items_list],
                items_list.index(curr))

    def load_state(self, state, url):
        if state is None:
            state = ([url], 0)
        history, index = state

        back_forward_list = self._webview.get_back_forward_list()
        back_forward_list.clear()
        for i, uri in enumerate(history):
            history_item = WebKit.WebHistoryItem.new_with_data(uri, '')
            back_forward_list.add_item(history_item)
            if i == index:
                self._webview.go_to_back_forward_item(history_item)

        self._toolbar.update_back_forward(self._webview.can_go_back(),
                                          self._webview.can_go_forward())

    def _items_history_as_list(self, history):
        back_items = []
        for n in reversed(range(1, history.get_back_length() + 1)):
            item = history.get_nth_item(n * -1)
            back_items.append(item)

        current_item = [history.get_current_item()]

        forward_items = []
        for n in range(1, history.get_forward_length() + 1):
            item = history.get_nth_item(n)
            forward_items.append(item)

        all_items = back_items + current_item + forward_items
        return all_items

    def get_widget(self):
        return self._webview

    def get_local_method(self):
        return 'file://'
