# Copyright (C) 2008, Red Hat, Inc.
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

import logging
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from sugar4.graphics import style

from jarabe.model import shell
from jarabe.view.pulsingicon import PulsingIcon

_INTERVAL = 100


class LaunchWindow(Gtk.Box):

    def __init__(self, activity_id, icon_path, icon_color):
        super().__init__()
        
        self.add_css_class('launch-window')
        
        provider = Gtk.CssProvider()
        css = b".launch-window { background-color: %s; }" % style.COLOR_WHITE.get_html().encode('utf-8')
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.set_hexpand(True)
        self.set_vexpand(True)

        canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        canvas.set_visible(True)
        self.append(canvas)

        display = Gdk.Display.get_default()
        screen_height = 768
        screen_width = 1024
        if display:
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                geo = monitors.get_item(0).get_geometry()
                screen_width, screen_height = geo.width, geo.height

        bar_size = screen_height / 5 * 2

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header.set_size_request(-1, int(bar_size))
        header.set_visible(True)
        canvas.append(header)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_size_request(int(screen_width / 5), -1)
        box.set_vexpand(True)
        box.set_visible(True)
        canvas.append(box)

        self._activity_id = activity_id

        self._activity_icon = PulsingIcon(file=icon_path,
                                          pixel_size=style.XLARGE_ICON_SIZE,
                                          interval=_INTERVAL)
        self._activity_icon.set_base_color(icon_color)
        self._activity_icon.set_zooming(style.SMALL_ICON_SIZE,
                                        style.XLARGE_ICON_SIZE, 10)
        self._activity_icon.set_pulsing(True)
        self._activity_icon.set_visible(True)
        
        self._activity_icon.set_hexpand(True)
        self._activity_icon.set_halign(Gtk.Align.CENTER)
        self._activity_icon.set_valign(Gtk.Align.CENTER)
        box.append(self._activity_icon)

        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=style.DEFAULT_SPACING)
        footer.set_size_request(-1, int(bar_size))
        footer.set_visible(True)
        canvas.append(footer)

        self.error_text = Gtk.Label()
        self.error_text.props.use_markup = True
        footer.append(self.error_text)

        button_box = Gtk.Box()
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_valign(Gtk.Align.START)
        button_box.set_visible(True)
        footer.append(button_box)
        
        self.cancel_button = Gtk.Button.new_from_icon_name('process-stop')
        button_box.append(self.cancel_button)

        if display:
            monitors = display.get_monitors()
            monitors.connect('items-changed', self.__size_changed_cb)

        self._home = shell.get_model()
        self._home.connect('active-activity-changed',
                           self.__active_activity_changed_cb)
        self.connect('unrealize', self.__unrealize_cb)

        self._update_size()

    def _update_size(self):
        pass

    def __size_changed_cb(self, list_model, position, removed, added):
        self._update_size()

    def __active_activity_changed_cb(self, model, activity):
        if activity is not None and activity.get_activity_id() == self._activity_id:
            self._activity_icon.props.paused = False
        else:
            self._activity_icon.props.paused = True

    def __unrealize_cb(self, widget):
        self._activity_icon.props.pulsing = False
        self._home.disconnect_by_func(self.__active_activity_changed_cb)


def setup():
    global _INTERVAL

    settings = Gio.Settings.new('org.sugarlabs.desktop')
    _INTERVAL = settings.get_int('launcher-interval')

    model = shell.get_model()
    model.connect('launch-started', __launch_started_cb)
    model.connect('launch-failed', __launch_failed_cb)
    model.connect('launch-completed', __launch_completed_cb)


def add_launcher(activity_id, icon_path, icon_color):
    model = shell.get_model()

    if model.get_launcher(activity_id) is not None:
        return

    launch_window = LaunchWindow(activity_id, icon_path, icon_color)

    model._stack.add_named(launch_window, f"launcher_{activity_id}")
    model._stack.set_visible_child_name(f"launcher_{activity_id}")
    model.register_launcher(activity_id, launch_window)


def __launch_started_cb(home_model, home_activity):
    add_launcher(home_activity.get_activity_id(),
                 home_activity.get_icon_path(), home_activity.get_icon_color())


def __launch_failed_cb(home_model, home_activity):
    activity_id = home_activity.get_activity_id()
    launcher = shell.get_model().get_launcher(activity_id)

    if launcher is None:
        logging.error('Launcher for %s is missing', activity_id)
    else:
        launcher.error_text.props.label = _('<b>%s</b> failed to start.') % \
            home_activity.get_activity_name()
        launcher.error_text.set_visible(True)

        launcher.cancel_button.connect('clicked',
                                       __cancel_button_clicked_cb,
                                       home_activity)
        launcher.cancel_button.set_visible(True)


def __cancel_button_clicked_cb(button, home_activity):
    _destroy_launcher(home_activity)


def __launch_completed_cb(home_model, home_activity):
    _destroy_launcher(home_activity)


def _destroy_launcher(home_activity):
    activity_id = home_activity.get_activity_id()

    model = shell.get_model()
    launcher = model.get_launcher(activity_id)
    if launcher is None:
        if not home_activity.is_journal():
            logging.error('Launcher was not registered for %s', activity_id)
        return

    model.unregister_launcher(activity_id)
    if launcher.get_parent() == model._stack:
        model._stack.remove(launcher)
    if model._stack.get_visible_child() is None:
        model._stack.set_visible_child_name("home")

