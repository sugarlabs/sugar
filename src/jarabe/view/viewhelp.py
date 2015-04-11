# Copyright (C) 2013 Kalpa Welivitigoda
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
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import WebKit2
from gi.repository import Gio
from gi.repository import GdkX11

from sugar3 import env
from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.bundle.activitybundle import get_bundle_instance
from jarabe.model import shell


_logger = logging.getLogger('ViewHelp')


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
        return None
    help_content_link = os.path.join(activity_path, 'helplink.json')
    if not os.path.exists(help_content_link):
        _logger.error('Help activity not installed or json file not found')
        return None

    links = None
    try:
        with open(help_content_link) as json_file:
            links = json.load(json_file)
    except IOError:
        _logger.error('helplink.json malformed, or can\'t be read')

    if links:
        if link_id in links.keys():
            return (links[link_id], title)

    return None


def setup_view_help(activity):
    if shell.get_model().has_modal():
        return
    # check whether the execution was from an activity
    bundle_path = activity.get_bundle_path()
    if bundle_path is None:
        window_xid = 0
    else:
        # get activity name and window id
        window_xid = activity.get_xid()

    url_and_title = get_help_url_and_title(activity)

    if url_and_title:
        viewhelp = ViewHelp(url_and_title[1], url_and_title[0], window_xid)
        activity.push_shell_window(viewhelp)
        viewhelp.connect('hide', activity.pop_shell_window)
        viewhelp.show()
    else:
        _logger.error('Help content is not available for the activity')


class ViewHelp(Gtk.Window):
    parent_window_xid = None

    def __init__(self, title, help_file, window_xid):
        self.parent_window_xid = window_xid

        Gtk.Window.__init__(self)
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(box)
        box.show()

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)

        self.connect('realize', self.__realize_cb)

        toolbar = Toolbar(title)
        box.pack_start(toolbar, False, False, 0)
        toolbar.show()
        toolbar.connect('stop-clicked', self.__stop_clicked_cb)

        webview = WebKit2.WebView()
        box.pack_start(webview, True, True, 0)
        webview.show()

        context = WebKit2.WebContext.get_default()
        context.register_uri_scheme('help', self.__app_scheme_cb, None)

        language = self._get_current_language()
        view_file = self._get_help_file(language, help_file)
        webview.load_uri('help://' + view_file)

    def __app_scheme_cb(self, request, user_data):
        uri = request.get_path()
        if uri.find('_images') > -1:
            if uri.find('/%s/_images/' % self._get_current_language()) > -1:
                uri = uri.replace('/html/%s/_images/' %
                                  self._get_current_language, '/images/')
            else:
                uri = uri.replace('/html/_images/', '/images/')
        request.finish(Gio.File.new_for_path(uri).read(None),
                       -1, Gio.content_type_guess(uri, None)[0])

    def __stop_clicked_cb(self, widget):
        self.destroy()
        shell.get_model().pop_modal()

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)
        display = Gdk.Display.get_default()
        parent = GdkX11.X11Window.foreign_new_for_display(
            display, self.parent_window_xid)
        window.set_transient_for(parent)
        shell.get_model().push_modal()

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


class Toolbar(Gtk.Toolbar):

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, activity_name):
        Gtk.Toolbar.__init__(self)

        title = 'Help: ' + activity_name

        self._add_separator(False)

        label = Gtk.Label()
        label.set_markup('<b>%s</b>' % title)
        label.set_alignment(0, 0.5)
        self._add_widget(label)

        self._add_separator(True)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Close'))
        stop.connect('clicked', self.__stop_clicked_cb)
        self.insert(stop, -1)
        stop.show()

    def __stop_clicked_cb(self, widget):
        self.emit('stop-clicked')

    def _add_widget(self, widget):
        tool_item = Gtk.ToolItem()
        tool_item.add(widget)
        widget.show()
        self.insert(tool_item, -1)
        tool_item.show()

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.insert(separator, -1)
        separator.show()
