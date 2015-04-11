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
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import WebKit2
from gi.repository import Gio
from gi.repository import GdkX11

from sugar3 import env
from sugar3.graphics import style
from sugar3.graphics.icon import get_icon_file_name
from sugar3.graphics.toolbutton import ToolButton
from sugar3.bundle.activitybundle import get_bundle_instance
from jarabe.model import shell


_logger = logging.getLogger('ViewSocialHelp')


def setup_view_social_help(activity):
    if shell.get_model().has_modal():
        return
    # check whether the execution was from an activity
    bundle_path = activity.get_bundle_path()
    if bundle_path is None:
        return
    else:
        # get activity name and window id
        window_xid = activity.get_xid()

    activity_bundle = get_bundle_instance(bundle_path)
    bundle_id = activity_bundle.get_bundle_id()

    viewsocialhelp = ViewSocialHelp(bundle_id, window_xid)
    activity.push_shell_window(viewsocialhelp)
    viewsocialhelp.connect('hide', activity.pop_shell_window)
    viewsocialhelp.show()


class ViewSocialHelp(Gtk.Window):
    parent_window_xid = None

    def __init__(self, bundle_id, window_xid):
        self.parent_window_xid = window_xid

        Gtk.Window.__init__(self)
        overlay = Gtk.Overlay()
        self.add(overlay)
        overlay.show()

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)

        tb = Gtk.Toolbar()
        tb.props.valign = Gtk.Align.START
        tb.props.halign = Gtk.Align.END
        overlay.add_overlay(tb)
        tb.show()

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Close'))
        stop.connect('clicked', self.__stop_clicked_cb)
        tb.insert(stop, -1)
        stop.show()

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)

        self.connect('realize', self.__realize_cb)

        webview = WebKit2.WebView()
        webview.connect('load-changed', self.__load_status_changed_cb)

        context = WebKit2.WebContext.get_default()
        cookies = context.get_cookie_manager()
        cookies.set_persistent_storage(
            os.path.join(env.get_profile_path(), 'social-help.cookies'),
            WebKit2.CookiePersistentStorage.SQLITE)

        overlay.add(webview)

        webview.show()
        webview.load_uri('https://use-socialhelp.sugarlabs.org/goto/'
                         + bundle_id)

    def __load_status_changed_cb(self, web_view, load_event):
        if load_event == WebKit2.LoadEvent.FINISHED:
            web_view.run_javascript('document.body.classList.add("sugar");',
                                    None, None, None)

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
