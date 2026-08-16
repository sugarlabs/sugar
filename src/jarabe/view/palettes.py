# Copyright (C) 2008 One Laptop Per Child
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
import signal
from gettext import gettext as _
import logging

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from sugar4 import env
from sugar4 import profile
from sugar4.graphics.palette import Palette
from sugar4.graphics.palettemenu import PaletteMenuBox
from sugar4.graphics.palettemenu import PaletteMenuItem
from sugar4.graphics.palettemenu import PaletteMenuItemSeparator
from sugar4.graphics.icon import Icon
from sugar4.graphics import style
from sugar4.graphics.xocolor import XoColor
from gettext import pgettext

from jarabe.model import shell
from jarabe.view.viewsource import setup_view_source
from jarabe.view.viewhelp import setup_view_help
from jarabe.view.viewhelp import should_show_view_help
from jarabe.journal import misc


class BasePalette(Palette):

    def __init__(self, home_activity):
        Palette.__init__(self)

        self._notify_launch_hid = None

        if home_activity.props.launch_status == shell.Activity.LAUNCHING:
            self._notify_launch_hid = home_activity.connect(
                'notify::launch-status', self.__notify_launch_status_cb)
            self.set_primary_text(_('Starting...'))
        elif home_activity.props.launch_status == shell.Activity.LAUNCH_FAILED:
            self._on_failed_launch()
        else:
            self.setup_palette()

    def setup_palette(self):
        raise NotImplementedError

    def _on_failed_launch(self):
        message = _('Activity failed to start')
        self.set_primary_text(message)

    def __notify_launch_status_cb(self, home_activity, pspec):
        home_activity.disconnect(self._notify_launch_hid)
        self._notify_launch_hid = None
        if home_activity.props.launch_status == shell.Activity.LAUNCH_FAILED:
            self._on_failed_launch()
        else:
            self.setup_palette()


class CurrentActivityPalette(BasePalette):

    __gsignals__ = {
        'done': (GObject.SignalFlags.RUN_FIRST,
                 None,
                 ([])),
    }

    def __init__(self, home_activity):
        self._home_activity = home_activity
        BasePalette.__init__(self, home_activity)

    def setup_palette(self):
        activity_name = self._home_activity.get_activity_name()
        if activity_name:
            self.props.primary_text = activity_name

        title = self._home_activity.get_title()
        if title and title != activity_name:
            self.props.secondary_text = title

        self.menu_box = PaletteMenuBox()

        menu_item = PaletteMenuItem(_('Resume'), 'activity-start')
        menu_item.connect('item-activated', self.__resume_activate_cb)
        self.menu_box.append_item(menu_item)
        menu_item.set_visible(True)

        # TODO: share-with, keep

        menu_item = PaletteMenuItem(_('View Source'), 'view-source')
        menu_item.connect('item-activated', self.__view_source__cb)
        menu_item.set_accelerator('Shift+Alt+V')
        self.menu_box.append_item(menu_item)
        menu_item.set_visible(True)

        if should_show_view_help(self._home_activity):
            menu_item = PaletteMenuItem(_('View Help'), 'toolbar-help')
            menu_item.connect('item-activated', self.__view_help__cb)
            menu_item.set_accelerator('Shift+Alt+H')
            self.menu_box.append_item(menu_item)
            menu_item.set_visible(True)

        # avoid circular importing reference
        from jarabe.frame.notification import NotificationBox

        menu_item = NotificationBox(self._home_activity.get_activity_id())
        self.menu_box.append_item(menu_item)

        separator = PaletteMenuItemSeparator()
        menu_item.prepend(separator)
        separator.set_visible(True)

        separator = PaletteMenuItemSeparator()
        self.menu_box.append_item(separator)
        separator.set_visible(True)

        menu_item = PaletteMenuItem(_('Stop'), 'activity-stop')
        menu_item.connect('item-activated', self.__stop_activate_cb)
        self.menu_box.append_item(menu_item)
        menu_item.set_visible(True)

        self.set_content(self.menu_box)
        self.menu_box.set_visible(True)

    def __resume_activate_cb(self, menu_item):
        shell.get_model().activate_activity(self._home_activity)
        self.emit('done')

    def __view_source__cb(self, menu_item):
        setup_view_source(self._home_activity)
        shell_model = shell.get_model()
        if self._home_activity is not shell_model.get_active_activity():
            shell_model.activate_activity(self._home_activity)
        self.emit('done')

    def __view_help__cb(self, menu_item):
        setup_view_help(self._home_activity)
        self.emit('done')

    def __stop_activate_cb(self, menu_item):
        self._home_activity.stop()
        pid = self._home_activity.get_pid()
        GLib.timeout_add(3000, self.__kill_cb, pid, signal.SIGTERM)
        GLib.timeout_add(4500, self.__kill_cb, pid, signal.SIGKILL)
        self.emit('done')

    def __kill_cb(self, pid, sig):
        try:
            os.kill(pid, sig)
        except (OSError, ProcessLookupError):
            pass
        return False


class ActivityPalette(Palette):
    __gtype_name__ = 'SugarActivityPalette'

    def __init__(self, activity_info):
        self._activity_info = activity_info

        color = profile.get_color()
        activity_icon = Icon(file=activity_info.get_icon(),
                             xo_color=color,
                             pixel_size=style.STANDARD_ICON_SIZE)

        name = activity_info.get_name()
        Palette.__init__(self, primary_text=name, icon=activity_icon)

        xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                      style.COLOR_TRANSPARENT.get_svg()))
        self.menu_box = PaletteMenuBox()
        menu_item = PaletteMenuItem(text_label=_('Start new'),
                                    file_name=activity_info.get_icon(),
                                    xo_color=xo_color)
        menu_item.connect('item-activated', self.__start_activate_cb)
        self.menu_box.append_item(menu_item)
        menu_item.set_visible(True)
        self.set_content(self.menu_box)
        self.menu_box.set_visible(True)

        # TODO: start-with

    def __start_activate_cb(self, menu_item):
        misc.launch(self._activity_info)


class JournalPalette(BasePalette):

    def __init__(self, home_activity):
        self._home_activity = home_activity
        self._progress_bar = None
        self._free_space_label = None

        BasePalette.__init__(self, home_activity)

    def setup_palette(self):
        self.set_primary_text(self._home_activity.get_title(), accel_path='F5')

        box = PaletteMenuBox()
        self.set_content(box)
        box.set_visible(True)

        menu_item = PaletteMenuItem(_('Show contents'))
        icon = Icon(file=self._home_activity.get_icon_path(),
                    pixel_size=style.SMALL_ICON_SIZE,
                    xo_color=self._home_activity.get_icon_color())
        
        menu_item.set_icon_widget(icon)
        icon.set_visible(True)

        menu_item.connect('item-activated', self.__open_activate_cb)
        box.append_item(menu_item)
        menu_item.set_visible(True)

        separator = PaletteMenuItemSeparator()
        box.append_item(separator)
        separator.set_visible(True)

        inner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner_box.set_spacing(style.DEFAULT_PADDING)
        box.append_item(inner_box, vertical_padding=0)
        inner_box.set_visible(True)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_hexpand(True)
        inner_box.append(self._progress_bar)
        self._progress_bar.set_visible(True)

        self._free_space_label = Gtk.Label()
        self._free_space_label.set_halign(Gtk.Align.CENTER)
        self._free_space_label.set_valign(Gtk.Align.CENTER)
        self._free_space_label.set_hexpand(True)
        inner_box.append(self._free_space_label)
        self._free_space_label.set_visible(True)

        self.connect('popup', self.__popup_cb)

    def __open_activate_cb(self, menu_item):
        shell.get_model().activate_activity(self._home_activity)

    def __popup_cb(self, palette):
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[0] * stat[4]
        total_space = stat[0] * stat[2]

        fraction = (total_space - free_space) / float(total_space)
        self._progress_bar.props.fraction = fraction
        self._free_space_label.props.label = _('%(free_space)d MiB Free') % \
            {'free_space': free_space / (1024 * 1024)}


class VolumePalette(Palette):

    def __init__(self, mount):
        Palette.__init__(self, label=mount.get_name())
        self._mount = mount

        self.props.secondary_text = mount.get_root().get_path()

        self.content_box = PaletteMenuBox()
        self.set_content(self.content_box)
        self.content_box.set_visible(True)

        menu_item = PaletteMenuItem(pgettext('Volume', 'Remove'))

        icon = Icon(icon_name='media-eject', pixel_size=style.SMALL_ICON_SIZE)
        menu_item.set_icon_widget(icon)
        icon.set_visible(True)

        menu_item.connect('item-activated', self.__unmount_activate_cb)
        self.content_box.append_item(menu_item)
        menu_item.set_visible(True)

        separator = PaletteMenuItemSeparator()
        self.content_box.append_item(separator)
        separator.set_visible(True)

        free_space_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        free_space_box.set_spacing(style.DEFAULT_PADDING)
        self.content_box.append_item(free_space_box)
        free_space_box.set_visible(True)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_hexpand(True)
        free_space_box.append(self._progress_bar)
        self._progress_bar.set_visible(True)

        self._free_space_label = Gtk.Label()
        self._free_space_label.set_halign(Gtk.Align.CENTER)
        self._free_space_label.set_valign(Gtk.Align.CENTER)
        self._free_space_label.set_hexpand(True)
        free_space_box.append(self._free_space_label)
        self._free_space_label.set_visible(True)

        self.connect('popup', self.__popup_cb)

    def __unmount_activate_cb(self, menu_item):
        flags = 0
        master_window = None
        app = shell.get_model()
        if app and app.get_windows():
            master_window = app.get_windows()[0]
        
        mount_operation = Gtk.MountOperation(
            parent=master_window)
        cancellable = None
        user_data = None
        self._mount.unmount_with_operation(flags, mount_operation, cancellable,
                                           self.__unmount_cb, user_data)

    def __unmount_cb(self, mount, result, user_data):
        logging.debug('__unmount_cb %r %r', mount, result)
        mount.unmount_with_operation_finish(result)

    def __popup_cb(self, palette):
        mount_point = self._mount.get_root().get_path()
        stat = os.statvfs(mount_point)
        free_space = stat[0] * stat[4]
        total_space = stat[0] * stat[2]

        fraction = (total_space - free_space) / float(total_space)
        self._progress_bar.props.fraction = fraction
        self._free_space_label.props.label = _('%(free_space)d MiB Free') % \
            {'free_space': free_space / (1024 * 1024)}
