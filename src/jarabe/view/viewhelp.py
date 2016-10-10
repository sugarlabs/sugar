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

from gettext import gettext as _
import logging
import os
import json

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import Gio

from sugar3 import env
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.bundle.activitybundle import get_bundle_instance
from jarabe.model import shell


try:
    olpc_build = file('/boot/olpc_build', 'r').readline()
except:
    olpc_build = ''

if olpc_build.startswith('13'):
    from jarabe.view.viewhelp_webkit1 import Browser
else:
    from jarabe.view.viewhelp_webkit2 import Browser


_logger = logging.getLogger('ViewHelp')

_MODE_HELP = 0
_MODE_SOCIAL_HELP = 1

_LOADING_ICON = 'toolbar-social-help-animated'


def _get_current_language():
    locale = os.environ.get('LANG')
    return locale.split('.')[0].split('_')[0].lower()


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


class ViewHelp(Gtk.Window):
    parent_window_xid = None

    def __init__(self, activity, window_xid):
        self.parent_window_xid = window_xid

        url, title = get_help_url_and_title(activity)
        has_local_help = url is not None
        self._mode = _MODE_HELP if has_local_help else _MODE_SOCIAL_HELP

        Gtk.Window.__init__(self)
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(box)
        box.show()

        self.set_modal(True)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)

        self.connect('realize', self.__realize_cb)
        self.connect('hide', self.__hide_cb)
        self.connect('key-press-event', self.__key_press_event_cb)

        self._toolbar = Toolbar(title, has_local_help)
        box.pack_start(self._toolbar, False, False, 0)
        self._toolbar.show()
        self._toolbar.connect('stop-clicked', self.__stop_clicked_cb)
        self._toolbar.connect('mode-changed', self.__mode_changed_cb)

        self._browser = Browser(self._toolbar)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self._browser.get_widget())
        scrolled_window.show()

        box.pack_start(scrolled_window, True, True, 0)

        language = _get_current_language()
        self._help_state = None
        if has_local_help:
            self._help_url = self._browser.get_local_method() + \
                self._get_help_file(language, url)

        self._social_help_uri = '{}/goto/{}'.format(
            get_social_help_server(), activity.get_bundle_id())
        self._social_help_state = None

        self._load_mode(self._mode)

    def __stop_clicked_cb(self, widget):
        self.destroy()

    def __key_press_event_cb(self, window, event):
        if event.keyval == Gdk.KEY_Escape:
            self.__stop_clicked_cb(None)

    def __mode_changed_cb(self, toolbar, mode):
        if mode == _MODE_HELP:
            self._social_help_state = self._browser.save_state()
        else:
            self._help_state = self._browser.save_state()

        self._mode = mode
        self._load_mode(self._mode)

    def _load_mode(self, mode):
        if mode == _MODE_HELP:
            self._browser.load_state(self._help_state, self._help_url)
        else:
            self._browser.load_state(self._social_help_state,
                                     self._social_help_uri)

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)
        if self.parent_window_xid > 0:
            display = Gdk.Display.get_default()
            parent = GdkX11.X11Window.foreign_new_for_display(
                display, self.parent_window_xid)
            window.set_transient_for(parent)
        shell.get_model().push_modal()

    def __hide_cb(self, widget):
        shell.get_model().pop_modal()

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
        'back-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'forward-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'mode-changed': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self, activity_name, has_local_help):
        Gtk.Toolbar.__init__(self)

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
            self.insert(help_button, -1)
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
            social_help_button.connect(
                'toggled', self.__button_toggled_cb, _MODE_SOCIAL_HELP)
            self.insert(social_help_button, -1)
            social_help_button.show()
            self._add_separator(False)

        self._back_button = ToolButton(icon_name='go-previous-paired')
        self._back_button.props.tooltip = _('Back')
        self._back_button.connect('clicked', self.__back_clicked_cb)
        self.insert(self._back_button, -1)
        self._back_button.show()
        self._forward_button = ToolButton(icon_name='go-next-paired')
        self._forward_button.props.tooltip = _('Forward')
        self._forward_button.connect('clicked', self.__forward_clicked_cb)
        self.insert(self._forward_button, -1)
        self._forward_button.show()

        title = _('Help: %s') % activity_name
        self._label = Gtk.Label()
        self._label.set_markup('<b>%s</b>' % title)
        self._label.set_alignment(0, 0.5)
        self._add_widget(self._label)

        self._add_separator(True)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Close'))
        stop.connect('clicked', self.__stop_clicked_cb)
        self.insert(stop, -1)
        stop.show()

    def __stop_clicked_cb(self, widget):
        self.emit('stop-clicked')

    def __button_toggled_cb(self, button, mode):
        if button.props.active:
            self.emit('mode-changed', mode)

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

    def update_back_forward(self, can_go_back, can_go_forward):
        self._back_button.props.sensitive = can_go_back
        self._forward_button.props.sensitive = can_go_forward

    def __back_clicked_cb(self, button):
        self.emit('back-clicked')

    def __forward_clicked_cb(self, button):
        self.emit('forward-clicked')
