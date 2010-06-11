# Copyright (C) 2008, Red Hat, Inc.
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

import logging
from gettext import gettext as _

import gtk
import hippo
import gobject

from sugar import wm
from sugar.graphics import style
from sugar.graphics import animator
from sugar.graphics.xocolor import XoColor

from jarabe.model import shell
from jarabe.view.pulsingicon import CanvasPulsingIcon


class LaunchWindow(gtk.Window):

    def __init__(self, activity_id, icon_path, icon_color):
        gobject.GObject.__init__(self)

        self.props.type_hint = gtk.gdk.WINDOW_TYPE_HINT_NORMAL
        self.props.decorated = False
        self.modify_bg(gtk.STATE_NORMAL, style.COLOR_WHITE.get_gdk_color())

        canvas = gtk.VBox()
        canvas.show()
        self.add(canvas)

        bar_size = gtk.gdk.screen_height() / 5 * 2

        header = gtk.VBox()
        header.set_size_request(-1, bar_size)
        header.show()
        canvas.pack_start(header, expand=False)

        self._activity_id = activity_id
        self._box = LaunchBox(activity_id, icon_path, icon_color)
        box = hippo.Canvas()
        box.modify_bg(gtk.STATE_NORMAL, style.COLOR_WHITE.get_gdk_color())
        box.set_root(self._box)
        box.show()
        canvas.pack_start(box)

        footer = gtk.VBox(spacing=style.DEFAULT_SPACING)
        footer.set_size_request(-1, bar_size)
        footer.show()
        canvas.pack_end(footer, expand=False)

        self.error_text = gtk.Label()
        self.error_text.props.use_markup = True
        footer.pack_start(self.error_text, expand=False)

        button_box = gtk.Alignment(xalign=0.5)
        button_box.show()
        footer.pack_start(button_box, expand=False)
        self.cancel_button = gtk.Button(stock=gtk.STOCK_STOP)
        button_box.add(self.cancel_button)

        self.connect('realize', self.__realize_cb)

        screen = gtk.gdk.screen_get_default()
        screen.connect('size-changed', self.__size_changed_cb)

        self._update_size()

    def show(self):
        self.present()
        self._box.zoom_in()

    def _update_size(self):
        self.resize(gtk.gdk.screen_width(), gtk.gdk.screen_height())

    def __realize_cb(self, widget):
        wm.set_activity_id(widget.window, str(self._activity_id))
        widget.window.property_change('_SUGAR_WINDOW_TYPE', 'STRING', 8,
                                      gtk.gdk.PROP_MODE_REPLACE, 'launcher')

    def __size_changed_cb(self, screen):
        self._update_size()


class LaunchBox(hippo.CanvasBox):

    def __init__(self, activity_id, icon_path, icon_color):
        gobject.GObject.__init__(self, orientation=hippo.ORIENTATION_VERTICAL)

        self._activity_id = activity_id
        self._activity_icon = CanvasPulsingIcon(
            file_name=icon_path,
            pulse_color=icon_color,
            background_color=style.COLOR_WHITE.get_gdk_color())
        self.append(self._activity_icon, hippo.PACK_EXPAND)

        # FIXME support non-xo colors in CanvasPulsingIcon
        self._activity_icon.props.base_color = \
            XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                               style.COLOR_TRANSPARENT.get_svg()))

        self._animator = animator.Animator(1.0)

        self._home = shell.get_model()
        self._home.connect('active-activity-changed',
                           self.__active_activity_changed_cb)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, box):
        self._activity_icon.props.pulsing = False
        self._home.disconnect_by_func(self.__active_activity_changed_cb)

    def zoom_in(self):
        self._activity_icon.props.size = style.STANDARD_ICON_SIZE

        self._animator.remove_all()
        self._animator.add(_Animation(self._activity_icon,
                                      style.STANDARD_ICON_SIZE,
                                      style.XLARGE_ICON_SIZE))
        self._animator.start()
        self._activity_icon.props.pulsing = True

    def __active_activity_changed_cb(self, model, activity):
        if activity.get_activity_id() == self._activity_id:
            self._activity_icon.props.paused = False
        else:
            self._activity_icon.props.paused = True


class _Animation(animator.Animation):

    def __init__(self, icon, start_size, end_size):
        animator.Animation.__init__(self, 0.0, 1.0)

        self._icon = icon
        self.start_size = start_size
        self.end_size = end_size

    def next_frame(self, current):
        d = (self.end_size - self.start_size) * current
        self._icon.props.size = int(self.start_size + d)


_launchers = {}


def setup():
    model = shell.get_model()
    model.connect('launch-started', __launch_started_cb)
    model.connect('launch-failed', __launch_failed_cb)
    model.connect('launch-completed', __launch_completed_cb)


def add_launcher(activity_id, icon_path, icon_color):

    if activity_id in _launchers:
        return

    launch_window = LaunchWindow(activity_id, icon_path, icon_color)
    launch_window.show()

    _launchers[activity_id] = launch_window


def __launch_started_cb(home_model, home_activity):
    add_launcher(home_activity.get_activity_id(),
            home_activity.get_icon_path(), home_activity.get_icon_color())


def __launch_failed_cb(home_model, home_activity):
    activity_id = home_activity.get_activity_id()
    launcher = _launchers.get(activity_id)

    if launcher is None:
        logging.error('Launcher for %s is missing', activity_id)
    else:
        launcher.error_text.props.label = _('<b>%s</b> failed to start.') % \
                home_activity.get_activity_name()
        launcher.error_text.show()

        launcher.cancel_button.connect('clicked',
                __cancel_button_clicked_cb, home_activity)
        launcher.cancel_button.show()


def __cancel_button_clicked_cb(button, home_activity):
    _destroy_launcher(home_activity)


def __launch_completed_cb(home_model, home_activity):
    _destroy_launcher(home_activity)


def _destroy_launcher(home_activity):
    activity_id = home_activity.get_activity_id()

    if activity_id in _launchers:
        _launchers[activity_id].destroy()
        del _launchers[activity_id]
    else:
        logging.error('Launcher for %s is missing', activity_id)
