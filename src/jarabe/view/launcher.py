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

from gi.repository import SugarExt
from sugar3.graphics import style

from jarabe.model import shell
from jarabe.view.pulsingicon import PulsingIcon


_INTERVAL = 100


class LaunchWindow(Gtk.Window):

    def __init__(self, activity_id, icon_path, icon_color):
        Gtk.Window.__init__(self)
        self.set_has_resize_grip(False)

        self.props.type_hint = Gdk.WindowTypeHint.SPLASHSCREEN
        self.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        canvas = Gtk.VBox()
        canvas.show()
        self.add(canvas)

        bar_size = Gdk.Screen.height() / 5 * 2

        header = Gtk.VBox()
        header.set_size_request(-1, bar_size)
        header.show()
        canvas.pack_start(header, False, True, 0)

        box = Gtk.HBox()
        box.set_size_request(Gdk.Screen.width() / 5, -1)
        box.show()
        canvas.pack_start(box, True, True, 0)

        self._activity_id = activity_id

        self._activity_icon = PulsingIcon(file=icon_path,
                                          pixel_size=style.XLARGE_ICON_SIZE,
                                          interval=_INTERVAL)
        self._activity_icon.set_base_color(icon_color)
        self._activity_icon.set_zooming(style.SMALL_ICON_SIZE,
                                        style.XLARGE_ICON_SIZE, 10)
        self._activity_icon.set_pulsing(True)
        self._activity_icon.show()
        box.pack_start(self._activity_icon, True, False, 0)

        footer = Gtk.VBox(spacing=style.DEFAULT_SPACING)
        footer.set_size_request(-1, bar_size)
        footer.show()
        canvas.pack_end(footer, False, True, 0)

        self.error_text = Gtk.Label()
        self.error_text.props.use_markup = True
        footer.pack_start(self.error_text, False, True, 0)

        button_box = Gtk.Alignment.new(0.5, 0, 0, 0)
        button_box.show()
        footer.pack_start(button_box, False, True, 0)
        self.cancel_button = Gtk.Button(stock=Gtk.STOCK_STOP)
        button_box.add(self.cancel_button)

        self.connect('realize', self.__realize_cb)

        screen = Gdk.Screen.get_default()
        screen.connect('size-changed', self.__size_changed_cb)

        self._home = shell.get_model()
        self._home.connect('active-activity-changed',
                           self.__active_activity_changed_cb)

        self.connect('destroy', self.__destroy_cb)

        self._update_size()

    def show(self):
        self.present()

    def _update_size(self):
        self.resize(Gdk.Screen.width(), Gdk.Screen.height())

    def __realize_cb(self, widget):
        SugarExt.wm_set_activity_id(widget.get_window().get_xid(),
                                    str(self._activity_id))

    def __size_changed_cb(self, screen):
        self._update_size()

    def __active_activity_changed_cb(self, model, activity):
        if activity.get_activity_id() == self._activity_id:
            self._activity_icon.props.paused = False
        else:
            self._activity_icon.props.paused = True

    def __destroy_cb(self, box):
        self._activity_icon.props.pulsing = False
        self._home.disconnect_by_func(self.__active_activity_changed_cb)


def setup():
    global _INTERVAL

    settings = Gio.Settings('org.sugarlabs.desktop')
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
    launch_window.show()

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
        launcher.error_text.show()

        launcher.cancel_button.connect('clicked',
                                       __cancel_button_clicked_cb,
                                       home_activity)
        launcher.cancel_button.show()


def __cancel_button_clicked_cb(button, home_activity):
    _destroy_launcher(home_activity)


def __launch_completed_cb(home_model, home_activity):
    _destroy_launcher(home_activity)


def _destroy_launcher(home_activity):
    activity_id = home_activity.get_activity_id()

    launcher = shell.get_model().get_launcher(activity_id)
    if launcher is None:
        if not home_activity.is_journal():
            logging.error('Launcher was not registered for %s', activity_id)
        return

    shell.get_model().unregister_launcher(activity_id)
    launcher.destroy()
