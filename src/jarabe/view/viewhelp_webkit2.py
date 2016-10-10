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
gi.require_version('WebKit2', '4.0')

from gi.repository import WebKit2
from gi.repository import Gio

from sugar3 import env


def _get_current_language():
    locale = os.environ.get('LANG')
    return locale.split('.')[0].split('_')[0].lower()


class Browser():

    def __init__(self, toolbar):
        self._toolbar = toolbar

        context = WebKit2.WebContext.get_default()
        cookie_manager = context.get_cookie_manager()
        cookie_manager.set_persistent_storage(
            os.path.join(env.get_profile_path(), 'social-help.cookies'),
            WebKit2.CookiePersistentStorage.SQLITE)

        self._webview = WebKit2.WebView()
        self._webview.get_context().register_uri_scheme(
            'help', self.__app_scheme_cb, None)

        self._webview.connect('load-changed', self.__load_changed_cb)
        toolbar.update_back_forward(False, False)
        toolbar.connect('back-clicked', self.__back_cb)
        toolbar.connect('forward-clicked', self.__forward_cb)
        self._webview.show()

    def __app_scheme_cb(self, request, user_data):
        path = request.get_path()
        if path.find('_images') > -1:
            if path.find('/%s/_images/' % _get_current_language()) > -1:
                path = path.replace('/html/%s/_images/' %
                                    _get_current_language(),
                                    '/images/')
            else:
                path = path.replace('/html/_images/', '/images/')

        request.finish(Gio.File.new_for_path(path).read(None),
                       -1, Gio.content_type_guess(path, None)[0])

    def __load_changed_cb(self, widget, event):
        self._toolbar.update_back_forward(self._webview.can_go_back(),
                                          self._webview.can_go_forward())

    def __back_cb(self, widget):
        self._webview.go_back()

    def __forward_cb(self, widget):
        self._webview.go_forward()

    def save_state(self):
        return self._webview.get_session_state()

    def load_state(self, state, url):
        if state is None:
            self._webview.load_uri(url)
        else:
            self._webview.restore_session_state(state)
            # this is what epiphany does:
            # https://github.com/GNOME/epiphany/blob/
            # 04e7811c32ba8a2c980a77aac1316b77f0969057/src/ephy-session.c#L280
            bf_list = self._webview.get_back_forward_list()
            item = bf_list.get_current_item()
            if item is not None:
                self._webview.go_to_back_forward_list_item(item)

        self._toolbar.update_back_forward(self._webview.can_go_back(),
                                          self._webview.can_go_forward())

    def get_widget(self):
        return self._webview

    def get_local_method(self):
        return 'help://'
