# Copyright (C) 2013 Kalpa Welivitigoda
# Copyright (C) 2015 Sam Parkinson
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
import logging
import os
import json

from gi.repository import Gtk
from gi.repository import WebKit
from gi.repository import SoupGNOME
from gi.repository import Gio

from sugar3 import env
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.icon import get_icon_file_name
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.bundle.activitybundle import get_bundle_instance
from sugar3.graphics.popwindow import PopWindow
from jarabe.model import shell


_logger = logging.getLogger('ViewHelp')

_MODE_HELP = 0
_MODE_SOCIAL_HELP = 1

_LOADING_ICON = 'toolbar-social-help-animated'


def _get_help_activity_path():
    path = os.path.join(env.get_user_activities_path(), 'Help.activity')
    if os.path.exists(path):
        return path
    # if was installed by a distro package
    path = '/usr/share/sugar/activities/Help.activity'
    if os.path.exists(path):
        return path
    return None


def get_help_url_and_title(activity):
    """
    Returns the help document name and the title to display,
    or None if not content is available.
    """
    bundle_path = activity.get_bundle_path()
    if bundle_path is None:
        shell_model = shell.get_model()
        zoom_level = shell_model.zoom_level
        if zoom_level == shell_model.ZOOM_MESH:
            title = _('Mesh')
            link_id = 'mesh_view'
        elif zoom_level == shell_model.ZOOM_GROUP:
            title = _('Group')
            link_id = 'group_view'
        elif zoom_level == shell_model.ZOOM_HOME:
            title = _('Home')
            link_id = 'home_view'
        else:
            title = _('Journal')
            link_id = 'org.laptop.JournalActivity'
    else:
        # get activity name and window id
        activity_bundle = get_bundle_instance(bundle_path)
        title = activity_bundle.get_name()
        link_id = activity_bundle.get_bundle_id()

    # get the help file name for the activity
    activity_path = _get_help_activity_path()
    if activity_path is None:
        return None, title
    help_content_link = os.path.join(activity_path, 'helplink.json')
    if not os.path.exists(help_content_link):
        _logger.error('Help activity not installed or json file not found')
        return None, title

    links = None
    try:
        with open(help_content_link) as json_file:
            links = json.load(json_file)
    except IOError:
        _logger.error('helplink.json malformed, or can\'t be read')

    if links:
        if link_id in links.keys():
            return links[link_id], title

    return None, title


def get_social_help_server():
    settings = Gio.Settings('org.sugarlabs.collaboration')
    return settings.get_string('social-help-server')


def should_show_view_help(activity):
    url, title = get_help_url_and_title(activity)
    return bool(get_social_help_server()) or url is not None


def setup_view_help(activity):
    if activity.has_shell_window():
        return
    # check whether the execution was from an activity
    bundle_path = activity.get_bundle_path()
    if bundle_path is None:
        window_xid = 0
    else:
        # get activity name and window id
        window_xid = activity.get_xid()

    if not should_show_view_help(activity):
        return

    if shell.get_model().has_modal():
        return

    viewhelp = ViewHelp(activity, window_xid)
    activity.push_shell_window(viewhelp)
    viewhelp.connect('hide', activity.pop_shell_window)
    viewhelp.show()


class ViewHelp(PopWindow):
    parent_window_xid = None

    def __init__(self, activity, window_xid):
        self.parent_window_xid = window_xid

        url, title = get_help_url_and_title(activity)
        has_local_help = url is not None
        self._mode = _MODE_HELP if has_local_help else _MODE_SOCIAL_HELP

        PopWindow.__init__(self, window_xid=window_xid)
        self._parent_window_xid = window_xid

        self.build_toolbar(title, has_local_help)
        session = WebKit.get_default_session()
        cookie_jar = SoupGNOME.CookieJarSqlite(
            filename=os.path.join(env.get_profile_path(),
                                  'social-help.cookies'),
            read_only=False)
        session.add_feature(cookie_jar)

        self._webview = WebKit.WebView()
        self._webview.set_full_content_zoom(True)
        self._webview.connect('resource-request-starting',
                              self._resource_request_starting_cb)

        self._scroll_window = Gtk.ScrolledWindow()
        self._scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                       Gtk.PolicyType.AUTOMATIC)

        self._scroll_window.add(self._webview)
        self._vbox.pack_start(self._scroll_window, True, True, 0)
        self._scroll_window.show()
        self._webview.show()
        self.show()

        language = self._get_current_language()
        if has_local_help:
            self._help_url = 'file://' + self._get_help_file(language, url)
        self._social_help_url = '{}/goto/{}'.format(
            get_social_help_server(), activity.get_bundle_id())

        self._webview.connect(
            'notify::load-status', self.__load_status_changed_cb)
        self._load_mode(self._mode)

    def build_toolbar(self, activity_name, has_local_help):
        self._add_separator(False)

        if has_local_help and get_social_help_server():
            help_button = RadioToolButton()
            icon = Icon(icon_name='toolbar-help',
                        pixel_size=style.STANDARD_ICON_SIZE,
                        fill_color=style.COLOR_TRANSPARENT.get_svg(),
                        stroke_color=style.COLOR_WHITE.get_svg())
            help_button.set_icon_widget(icon)
            icon.show()
            help_button.props.tooltip = _('Help Manual')
            help_button.connect('toggled', self.__button_toggled_cb,
                                _MODE_HELP)
            self.get_title_box().insert(help_button, 0)
            help_button.show()
            self._add_separator(False)

            social_help_button = RadioToolButton()
            icon = Icon(icon_name='toolbar-social-help',
                        pixel_size=style.STANDARD_ICON_SIZE,
                        fill_color=style.COLOR_TRANSPARENT.get_svg(),
                        stroke_color=style.COLOR_WHITE.get_svg())
            social_help_button.set_icon_widget(icon)
            icon.show()
            social_help_button.props.tooltip = _('Social Help')
            social_help_button.props.group = help_button
            social_help_button.connect('toggled', self.__button_toggled_cb,
                                       _MODE_SOCIAL_HELP)
            self.get_title_box().insert(social_help_button, 0)
            social_help_button.show()
            self._add_separator(False)

        title = _('Help: %s') % activity_name
        self.get_title_box().props.title = title

        self._add_separator(False)

    def __button_toggled_cb(self, button, mode):
        if button.props.active:
            self.__mode_changed_cb(mode)

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.get_title_box().insert(separator, 0)
        separator.show()

    def _resource_request_starting_cb(self, webview, web_frame, web_resource,
                                      request, response):
        uri = web_resource.get_uri()
        if uri.startswith('file://') and uri.find('_images') > -1:
            if uri.find('/%s/_images/' % self._get_current_language()) > -1:
                new_uri = uri.replace('/html/%s/_images/' %
                                      self._get_current_language(),
                                      '/images/')
            else:
                new_uri = uri.replace('/html/_images/', '/images/')
            request.set_uri(new_uri)

    def __stop_clicked_cb(self, widget):
        self.destroy()

    def __mode_changed_cb(self, mode):
        if self._mode == _MODE_HELP:
            self._help_url = self._webview.props.uri
        else:
            self._social_help_url = self._webview.props.uri

        self._mode = mode
        self._load_mode(self._mode)

    def _load_mode(self, mode):
        if mode == _MODE_HELP:
            self._webview.load_uri(self._help_url)
        else:
            # Loading any content for the social help page can take a
            # very long time (eg. the site is behind a redirector).
            # Loading the animation forces webkit to re-render the
            # page instead of keeping the previous page (so the user
            # sees that it is loading)
            path = get_icon_file_name(_LOADING_ICON)
            if path:
                self._webview.load_uri('file://' + path)
                # Social help is loaded after the icon is loaded
            else:
                self._webview.load_uri(self._social_help_url)

    def __load_status_changed_cb(self, *args):
        if self._webview.props.load_status == WebKit.LoadStatus.FINISHED \
           and _LOADING_ICON in self._webview.props.uri:
            self._webview.load_uri(self._social_help_url)

    def _get_current_language(self):
        locale = os.environ.get('LANG')
        return locale.split('.')[0].split('_')[0].lower()

    def _get_help_file(self, language, help_file):
        activity_path = _get_help_activity_path()
        # check if exist a page for the language selected
        # if not, use the default page
        path = os.path.join(activity_path, 'html', language, help_file)
        if not os.path.isfile(path):
            path = os.path.join(activity_path, 'html', help_file)

        return path
