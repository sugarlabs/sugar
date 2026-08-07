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

import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gio

from sugar4.graphics import animator
from sugar4.graphics import style
from sugar4.graphics import palettegroup
from sugar4 import profile

from jarabe.frame.eventarea import EventArea
from jarabe.frame.activitiestray import ActivitiesTray
from jarabe.frame.zoomtoolbar import ZoomToolbar
from jarabe.frame.friendstray import FriendsTray
from jarabe.frame.devicestray import DevicesTray
from jarabe.frame.framewindow import FrameWindow
from jarabe.frame.clipboardpanelwindow import ClipboardPanelWindow
from jarabe.frame.notification import NotificationIcon, NotificationWindow
from jarabe.model import notifications

TOP_RIGHT = 0
TOP_LEFT = 1
BOTTOM_RIGHT = 2
BOTTOM_LEFT = 3

NOTIFICATION_DURATION = 5000


def _get_screen_size():
    display = Gdk.Display.get_default()
    if display:
        monitors = display.get_monitors()
        if monitors and monitors.get_n_items() > 0:
            geometry = monitors.get_item(0).get_geometry()
            return geometry.width, geometry.height
    return 1024, 768


class _Animation:
    """Simple timer-based frame animation.

    Uses GLib.timeout_add so it works regardless of whether the panel
    widget is currently mapped/realized (unlike add_tick_callback which
    requires the widget to be on screen first).
    """

    _DURATION_MS = 500
    _STEP_MS = 16       # ~60 fps

    def __init__(self, frame, start, end):
        self._frame = frame
        self.start = start
        self.end = end
        self._sid = 0
        self._elapsed_ms = 0

    def start_anim(self):
        self._elapsed_ms = 0
        self._sid = GLib.timeout_add(self._STEP_MS, self._on_tick)

    def stop(self):
        if self._sid:
            GLib.source_remove(self._sid)
            self._sid = 0

    def _on_tick(self):
        self._elapsed_ms += self._STEP_MS
        progress = min(self._elapsed_ms / self._DURATION_MS, 1.0)
        current = self.start + (self.end - self.start) * progress
        self._frame.move_panels(current)

        if progress >= 1.0:
            self._sid = 0
            # At position 0.0 the panels are off-screen via margin; no
            # visibility change needed.
            return False  # stop timer
        return True  # continue


class Frame(object):

    def __init__(self):
        logging.debug('STARTUP: Loading the frame')

        self.settings = Gio.Settings.new('org.sugarlabs.frame')
        self._palette_group = palettegroup.get_group('frame')

        self._left_panel = None
        self._right_panel = None
        self._top_panel = None
        self._bottom_panel = None

        self._wanted = False
        self.current_position = 0.0
        self._animator = None
        self._hide_timeout_id = 0
 
        self._event_area = EventArea(self.settings)
        self._event_area.connect('enter', self._enter_corner_cb)
        self._event_area.connect('leave', self._leave_corner_cb)
 
        self._top_panel = self._create_top_panel()
        self._bottom_panel = self._create_bottom_panel()
        self._left_panel = self._create_left_panel()
        self._right_panel = self._create_right_panel()

        for panel in (self._top_panel, self._bottom_panel,
                      self._left_panel, self._right_panel):
            if panel:
                controller = Gtk.EventControllerMotion.new()
                controller.connect('enter', self._panel_enter_cb, panel)
                controller.connect('leave', self._panel_leave_cb, panel)
                panel.add_controller(controller)

        from jarabe.model import shell
        shell_model = shell.get_model()
        if hasattr(shell_model, '_overlay') and shell_model._overlay:
            # Add event area hot corners
            for box in self._event_area._boxes.values():
                shell_model._overlay.add_overlay(box)
                box.set_visible(True)
                
            # Add frame panels
            shell_model._overlay.add_overlay(self._top_panel)
            shell_model._overlay.add_overlay(self._bottom_panel)
            shell_model._overlay.add_overlay(self._left_panel)
            shell_model._overlay.add_overlay(self._right_panel)



        display = Gdk.Display.get_default()
        if display:
            self._monitors = display.get_monitors()
            if self._monitors:
                self._monitors.connect('items-changed', self._size_changed_cb)
                for i in range(self._monitors.get_n_items()):
                    monitor = self._monitors.get_item(i)
                    monitor.connect('notify::geometry', self._monitor_geometry_changed_cb)

        self._notif_by_icon = {}

        notification_service = notifications.get_service()
        notification_service.notification_received.connect(
            self.__notification_received_cb)
        notification_service.notification_cancelled.connect(
            self.__notification_cancelled_cb)

    def is_visible(self):
        # Check if any panel is currently revealed
        for panel in (self._top_panel, self._bottom_panel,
                      self._left_panel, self._right_panel):
            if panel and panel.get_reveal_child():
                return True
        return False

    visible = property(is_visible, None)

    def toggle(self):
        if not self._wanted:
            self.show()
        else:
            self.hide()

    def hide(self):
        self._cancel_hide_timeout()
        if not self._wanted:
            return
        self._wanted = False
        palettegroup.popdown_all()
        for panel in (self._top_panel, self._bottom_panel,
                      self._left_panel, self._right_panel):
            if panel:
                panel.set_reveal_child(False)

    def show(self):
        self._cancel_hide_timeout()
        if self._wanted:
            return
        self._wanted = True
        for panel in (self._top_panel, self._bottom_panel,
                      self._left_panel, self._right_panel):
            if panel:
                panel.set_reveal_child(True)

    def _hide_windows(self):
        # No-op: Revealer handles hiding with slide animation.
        pass

    def move_panels(self, pos):
        # Legacy method kept for compatibility; not used with Revealer approach.
        self.current_position = pos

    def _create_top_panel(self):
        panel = self._create_panel(Gtk.PositionType.TOP)

        zoom_toolbar = ZoomToolbar()
        panel.append(zoom_toolbar, expand=False)
        zoom_toolbar.set_visible(True)
        zoom_toolbar.connect('level-clicked', self._level_clicked_cb)

        activities_tray = ActivitiesTray()
        panel.append(activities_tray)
        activities_tray.set_visible(True)

        return panel

    def _create_bottom_panel(self):
        panel = self._create_panel(Gtk.PositionType.BOTTOM)

        devices_tray = DevicesTray()
        panel.append(devices_tray)
        devices_tray.set_visible(True)

        return panel

    def _create_right_panel(self):
        panel = self._create_panel(Gtk.PositionType.RIGHT)

        tray = FriendsTray()
        panel.append(tray)
        tray.set_visible(True)

        return panel

    def _create_left_panel(self):
        panel = ClipboardPanelWindow(self, Gtk.PositionType.LEFT)
        return panel

    def _create_panel(self, orientation):
        panel = FrameWindow(orientation)
        return panel

    def _level_clicked_cb(self, zoom_toolbar):
        self.hide()

    def _update_position(self):
        # With Revealer approach, animation is handled by the Revealer widget.
        # This method is kept for compatibility (called on screen resize).
        # Ensure panels reflect wanted state after a resize.
        for panel in (self._top_panel, self._bottom_panel,
                      self._left_panel, self._right_panel):
            if panel is None:
                continue
            panel.set_reveal_child(self._wanted)

    def _size_changed_cb(self, monitors, position, removed, added):
        for i in range(added):
            monitor = monitors.get_item(position + i)
            if monitor:
                monitor.connect('notify::geometry', self._monitor_geometry_changed_cb)
        self._update_position()
        
    def _monitor_geometry_changed_cb(self, monitor, pspec):
        self._update_position()

    def _enter_corner_cb(self, event_area):
        self._cancel_hide_timeout()
        self.toggle()

    def _panel_enter_cb(self, controller, x, y, panel):
        panel.hover = True
        self._cancel_hide_timeout()

    def _panel_leave_cb(self, controller, panel):
        panel.hover = False
        self._check_auto_hide()

    def _leave_corner_cb(self, event_area):
        self._check_auto_hide()

    def _cancel_hide_timeout(self):
        if self._hide_timeout_id:
            GLib.source_remove(self._hide_timeout_id)
            self._hide_timeout_id = 0

    def _check_auto_hide(self):
        self._cancel_hide_timeout()
        # Schedule auto-hide check after 250ms
        self._hide_timeout_id = GLib.timeout_add(250, self._auto_hide_cb)

    def _auto_hide_cb(self):
        self._hide_timeout_id = 0
        any_hover = self._event_area._hover or \
                    (self._top_panel and getattr(self._top_panel, 'hover', False)) or \
                    (self._bottom_panel and getattr(self._bottom_panel, 'hover', False)) or \
                    (self._left_panel and getattr(self._left_panel, 'hover', False)) or \
                    (self._right_panel and getattr(self._right_panel, 'hover', False))
        
        if not any_hover and self._wanted:
            self.hide()
        return False

    def notify_key_press(self):
        self._cancel_hide_timeout()
        self.toggle()

    '''
    The function adds a notification and returns the id of the timeout
    signal after which the notification will dissapear.
    '''

    def add_notification(self, icon, corner=Gtk.CornerType.TOP_LEFT,
                         duration=NOTIFICATION_DURATION):

        if not isinstance(icon, NotificationIcon):
            raise TypeError('icon must be a NotificationIcon.')

        window = NotificationWindow()

        if corner == Gtk.CornerType.TOP_LEFT:
            window.set_halign(Gtk.Align.START)
            window.set_valign(Gtk.Align.START)
        elif corner == Gtk.CornerType.TOP_RIGHT:
            window.set_halign(Gtk.Align.END)
            window.set_valign(Gtk.Align.START)
        elif corner == Gtk.CornerType.BOTTOM_LEFT:
            window.set_halign(Gtk.Align.START)
            window.set_valign(Gtk.Align.END)
        elif corner == Gtk.CornerType.BOTTOM_RIGHT:
            window.set_halign(Gtk.Align.END)
            window.set_valign(Gtk.Align.END)

        window.append(icon)
        icon.set_visible(True)
        window.set_visible(True)

        from jarabe.model import shell
        shell_model = shell.get_model()
        if hasattr(shell_model, '_overlay') and shell_model._overlay:
            shell_model._overlay.add_overlay(window)

        self._notif_by_icon[icon] = window

        timeout_id = GLib.timeout_add(
            duration, lambda: self.remove_notification(icon))
        return timeout_id

    def remove_notification(self, icon):
        if icon not in self._notif_by_icon:
            logging.debug('icon %r not in list of notifications.', icon)
            return

        window = self._notif_by_icon[icon]
        parent = window.get_parent()
        if parent:
            if hasattr(parent, 'remove_overlay'):
                parent.remove_overlay(window)
            else:
                window.unparent()
        del self._notif_by_icon[icon]

    def __button_release_event_cb(self, gesture, n_press, x, y, icon):
        self.remove_notification(icon)
        self.show()

    def __notification_received_cb(self, **kwargs):
        logging.debug('__notification_received_cb')
        icon = NotificationIcon()
        icon.show_badge()
        
        click = Gtk.GestureClick.new()
        click.connect('released', self.__button_release_event_cb, icon)
        icon.add_controller(click)

        hints = kwargs['hints']

        icon_file_name = hints.get('x-sugar-icon-file-name', '')
        icon_name = hints.get('x-sugar-icon-name', '')
        if icon_file_name:
            icon.props.icon_filename = icon_file_name
        elif icon_name:
            icon.props.icon_name = icon_name
        else:
            icon.props.icon_name = 'application-octet-stream'

        icon_colors = hints.get('x-sugar-icon-colors', '')
        if not icon_colors:
            icon_colors = profile.get_color()
        icon.props.xo_color = icon_colors

        duration = kwargs.get('expire_timeout', -1)
        if duration == -1:
            duration = NOTIFICATION_DURATION

        self.add_notification(icon, Gtk.CornerType.TOP_LEFT, duration)

    def __notification_cancelled_cb(self, **kwargs):
        # point yet.
        pass
