# Copyright (C) 2006, Red Hat, Inc.
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
import gtk
import gobject
import hippo

from view.frame.eventframe import EventFrame
from view.frame.ActivitiesBox import ActivitiesBox
from view.frame.ZoomBox import ZoomBox
from view.frame.overlaybox import OverlayBox
from view.frame.FriendsBox import FriendsBox
from view.frame.PanelWindow import PanelWindow
from view.frame.clipboardpanelwindow import ClipboardPanelWindow
from view.frame.notificationtray import NotificationTray
from model.ShellModel import ShellModel
from sugar.graphics.timeline import Timeline
from sugar.graphics.grid import Grid
from sugar.graphics.menushell import MenuShell

_ANIMATION = True

class Frame:
    INACTIVE = 0
    TEMPORARY = 1
    STICKY = 2
    HIDE_ON_LEAVE = 3
    AUTOMATIC = 4

    def __init__(self, shell):
        self._left_panel = None
        self._right_panel = None
        self._top_panel = None
        self._bottom_panel = None

        self._hover_frame = False
        self._shell = shell
        self._mode = Frame.INACTIVE
        self._grid = Grid()

        self._timeline = Timeline(self)
        self._timeline.add_tag('slide_in', 18, 24)
        self._timeline.add_tag('before_slide_out', 48, 48)
        self._timeline.add_tag('slide_out', 49, 54)

        self._event_frame = EventFrame()
        self._event_frame.connect('enter-edge', self._enter_edge_cb)
        self._event_frame.connect('enter-corner', self._enter_corner_cb)
        self._event_frame.connect('leave', self._event_frame_leave_cb)
        self._event_frame.show()

        self._create_top_panel()
        self._create_bottom_panel()
        self._create_left_panel()
        self._create_right_panel()

        shell.get_model().connect('notify::state',
                                  self._shell_state_changed_cb)

    def _create_top_panel(self):
        self._top_panel = self._create_panel(16, 1)
        menu_shell = self._top_panel.get_menu_shell()
        root = self._top_panel.get_root()

        menu_shell.set_position(MenuShell.BOTTOM)

        box = ZoomBox(self._shell, menu_shell)

        [x, y] = self._grid.point(1, 0)
        root.append(box, hippo.PACK_FIXED)
        root.set_position(box, x, y)

        tray = NotificationTray()
        tray_box = hippo.CanvasBox(box_width=self._grid.dimension(1),
                                   box_height=self._grid.dimension(1),
                                   xalign=hippo.ALIGNMENT_END)

        tray_widget = hippo.CanvasWidget()
        tray_widget.props.widget = tray
        tray_box.append(tray_widget, gtk.EXPAND)

        [x, y] = self._grid.point(13, 0)
        root.append(tray_box, hippo.PACK_FIXED)
        root.set_position(tray_box, x, y)

        box = OverlayBox(self._shell)

        [x, y] = self._grid.point(14, 0)
        root.append(box, hippo.PACK_FIXED)
        root.set_position(box, x, y)

    def _create_bottom_panel(self):
        self._bottom_panel = self._create_panel(16, 1)
        menu_shell = self._bottom_panel.get_menu_shell()
        root = self._bottom_panel.get_root()

        menu_shell.set_position(MenuShell.TOP)

        box = ActivitiesBox(self._shell)
        root.append(box, hippo.PACK_FIXED)

        [x, y] = self._grid.point(1, 0)
        root.set_position(box, x, y)

    def _create_right_panel(self):
        self._right_panel = self._create_panel(1, 10)
        menu_shell = self._right_panel.get_menu_shell()
        root = self._right_panel.get_root()

        menu_shell.set_position(MenuShell.LEFT)

        box = FriendsBox(self._shell, menu_shell)
        root.append(box)

    def _create_left_panel(self):
        self._left_panel = ClipboardPanelWindow(
            self, self._grid.dimension(1), self._grid.dimension(10))

        self._connect_to_panel(self._left_panel)
        self._left_panel.connect('drag-motion', self._drag_motion_cb)
        self._left_panel.connect('drag-leave', self._drag_leave_cb)

    def _shell_state_changed_cb(self, model, pspec):
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            self._timeline.goto('slide_out', True)
        
    def _create_panel(self, width, height):
        panel = PanelWindow(self._grid.dimension(width),
                            self._grid.dimension(height))
        self._connect_to_panel(panel)

        return panel

    def _move_panel(self, panel, x1, y1, x2, y2, pos):
        [screen_x1, screen_y1] = self._grid.point(x1, y1)
        [screen_x2, screen_y2] = self._grid.point(x2, y2)

        screen_x = (screen_x2 - screen_x1) * pos + screen_x1
        screen_y = (screen_y2 - screen_y1) * pos + screen_y1

        panel.move(int(screen_x), int(screen_y))

        # FIXME we should hide and show as necessary to free memory
        if not panel.props.visible:
            panel.show()

    def _connect_to_panel(self, panel):
        panel.connect('enter-notify-event', self._enter_notify_cb)
        panel.connect('leave-notify-event', self._leave_notify_cb)

        menu_shell = panel.get_menu_shell()
        menu_shell.connect('activated',
                           self._menu_shell_activated_cb)
        menu_shell.connect('deactivated',
                           self._menu_shell_deactivated_cb)

    def _menu_shell_activated_cb(self, menu_shell):
        self._timeline.goto('slide_in', True)

    def _menu_shell_deactivated_cb(self, menu_shell):
        if self._mode != Frame.STICKY and not self._hover_frame:
            self._timeline.play('before_slide_out', 'slide_out')

    def _enter_notify_cb(self, window, event):
        self._enter_notify()
        logging.debug('Frame._enter_notify_cb ' + str(self._mode))
        
    def _drag_motion_cb(self, window, context, x, y, time):
        self._enter_notify()
        logging.debug('Frame._drag_motion_cb ' + str(self._mode))
        return True
        
    def _drag_leave_cb(self, window, drag_context, timestamp):
        self._leave_notify(window)
        logging.debug('Frame._drag_leave_cb ' + str(self._mode))
            
    def _leave_notify_cb(self, window, event):
        # FIXME for some reason every click cause also a leave-notify
        if event.state == gtk.gdk.BUTTON1_MASK:
            return

        self._leave_notify(window)
        logging.debug('Frame._leave_notify_cb ' + str(self._mode))

    def _enter_notify(self):
        self._hover_frame = True
        self._timeline.goto('slide_in', True) 
               
    def _leave_notify(self, panel):
        self._hover_frame = False
        if not panel.get_menu_shell().is_active() and \
           (self._mode == Frame.HIDE_ON_LEAVE or \
            self._mode == Frame.AUTOMATIC):
            self._timeline.play('before_slide_out', 'slide_out')

    def _enter_edge_cb(self, event_frame):
        self._mode = Frame.HIDE_ON_LEAVE
        self._timeline.play(None, 'slide_in')
        logging.debug('Frame._enter_edge_cb ' + str(self._mode))
        
    def _enter_corner_cb(self, event_frame):
        self._mode = Frame.HIDE_ON_LEAVE
        self._timeline.play('slide_in', 'slide_in')
        logging.debug('Frame._enter_corner_cb ' + str(self._mode))
        
    def _event_frame_leave_cb(self, event_frame):
        if self._mode != Frame.STICKY:
            self._timeline.goto('slide_out', True)
        logging.debug('Frame._event_frame_leave_cb ' + str(self._mode))
        
    def show_and_hide(self, seconds):
        self._mode = Frame.AUTOMATIC
        self._timeline.play()

    def notify_key_press(self):
        if self._timeline.on_tag('slide_in'):
            self._timeline.play('before_slide_out', 'slide_out')
        elif self._timeline.on_tag('before_slide_out'):
            self._mode = Frame.TEMPORARY
        else:
            self._mode = Frame.STICKY
            self._timeline.play('slide_in', 'slide_in')

    def notify_key_release(self):
        if self._mode == Frame.TEMPORARY:
            self._timeline.play('before_slide_out', 'slide_out')

    def _move(self, pos):
        self._move_panel(self._top_panel, 0, -1, 0, 0, pos)
        self._move_panel(self._bottom_panel, 0, 12, 0, 11, pos)
        self._move_panel(self._left_panel, -1, 1, 0, 1, pos)
        self._move_panel(self._right_panel, 16, 1, 15, 1, pos)

    def do_slide_in(self, current=0, n_frames=0):
        if _ANIMATION:
            self._move(float(current + 1) / float(n_frames))
        elif current == 0:
            self._move(1)
        if self._event_frame.is_visible():
            self._event_frame.hide()

    def do_slide_out(self, current=0, n_frames=0):
        if _ANIMATION:
            self._move(1 - (float(current + 1) / float(n_frames)))
        elif current == 0:
            self._move(0)
        if not self._event_frame.is_visible():
            self._event_frame.show()

    def is_visible(self):
        return self._top_panel.props.visible
