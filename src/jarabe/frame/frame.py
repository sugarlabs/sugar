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
from gi.repository import GObject
from gi.repository import Gio

from sugar3.graphics import animator
from sugar3.graphics import style
from sugar3.graphics import palettegroup
from sugar3 import profile

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


class _Animation(animator.Animation):

    def __init__(self, frame, end):
        start = frame.current_position
        animator.Animation.__init__(self, start, end)
        self._frame = frame

    def next_frame(self, current):
        self._frame.move(current)


class Frame(object):

    def __init__(self):
        logging.debug('STARTUP: Loading the frame')

        self.settings = Gio.Settings('org.sugarlabs.frame')
        self._palette_group = palettegroup.get_group('frame')

        self._left_panel = None
        self._right_panel = None
        self._top_panel = None
        self._bottom_panel = None

        self._wanted = False
        self.current_position = 0.0
        self._animator = None

        self._event_area = EventArea(self.settings)
        self._event_area.connect('enter', self._enter_corner_cb)
        self._event_area.show()

        self._top_panel = self._create_top_panel()
        self._bottom_panel = self._create_bottom_panel()
        self._left_panel = self._create_left_panel()
        self._right_panel = self._create_right_panel()

        screen = Gdk.Screen.get_default()
        screen.connect('size-changed', self._size_changed_cb)

        self._notif_by_icon = {}

        notification_service = notifications.get_service()
        notification_service.notification_received.connect(
            self.__notification_received_cb)
        notification_service.notification_cancelled.connect(
            self.__notification_cancelled_cb)

    def is_visible(self):
        return self.current_position != 0.0

    visible = property(is_visible, None)

    def toggle(self):
        if not self._wanted:
            self.show()
        else:
            self.hide()

    def hide(self):
        if not self._wanted:
            return

        self._wanted = False

        if self._animator:
            self._animator.stop()

        palettegroup.popdown_all()
        self._animator = animator.Animator(0.5, widget=self._top_panel)
        self._animator.add(_Animation(self, 0.0))
        self._animator.start()

    def show(self):
        if self._wanted:
            return

        self._wanted = True

        if self._animator:
            self._animator.stop()

        self._animator = animator.Animator(0.5, widget=self._top_panel)
        self._animator.add(_Animation(self, 1.0))
        self._animator.start()

    def move(self, pos):
        self.current_position = pos
        self._update_position()

    def _create_top_panel(self):
        panel = self._create_panel(Gtk.PositionType.TOP)

        zoom_toolbar = ZoomToolbar()
        panel.append(zoom_toolbar, expand=False)
        zoom_toolbar.show()
        zoom_toolbar.connect('level-clicked', self._level_clicked_cb)

        activities_tray = ActivitiesTray()
        panel.append(activities_tray)
        activities_tray.show()

        return panel

    def _create_bottom_panel(self):
        panel = self._create_panel(Gtk.PositionType.BOTTOM)

        devices_tray = DevicesTray()
        panel.append(devices_tray)
        devices_tray.show()

        return panel

    def _create_right_panel(self):
        panel = self._create_panel(Gtk.PositionType.RIGHT)

        tray = FriendsTray()
        panel.append(tray)
        tray.show()

        return panel

    def _create_left_panel(self):
        panel = ClipboardPanelWindow(self, Gtk.PositionType.LEFT)

        return panel

    def _create_panel(self, orientation):
        panel = FrameWindow(orientation)

        return panel

    def _move_panel(self, panel, pos, x1, y1, x2, y2):
        x = (x2 - x1) * pos + x1
        y = (y2 - y1) * pos + y1

        panel.move(int(x), int(y))

        # FIXME we should hide and show as necessary to free memory
        if not panel.props.visible:
            panel.show()

    def _level_clicked_cb(self, zoom_toolbar):
        self.hide()

    def _update_position(self):
        screen_h = Gdk.Screen.height()
        screen_w = Gdk.Screen.width()

        self._move_panel(self._top_panel, self.current_position,
                         0, - self._top_panel.size, 0, 0)

        self._move_panel(self._bottom_panel, self.current_position,
                         0, screen_h, 0, screen_h - self._bottom_panel.size)

        self._move_panel(self._left_panel, self.current_position,
                         - self._left_panel.size, 0, 0, 0)

        self._move_panel(self._right_panel, self.current_position,
                         screen_w, 0, screen_w - self._right_panel.size, 0)

    def _size_changed_cb(self, screen):
        self._update_position()

    def _enter_corner_cb(self, event_area):
        self.toggle()

    def notify_key_press(self):
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

        screen = Gdk.Screen.get_default()
        if corner == Gtk.CornerType.TOP_LEFT:
            window.move(0, 0)
        elif corner == Gtk.CornerType.TOP_RIGHT:
            window.move(screen.get_width() - style.GRID_CELL_SIZE, 0)
        elif corner == Gtk.CornerType.BOTTOM_LEFT:
            window.move(0, screen.get_height() - style.GRID_CELL_SIZE)
        elif corner == Gtk.CornerType.BOTTOM_RIGHT:
            window.move(screen.get_width() - style.GRID_CELL_SIZE,
                        screen.get_height() - style.GRID_CELL_SIZE)
        else:
            raise ValueError('Inalid corner: %r' % corner)

        window.add(icon)
        icon.show()
        window.show()

        self._notif_by_icon[icon] = window

        timeout_id = GObject.timeout_add(
            duration, lambda: self.remove_notification(icon))
        return timeout_id

    def remove_notification(self, icon):
        if icon not in self._notif_by_icon:
            logging.debug('icon %r not in list of notifications.', icon)
            return

        window = self._notif_by_icon[icon]
        window.destroy()
        del self._notif_by_icon[icon]

    def __button_release_event_cb(self, icon, data=None):
        self.remove_notification(icon)
        self.show()

    def __notification_received_cb(self, **kwargs):
        logging.debug('__notification_received_cb')
        icon = NotificationIcon()
        icon.show_badge()
        icon.connect('button-release-event', self.__button_release_event_cb)

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
        # Do nothing for now. Our notification UI is so simple, there's no
        # point yet.
        pass
