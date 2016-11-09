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
import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
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
        screen.connect('size-changed', self.__screen_size_changed_cb)
        self.set_default_size(screen.get_width(),
                              screen.get_height())

        self.__screen_size_changed_cb(None)

        self.realize()
        self._busy_count = 0
        self.busy()

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

        self._box = HomeBackgroundBox()

        self._toolbar = ViewToolbar()
        self._box.pack_start(self._toolbar, False, True, 0)
        self._toolbar.show()

        self._alert = None

        self._home_box = HomeBox(self._toolbar)
        self._box.pack_start(self._home_box, True, True, 0)
        self._home_box.show()
        self._toolbar.show_view_buttons()

        # Loads the Gsettings value for activity 'resume-mode'
        setting = Gio.Settings('org.sugarlabs.user')
        self._resume_mode = setting.get_boolean('resume-activity')
        self._home_box.set_resume_mode(self._resume_mode)

        self._group_box = GroupBox(self._toolbar)
        self._mesh_box = MeshBox(self._toolbar)
        self._transition_box = TransitionBox()

        self.add(self._box)
        self._box.show()

        self._transition_box.connect('completed',
                                     self._transition_completed_cb)

        shell.get_model().zoom_level_changed.connect(
            self.__zoom_level_changed_cb)

        self._alt_timeout_sid = None

    def add_alert(self, alert):
        self._alert = alert
        self._show_alert()

    def remove_alert(self, alert):
        if alert == self._alert:
            self._box.remove(self._alert)
            self._alert = None

    def _show_alert(self):
        if self._alert:
            self._box.pack_start(self._alert, False, False, 0)
            self._box.reorder_child(self._alert, 1)

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

    def __screen_size_changed_cb(self, screen):
        screen = Gdk.Screen.get_default()
        n = screen.get_number()
        rect = screen.get_monitor_geometry(n)
        geometry = Gdk.Geometry()
        geometry.max_width = geometry.base_width = geometry.min_width = \
            rect.width
        geometry.max_height = geometry.base_height = geometry.min_height = \
            rect.height
        geometry.width_inc = geometry.height_inc = geometry.min_aspect = \
            geometry.max_aspect = 1
        hints = Gdk.WindowHints(Gdk.WindowHints.ASPECT |
                                Gdk.WindowHints.BASE_SIZE |
                                Gdk.WindowHints.MAX_SIZE |
                                Gdk.WindowHints.MIN_SIZE)
        workarea = screen.get_monitor_workarea(n)
        self.move(workarea.x, workarea.y)
        self.set_geometry_hints(None, geometry, hints)

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
            self._activate_view(shell.get_model().zoom_level)

    def __is_alt(self, event):
        # When shift is on, <ALT> becomes <META>
        shift = (event.state & Gdk.ModifierType.SHIFT_MASK) == 1
        return event.keyval in [Gdk.KEY_Alt_L, Gdk.KEY_Alt_R] or \
            event.keyval in [Gdk.KEY_Meta_L, Gdk.KEY_Meta_R] and shift

    def __key_press_event_cb(self, window, event):
        if self.__is_alt(event) and not self._alt_timeout_sid:
            self._home_box.set_resume_mode(not self._resume_mode)
            self._alt_timeout_sid = GObject.timeout_add(100,
                                                        self.__alt_timeout_cb)

        if not self._toolbar.search_entry.props.has_focus:
            self._toolbar.search_entry.grab_focus()

        return False

    def __key_release_event_cb(self, window, event):
        if self.__is_alt(event) and self._alt_timeout_sid:
            self._home_box.set_resume_mode(self._resume_mode)
            GObject.source_remove(self._alt_timeout_sid)
            self._alt_timeout_sid = None

        return False

    def __alt_timeout_cb(self):
        display = Gdk.Display.get_default()
        screen_, x_, y_, modmask = display.get_pointer()
        if modmask & Gdk.ModifierType.MOD1_MASK:
            return True

        self._home_box.set_resume_mode(self._resume_mode)

        if self._alt_timeout_sid:
            GObject.source_remove(self._alt_timeout_sid)
            self._alt_timeout_sid = None

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
            self._hide_alert()
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

        self._hide_alert()
        children = self._box.get_children()
        if len(children) >= 2:
            self._box.remove(children[1])

        if level == ShellModel.ZOOM_HOME:
            self._box.pack_start(self._home_box, True, True, 0)
            self._home_box.show()
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Home'))
            self._toolbar.show_view_buttons()
        elif level == ShellModel.ZOOM_GROUP:
            self._box.pack_start(self._group_box, True, True, 0)
            self._group_box.show()
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Group'))
            self._toolbar.hide_view_buttons()
        elif level == ShellModel.ZOOM_MESH:
            self._box.pack_start(self._mesh_box, True, True, 0)
            self._mesh_box.show()
            self._toolbar.clear_query()
            self._toolbar.set_placeholder_text_for_view(_('Neighborhood'))
            self._toolbar.hide_view_buttons()
        self._show_alert()

    def get_home_box(self):
        return self._home_box

    def busy(self):
        if self._busy_count == 0:
            self._old_cursor = self.get_window().get_cursor()
            self._set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        self._busy_count += 1

    def unbusy(self):
        self._busy_count -= 1
        if self._busy_count == 0:
            self._set_cursor(self._old_cursor)

    def _set_cursor(self, cursor):
        self.get_window().set_cursor(cursor)
        Gdk.flush()


def get_instance():
    global _instance
    if not _instance:
        _instance = HomeWindow()
    return _instance
