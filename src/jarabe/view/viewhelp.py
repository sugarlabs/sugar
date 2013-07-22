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

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.bundle.activitybundle import ActivityBundle

import logging
import os
from os.path import expanduser
from helplink import get_links

_logger = logging.getLogger('ViewHelp')
links = get_links()
activity_path = None


def setup_view_help(activity):
    global activity_path
    bundle_path = activity.get_bundle_path()
    if bundle_path is None:
        # display error message
        return
    activity_bundle = ActivityBundle(bundle_path)
    activity_name = activity_bundle.get_name()
    activity_path = str.join(os.sep, activity.get_bundle_path().split(os.sep)[:-1])
#    _logger.exception('ACTIVITY PATH:' + activity_path)

    if activity_name in links.keys():
        viewhelp = ViewHelp(activity_name, links[activity_name])
        viewhelp.show()
    else:
        # display error message
        return


class ViewHelp(Gtk.Window):
    def __init__(self, activity_name, help_file):
        Gtk.Window.__init__(self)
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(box)
        box.show()

        toolbar = Toolbar(activity_name)
        box.pack_start(toolbar, False, False, 0)
        toolbar.show()
        toolbar.connect('stop-clicked', self.stop_clicked_cb)

        webview = WebKit.WebView()
        webview.set_full_content_zoom(True)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(webview)
        scrolled_window.show()

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)

        box.pack_start(scrolled_window, True, True, 0)

        webview.show()
        language = self.get_current_language()
        locale_dir = self.get_locale_directory(language)
        #_logger.exception('LOCALE_DIR: ', locale_dir)
        webview.load_uri('file://' + os.path.join(locale_dir + help_file))

    def stop_clicked_cb(self, widget):
        self.destroy()

    def get_current_language(self):
        language_file_path = os.path.join(expanduser('~'), '.i18n')
        f = open(language_file_path, 'r')
        language = f.readlines()[0].split('=')[1]
        language = language.split('.')[0]
        f.close()
        return language

    def get_locale_directory(self, language):
        path = os.path.join(activity_path, 'Help.activity/help/')
        #locale_path = os.path.join(path, language)
        #_logger.exception('LOCALE PATH: ' + locale_path)
        #if os.path.isdir(locale_path):
        #return locale_path
        return path


class Toolbar(Gtk.Toolbar):

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, activity_name):
        Gtk.Toolbar.__init__(self)

        title = 'Help: ' + activity_name

        self.add_separator(False)

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
