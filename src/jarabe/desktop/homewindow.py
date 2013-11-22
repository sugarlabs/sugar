# Copyright (C) 2006-2007 Red Hat, Inc.
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

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _
import logging

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11

from sugar3.graphics import style
from sugar3.graphics import palettegroup

from jarabe.desktop.meshbox import MeshBox
from jarabe.desktop.homebox import HomeBox
from jarabe.desktop.homebackgroundbox import HomeBackgroundBox
from jarabe.desktop.groupbox import GroupBox
from jarabe.desktop.transitionbox import TransitionBox
from jarabe.desktop.viewtoolbar import ViewToolbar
from jarabe.model.shell import ShellModel
from jarabe.model import shell


_HOME_PAGE = 0
_GROUP_PAGE = 1
_MESH_PAGE = 2
_TRANSITION_PAGE = 3

_instance = None


class HomeWindow(Gtk.Window):
    def __init__(self):
        logging.debug('STARTUP: Loading the desktop window')
        Gtk.Window.__init__(self)
        self.set_has_resize_grip(False)

        accel_group = Gtk.AccelGroup()
        self.sugar_accel_group = accel_group
        self.add_accel_group(accel_group)

        self._active = False
        self._fully_obscured = True

        screen = self.get_screen()
        screen.connect('size-changed', self.__screen_size_change_cb)
        self.set_default_size(screen.get_width(),
                              screen.get_height())

        self.realize()
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_WHITE.get_gdk_color())

        self.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('visibility-notify-event',
                     self._visibility_notify_event_cb)
        self.connect('map-event', self.__map_event_cb)
        self.connect('key-press-event', self.__key_press_event_cb)
        self.connect('key-release-event', self.__key_release_event_cb)
        self.connect('button-press-event', self.__button_pressed_cb)

        self._box = HomeBackgroundBox()

        self._toolbar = ViewToolbar()
        self._box.pack_start(self._toolbar, False, True, 0)
        self._toolbar.show()

        self._home_box = HomeBox(self._toolbar)
        self._box.pack_start(self._home_box, True, True, 0)
        self._home_box.show()
        self._home_box.grab_focus()
        self._toolbar.show_view_buttons()

        self._group_box = GroupBox(self._toolbar)
        self._mesh_box = MeshBox(self._toolbar)
        self._transition_box = TransitionBox()

        self.add(self._box)
        self._box.show()

        self._transition_box.connect('completed',
                                     self._transition_completed_cb)

        shell.get_model().zoom_level_changed.connect(
            self.__zoom_level_changed_cb)

    def add_alert(self, alert):
        self._box.pack_start(alert, False, True, 0)
        self._box.reorder_child(alert, 1)

    def remove_alert(self, alert):
        self._box.remove(alert)

    def _deactivate_view(self, level):
        group = palettegroup.get_group('default')
        group.popdown()
        if level == ShellModel.ZOOM_HOME:
            self._home_box.suspend()
        elif level == ShellModel.ZOOM_MESH:
            self._mesh_box.suspend()

    def __screen_size_change_cb(self, screen):
        self.resize(screen.get_width(), screen.get_height())

    def _activate_view(self, level):
        if level == ShellModel.ZOOM_HOME:
            self._home_box.resume()
        elif level == ShellModel.ZOOM_MESH:
            self._mesh_box.resume()

    def _visibility_notify_event_cb(self, window, event):
        fully_obscured = (
            event.get_state() == Gdk.VisibilityState.FULLY_OBSCURED)
        if self._fully_obscured == fully_obscured:
            return
        self._fully_obscured = fully_obscured

        if fully_obscured:
            self._deactivate_view(shell.get_model().zoom_level)
        else:
            display = Gdk.Display.get_default()
            screen_, x_, y_, modmask = display.get_pointer()
            if modmask & Gdk.ModifierType.MOD1_MASK:
                self._home_box.set_resume_mode(False)
            else:
                self._home_box.set_resume_mode(True)

            self._activate_view(shell.get_model().zoom_level)

    def __key_press_event_cb(self, window, event):
        if event.keyval in [Gdk.KEY_Alt_L, Gdk.KEY_Alt_R]:
            self._home_box.set_resume_mode(False)
        else:
            if not self._toolbar.search_entry.has_focus():
                self._toolbar.search_entry.grab_focus()
        return False

    def __key_release_event_cb(self, window, event):
        if event.keyval in [Gdk.KEY_Alt_L, Gdk.KEY_Alt_R]:
            self._home_box.set_resume_mode(True)
        return False

    def __button_pressed_cb(self, widget, event):
        current_box = self._box.get_children()[1]
        current_box.grab_focus()
        return False

    def __map_event_cb(self, window, event):
        # have to make the desktop window active
        # since metacity doesn't make it on startup
        timestamp = event.get_time()
        x11_window = self.get_window()
        if not timestamp:
            timestamp = GdkX11.x11_get_server_time(x11_window)
        x11_window.focus(timestamp)

    def __zoom_level_changed_cb(self, **kwargs):
        old_level = kwargs['old_level']
        new_level = kwargs['new_level']

        self._deactivate_view(old_level)
        self._activate_view(new_level)

        if old_level != ShellModel.ZOOM_ACTIVITY and \
           new_level != ShellModel.ZOOM_ACTIVITY:
            children = self._box.get_children()
            if len(children) >= 2:
                self._box.remove(children[1])
            self._box.pack_start(self._transition_box, True, True, 0)
            self._transition_box.show()

            if new_level == ShellModel.ZOOM_HOME:
                end_size = style.XLARGE_ICON_SIZE
            elif new_level == ShellModel.ZOOM_GROUP:
                end_size = style.LARGE_ICON_SIZE
            elif new_level == ShellModel.ZOOM_MESH:
                end_size = style.STANDARD_ICON_SIZE

            if old_level == ShellModel.ZOOM_HOME:
                start_size = style.XLARGE_ICON_SIZE
            elif old_level == ShellModel.ZOOM_GROUP:
                start_size = style.LARGE_ICON_SIZE
            elif old_level == ShellModel.ZOOM_MESH:
                start_size = style.STANDARD_ICON_SIZE

            self._transition_box.start_transition(start_size, end_size)
        else:
            self._update_view(new_level)

    def _transition_completed_cb(self, transition_box):
        self._update_view(shell.get_model().zoom_level)

    def _update_view(self, level):
        if level == ShellModel.ZOOM_ACTIVITY:
            return

        children = self._box.get_children()
        if len(children) >= 2:
            self._box.remove(children[1])

        if level == ShellModel.ZOOM_HOME:
            self._box.pack_start(self._home_box, True, True, 0)
            self._home_box.show()
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Home'))
            self._home_box.grab_focus()
            self._toolbar.show_view_buttons()
        elif level == ShellModel.ZOOM_GROUP:
            self._box.pack_start(self._group_box, True, True, 0)
            self._group_box.show()
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Group'))
            self._group_box.grab_focus()
            self._toolbar.hide_view_buttons()
        elif level == ShellModel.ZOOM_MESH:
            self._box.pack_start(self._mesh_box, True, True, 0)
            self._mesh_box.show()
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Neighborhood'))
            self._mesh_box.grab_focus()
            self._toolbar.hide_view_buttons()

    def get_home_box(self):
        return self._home_box

    def busy_during_delayed_action(self, action):
        """Use busy cursor during execution of action, scheduled via idle_add.
        """
        def action_wrapper(old_cursor):
            try:
                action()
            finally:
                self.get_window().set_cursor(old_cursor)

        old_cursor = self.get_window().get_cursor()
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        GLib.idle_add(action_wrapper, old_cursor)


def get_instance():
    global _instance
    if not _instance:
        _instance = HomeWindow()
    return _instance
