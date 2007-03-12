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
from view.frame.framepopupcontext import FramePopupContext
from model.ShellModel import ShellModel
from sugar.graphics import animator
from sugar.graphics import units

STATE_SHOWING = 0
STATE_HIDING  = 1

MODE_NONE            = 0
MODE_MOUSE           = 1
MODE_KEYBOARD        = 2
MODE_NOT_INTERACTIVE = 3

_FRAME_HIDING_DELAY = 500

class _Animation(animator.Animation):
    def __init__(self, frame, end):
        start = frame.get_current_position()
        animator.Animation.__init__(self, start, end)
        self._frame = frame

    def next_frame(self, current):
        self._frame.move(current)

class _MouseListener(object):
    def __init__(self, frame):
        self._frame = frame
        self._hide_sid = 0

    def mouse_enter(self):
        if self._frame.mode == MODE_NONE:
            self._show_frame()

    def mouse_leave(self):
        if self._frame.mode == MODE_MOUSE:
            self._hide_frame()

    def _show_frame(self):
        if self._hide_sid != 0:
            gobject.source_remove(self._hide_sid)
        self._frame.show()
        self._frame.mode = MODE_MOUSE

    def _hide_frame_timeout_cb(self):
        self._frame.hide()
        return False

    def _hide_frame(self):
        if self._hide_sid != 0:
            gobject.source_remove(self._hide_sid)
        self._hide_sid = gobject.timeout_add(
                  _FRAME_HIDING_DELAY, self._hide_frame_timeout_cb)

class _KeyListener(object):
    def __init__(self, frame):
        self._frame = frame
        self._hide_sid = 0

    def key_press(self):
        if self._frame.mode != MODE_NONE and \
           self._frame.mode != MODE_KEYBOARD:
            return

        if self._frame.state == STATE_SHOWING:
            self._hide_frame()
        else:
            self._show_frame()

    def key_release(self):
        self._hide_frame()

    def _hide_frame_timeout_cb(self):
        self._frame.hide()
        return False

    def _show_frame(self):
        if self._hide_sid != 0:
            gobject.source_remove(self._hide_sid)
        self._frame.show()
        self._frame.mode = MODE_KEYBOARD

    def _hide_frame(self):
        if self._hide_sid != 0:
            gobject.source_remove(self._hide_sid)
        self._hide_sid = gobject.timeout_add(
                        100, self._hide_frame_timeout_cb)

class Frame(object):
    def __init__(self, shell):
        self.mode = MODE_NONE
        self.state = STATE_HIDING

        self._left_panel = None
        self._right_panel = None
        self._top_panel = None
        self._bottom_panel = None

        self._shell = shell
        self._current_position = 0.0
        self._animator = None
        self._hover = False

        self._event_frame = EventFrame()
        self._event_frame.connect('enter-corner', self._enter_corner_cb)
        self._event_frame.show()

        self._popup_context = FramePopupContext()
        self._popup_context.connect('activated',
                                    self._popup_context_activated_cb)
        self._popup_context.connect('deactivated',
                                    self._popup_context_deactivated_cb)

        self._top_panel = self._create_top_panel()
        self._bottom_panel = self._create_bottom_panel()
        self._left_panel = self._create_left_panel()
        self._right_panel = self._create_right_panel()

        shell.get_model().connect('notify::state',
                                  self._shell_state_changed_cb)
                                  
        screen = gtk.gdk.screen_get_default()
        screen.connect('size-changed', self._size_changed_cb)

        self._key_listener = _KeyListener(self)
        self._mouse_listener = _MouseListener(self)

    def hide(self):
        if self.state == STATE_HIDING:
            return
        if self._animator:
            self._animator.stop()

        self._animator = animator.Animator(0.5, 30, animator.EASE_OUT_EXPO)
        self._animator.add(_Animation(self, 0.0))
        self._animator.start()

        self._event_frame.show()

        self.state = STATE_HIDING
        self.mode = MODE_NONE

    def show(self):
        if self.state == STATE_SHOWING:
            return
        if self._animator:
            self._animator.stop()

        self._animator = animator.Animator(0.5, 30, animator.EASE_OUT_EXPO)
        self._animator.add(_Animation(self, 1.0))
        self._animator.start()

        self._event_frame.hide()

        self.state = STATE_SHOWING
        self.mode = MODE_NOT_INTERACTIVE

    def get_popup_context(self):
        return self._popup_context

    def get_current_position(self):
        return self._current_position

    def move(self, pos):
        self._current_position = pos
        self._update_position()

    def _is_hover(self):
        return (self._top_panel.hover or \
                self._bottom_panel.hover or \
                self._left_panel.hover or \
                self._right_panel.hover)

    def _create_top_panel(self):
        panel = self._create_panel(hippo.ORIENTATION_HORIZONTAL)
        root = panel.get_root()

        box = ZoomBox(self._shell, self._popup_context)
        root.append(box)

        box = OverlayBox(self._shell)
        root.append(box, hippo.PACK_END)

        return panel

    def _create_bottom_panel(self):
        panel = self._create_panel(hippo.ORIENTATION_HORIZONTAL)
        root = panel.get_root()

        box = ActivitiesBox(self._shell, self._popup_context)
        root.append(box)

        return panel

    def _create_right_panel(self):
        panel = self._create_panel(hippo.ORIENTATION_VERTICAL)
        root = panel.get_root()

        box = FriendsBox(self._shell, self._popup_context)
        root.append(box)

        return panel

    def _create_left_panel(self):
        panel = ClipboardPanelWindow(self, hippo.ORIENTATION_VERTICAL)

        self._connect_to_panel(panel)
        panel.connect('drag-motion', self._drag_motion_cb)
        panel.connect('drag-leave', self._drag_leave_cb)

        return panel

    def _shell_state_changed_cb(self, model, pspec):
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            self._timeline.goto('slide_out', True)
        
    def _create_panel(self, orientation):
        panel = PanelWindow(orientation)
        self._connect_to_panel(panel)

        return panel

    def _move_panel(self, panel, pos, x1, y1, x2, y2):
        x = (x2 - x1) * pos + x1
        y = (y2 - y1) * pos + y1

        panel.move(int(x), int(y))

        # FIXME we should hide and show as necessary to free memory
        if not panel.props.visible:
            panel.show()

    def _connect_to_panel(self, panel):
        panel.connect('enter-notify-event', self._enter_notify_cb)
        panel.connect('leave-notify-event', self._leave_notify_cb)

    def _update_position(self):
        screen_h = gtk.gdk.screen_height()
        screen_w = gtk.gdk.screen_width()

        self._move_panel(self._top_panel, self._current_position,
                         0, units.grid_to_pixels(-1),
                         0, 0)

        self._move_panel(self._bottom_panel, self._current_position,
                         0, screen_h,
                         0, screen_h - units.grid_to_pixels(1))

        self._move_panel(self._left_panel, self._current_position,
                         units.grid_to_pixels(-1), 0,
                         0, 0)

        self._move_panel(self._right_panel, self._current_position,
                         screen_w, 0,
                         screen_w - units.grid_to_pixels(1), 0)

    def _size_changed_cb(self, screen):
       self._update_position()
               
    def _popup_context_activated_cb(self, popup_context):
        self._mouse_listener.mouse_enter()

    def _popup_context_deactivated_cb(self, popup_context):
        if not self._hover:
            self._mouse_listener.mouse_leave()

    def _enter_notify_cb(self, window, event):
        if self._hover:
            return

        self._hover = True
        self._mouse_listener.mouse_enter()

    def _leave_notify_cb(self, window, event):
        if not self._hover:
            return

        if not self._is_hover():
            self._hover = False
            if not self._popup_context.is_active():
                self._mouse_listener.mouse_leave()
        
    def _drag_motion_cb(self, window, context, x, y, time):
        self._mouse_listener.mouse_enter()
        
    def _drag_leave_cb(self, window, drag_context, timestamp):
        self._mouse_listener.mouse_leave()
            
    def _enter_corner_cb(self, event_frame):
        self._mouse_listener.mouse_enter()
        
    def notify_key_press(self):
        self._key_listener.key_press()

    def notify_key_release(self):
        self._key_listener.key_release()
