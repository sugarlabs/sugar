# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2011 Walter Bender
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

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import WebKit
from gi.repository import GdkX11

from sugar3 import env
from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.bundle.activitybundle import ActivityBundle

import logging
import os
import json
from os.path import expanduser

_logger = logging.getLogger('ViewHelp')

# get the activity path
activity_path = env.get_user_activities_path()


def setup_view_help(activity):
    # check whether the execution was from an activity
    bundle_path = activity.get_bundle_path()
    if bundle_path is None:
        _logger.error('Not executed from an activity')
        return

    # get activity name and window id
    activity_bundle = ActivityBundle(bundle_path)
    activity_name = activity_bundle.get_name()
    bundle_id = activity_bundle.get_bundle_id()
    window_xid = activity.get_xid()

    # get the help file name for the activity
    try:
        help_content_link = os.path.join(activity_path, 'Help.activity/helplink.json')
        json_file = open(help_content_link)
        links = json.load(json_file)

        # display the activity help in a window
        if bundle_id in links.keys():
            viewhelp = ViewHelp(activity_name, links[bundle_id], window_xid)
            viewhelp.show()
        else:
            _logger.error('Help content is not available for the activity')
    except Exception:
        _logger.error('helplink.json file was not found or the json was malformed')


class ViewHelp(Gtk.Window):
    parent_window_xid = None

    def __init__(self, activity_name, help_file, window_xid):
        self.parent_window_xid = window_xid

        # initiate Gtk Window
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

        self.connect('realize', self.realize_cb)

        # implement the tool bar
        toolbar = Toolbar(activity_name)
        box.pack_start(toolbar, False, False, 0)
        toolbar.show()
        toolbar.connect('stop-clicked', self.stop_clicked_cb)

        # implement WebKit WebView
        webview = WebKit.WebView()
        webview.set_full_content_zoom(True)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(webview)
        scrolled_window.show()

        box.pack_start(scrolled_window, True, True, 0)

        webview.show()

        # get the current language and display relavent html file
        language = self.get_current_language()
        view_file = self.get_help_file(language, help_file)
        webview.load_uri('file://' + view_file)

    def stop_clicked_cb(self, widget):
        self.destroy()

    def realize_cb(self, widget):
        # focus the help viewer and prompt it over the activity window
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)
        display = Gdk.Display.get_default()
        parent = GdkX11.X11Window.foreign_new_for_display(display, self.parent_window_xid)
        window.set_transient_for(parent)

    def get_current_language(self):
        locale = os.environ.get('LANG')
        return locale.split('.')[0].split('_')[0].lower()

    def get_help_file(self, language, help_file):
        path = os.path.join(activity_path, 'Help.activity/help/', language, help_file)
        if not os.path.isfile(path):
            path = os.path.join(activity_path, 'Help.activity/help/en/', help_file)
        return path


class Toolbar(Gtk.Toolbar):

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, activity_name):
        Gtk.Toolbar.__init__(self)

        title = 'Help: ' + activity_name

        self.add_separator(False)

        # display activity name as the title of the window
        label = Gtk.Label()
        label.set_markup('<b>%s</b>' % title)
        label.set_alignment(0, 0.5)
        self.add_widget(label)

        self.add_separator(True)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Close'))
        stop.connect('clicked', self.stop_clicked_cb)
        self.insert(stop, -1)
        stop.show()

    def stop_clicked_cb(self, widget):
        self.emit('stop-clicked')

    def add_widget(self, widget):
        tool_item = Gtk.ToolItem()
        tool_item.add(widget)
        widget.show()
        self.insert(tool_item, -1)
        tool_item.show()

    def add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.insert(separator, -1)
        separator.show()
