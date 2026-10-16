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

try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
    WEBKIT_VER = 6
except (ValueError, ImportError):
    WebKit = None
    WEBKIT_VER = 6

from gi.repository import Gio

from sugar4 import env


def _get_current_language():
    locale = os.environ.get('LANG', 'en_US.UTF-8')
    return locale.split('.')[0].split('_')[0].lower()


class Browser():

    def __init__(self, toolbar):
        self._toolbar = toolbar

        if WebKit is None:
            from gi.repository import Gtk
            self._webview = Gtk.Label(label="WebKit 6.0 is not installed. Help cannot be displayed.")
            self._webview.set_visible(True)
            return

        if WEBKIT_VER == 6:
            context = WebKit.WebContext.get_default()
            cookie_manager = context.get_cookie_manager()
            if hasattr(cookie_manager, 'set_persistent_storage'):
                cookie_manager.set_persistent_storage(
                    os.path.join(env.get_profile_path(), 'social-help.cookies'),
                    WebKit.CookiePersistentStorage.SQLITE)

            self._webview = WebKit.WebView()
            self._webview.get_context().register_uri_scheme(
                'help', self.__app_scheme_cb, None, None)
        else:
            context = WebKit.WebContext.get_default()
            cookie_manager = context.get_cookie_manager()
            cookie_manager.set_persistent_storage(
                os.path.join(env.get_profile_path(), 'social-help.cookies'),
                WebKit.CookiePersistentStorage.SQLITE)

            self._webview = WebKit.WebView()
            self._webview.get_context().register_uri_scheme(
                'help', self.__app_scheme_cb, None)

        self._webview.connect('load-changed', self.__load_changed_cb)
        toolbar.update_back_forward(False, False)
        toolbar.connect('back-clicked', self.__back_cb)
        toolbar.connect('forward-clicked', self.__forward_cb)
        self._webview.set_visible(True)

    def __app_scheme_cb(self, request, user_data=None, *args):
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
        if WebKit is None: return
        self._toolbar.update_back_forward(self._webview.can_go_back(),
                                          self._webview.can_go_forward())

    def __back_cb(self, widget):
        if WebKit is None: return
        self._webview.go_back()

    def __forward_cb(self, widget):
        if WebKit is None: return
        self._webview.go_forward()

    def save_state(self):
        # WebKit 6.0 removed get_session_state()/restore_session_state().
        # Fall back to simple URL-based state tracking.
        if WebKit is None:
            return None
        uri = self._webview.get_uri()
        return uri if uri else None

    def load_state(self, state, url):
        # WebKit 6.0 removed restore_session_state().
        # state is now just a URI string (or None).
        if WebKit is None:
            return
        target_url = state if state is not None else url
        if target_url:
            self._webview.load_uri(target_url)

        self._toolbar.update_back_forward(self._webview.can_go_back(),
                                          self._webview.can_go_forward())

    def get_widget(self):
        return self._webview

    def get_local_method(self):
        return 'help://'
