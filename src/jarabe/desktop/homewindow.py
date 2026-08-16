# Copyright (C) 2006-2007 Red Hat, Inc.
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
import os
import logging

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio

from sugar4.graphics import style
from sugar4.graphics import palettegroup

from jarabe.desktop.meshbox import MeshBox
from jarabe.desktop.homebox import HomeBox
from jarabe.desktop.homebackgroundbox import HomeBackgroundBox
from jarabe.desktop.groupbox import GroupBox
from jarabe.desktop.transitionbox import TransitionBox
from jarabe.desktop.viewtoolbar import ViewToolbar
from jarabe.model.shell import ShellModel
from jarabe.model import shell
from jarabe import config

_HOME_PAGE = 0
_GROUP_PAGE = 1
_MESH_PAGE = 2
_TRANSITION_PAGE = 3

_instance = None


def _get_children(box):
    children = []
    child = box.get_first_child()
    while child:
        children.append(child)
        child = child.get_next_sibling()
    return children


class HomeWindow(Gtk.Box):

    def __init__(self):
        logging.debug('STARTUP: Loading the desktop window')
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class('home-window')
        self.add_css_class('background')

        self._active = False
        self._fully_obscured = True

        display = Gdk.Display.get_default()
        self._monitors = display.get_monitors()
        self._monitors_hid = self._monitors.connect('items-changed', self.__screen_size_changed_cb)
        self._monitor_geom_hid = None
        self._current_monitor = None
        if self._monitors.get_n_items() > 0:
            self._current_monitor = self._monitors.get_item(0)
            self._monitor_geom_hid = self._current_monitor.connect('notify::geometry', self.__screen_size_changed_cb)
            geom = self._current_monitor.get_geometry()
            self.set_size_request(geom.width, geom.height)

        icons_path = os.path.join(config.data_path, 'icons')
        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_theme.add_search_path(icons_path)

        self._busy_count = 0
        self.busy()

        key_controller = Gtk.EventControllerKey.new()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect('key-pressed', self.__key_pressed_cb)
        key_controller.connect('key-released', self.__key_released_cb)
        self.add_controller(key_controller)

        focus_controller = Gtk.EventControllerFocus.new()
        focus_controller.connect('leave', self.__focus_out_event_cb)
        self.add_controller(focus_controller)

        self._box = HomeBackgroundBox()
        self._box.set_hexpand(True)

        self._toolbar = ViewToolbar()
        self._toolbar.add_css_class('toolbar')
        self._box.append(self._toolbar)

        self._alert = None

        self._view_stack = Gtk.Stack()
        self._view_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self._view_stack.set_vexpand(True)
        self._box.append(self._view_stack)

        self._home_box = HomeBox(self._toolbar)
        self._view_stack.add_named(self._home_box, 'home')
        self._toolbar.show_view_buttons()

        setting = Gio.Settings.new('org.sugarlabs.user')
        self._resume_mode = setting.get_boolean('resume-activity')
        self._home_box.set_resume_mode(self._resume_mode)

        self._group_box = GroupBox(self._toolbar)
        self._view_stack.add_named(self._group_box, 'group')
        
        self._mesh_box = MeshBox(self._toolbar)
        self._view_stack.add_named(self._mesh_box, 'mesh')
        
        self._transition_box = TransitionBox()
        self._view_stack.add_named(self._transition_box, 'transition')

        self._view_stack.set_visible_child_name('home')

        self.append(self._box)

        self._transition_box.connect('completed',
                                     self._transition_completed_cb)

        self._zoom_hid = shell.get_model().zoom_level_changed.connect(
            self.__zoom_level_changed_cb)

        self._alt_held = False

    def add_alert(self, alert):
        self._alert = alert
        self._show_alert()

    def remove_alert(self, alert):
        if alert == self._alert:
            self._box.remove(self._alert)
            self._alert = None

    def _show_alert(self):
        if self._alert:
            self._box.append(self._alert)
            self._box.reorder_child_after(self._alert, self._toolbar)

    def _hide_alert(self):
        if self._alert:
            self._box.remove(self._alert)

    def _deactivate_view(self, level):
        group = palettegroup.get_group('default')
        group.popdown()
        if level == ShellModel.ZOOM_HOME:
            self._home_box.suspend()
        elif level == ShellModel.ZOOM_MESH:
            self._mesh_box.suspend()

    def __screen_size_changed_cb(self, *args):
        if self._monitors.get_n_items() > 0:
            monitor = self._monitors.get_item(0)
            if self._current_monitor != monitor:
                if self._current_monitor and self._monitor_geom_hid:
                    self._current_monitor.disconnect(self._monitor_geom_hid)
                self._current_monitor = monitor
                self._monitor_geom_hid = monitor.connect('notify::geometry', self.__screen_size_changed_cb)
            geom = monitor.get_geometry()
            self.set_size_request(geom.width, geom.height)

    def _activate_view(self, level):
        if level == ShellModel.ZOOM_HOME:
            self._home_box.resume()
        elif level == ShellModel.ZOOM_MESH:
            self._mesh_box.resume()

    def __is_alt(self, keyval, state):
        # with Shift held, Alt reports as Meta
        shift = (state & Gdk.ModifierType.SHIFT_MASK) != 0
        return keyval in [Gdk.KEY_Alt_L, Gdk.KEY_Alt_R] or \
            keyval in [Gdk.KEY_Meta_L, Gdk.KEY_Meta_R] and shift

    def __key_pressed_cb(self, controller, keyval, keycode, state):
        if self.__is_alt(keyval, state) and not getattr(self, '_alt_held', False):
            self._home_box.set_resume_mode(not self._resume_mode)
            self._alt_held = True

        _modifier_mask = (Gdk.ModifierType.CONTROL_MASK |
                          Gdk.ModifierType.ALT_MASK |
                          Gdk.ModifierType.SUPER_MASK |
                          Gdk.ModifierType.META_MASK)
        has_modifier = bool(state & _modifier_mask)

        unicode_char = Gdk.keyval_to_unicode(keyval)
        is_printable = unicode_char >= 0x20 and unicode_char != 0x7F

        if is_printable and not has_modifier:
            search_entry = self._toolbar.search_entry
            if search_entry is None:
                return False

            has_focus = bool(search_entry.get_state_flags() & Gtk.StateFlags.FOCUS_WITHIN)

            if not has_focus:
                search_entry.grab_focus()


        return False

    def __key_released_cb(self, controller, keyval, keycode, state):
        if self.__is_alt(keyval, state) and getattr(self, '_alt_held', False):
            self._home_box.set_resume_mode(self._resume_mode)
            self._alt_held = False

        return False

    def __focus_out_event_cb(self, controller):
        if getattr(self, '_alt_held', False):
            self._home_box.set_resume_mode(self._resume_mode)
            self._alt_held = False

    def __zoom_level_changed_cb(self, **kwargs):
        old_level = kwargs['old_level']
        new_level = kwargs['new_level']

        self._deactivate_view(old_level)
        self._activate_view(new_level)

        if old_level != ShellModel.ZOOM_ACTIVITY and \
           new_level != ShellModel.ZOOM_ACTIVITY:
            self._hide_alert()
            self._view_stack.set_visible_child_name('transition')

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

        self._hide_alert()

        if level == ShellModel.ZOOM_HOME:
            self._view_stack.set_visible_child_name('home')
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Home'))
            self._toolbar.show_view_buttons()
            GLib.idle_add(self._home_box.grab_focus)
        elif level == ShellModel.ZOOM_GROUP:
            self._view_stack.set_visible_child_name('group')
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Group'))
            self._toolbar.show_view_buttons()
            GLib.idle_add(self._group_box.grab_focus)
        elif level == ShellModel.ZOOM_MESH:
            self._view_stack.set_visible_child_name('mesh')
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Neighborhood'))
            self._toolbar.hide_view_buttons()
            GLib.idle_add(self._mesh_box.grab_focus)
        self._show_alert()

    def do_dispose(self):
        if hasattr(self, '_zoom_hid'):
            shell.get_model().zoom_level_changed.disconnect(self._zoom_hid)
            del self._zoom_hid
        if hasattr(self, '_monitors_hid') and self._monitors:
            self._monitors.disconnect(self._monitors_hid)
            del self._monitors_hid
        if hasattr(self, '_monitor_geom_hid') and self._monitor_geom_hid and self._current_monitor:
            self._current_monitor.disconnect(self._monitor_geom_hid)
            self._monitor_geom_hid = None
            self._current_monitor = None
        super().do_dispose()

    def get_home_box(self):
        return self._home_box

    def busy(self):
        if self._busy_count == 0:
            self._old_cursor = self.get_cursor()
            self._set_cursor(Gdk.Cursor.new_from_name('wait'))
        self._busy_count += 1

    def unbusy(self):
        self._busy_count -= 1
        if self._busy_count == 0:
            # Restore previous cursor — None means system default (arrow)
            self._set_cursor(self._old_cursor)

    def _set_cursor(self, cursor):
        self.set_cursor(cursor)


def get_instance():
    global _instance
    if not _instance:
        _instance = HomeWindow()
    return _instance

