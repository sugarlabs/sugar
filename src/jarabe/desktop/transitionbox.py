# Copyright (C) 2007, Red Hat, Inc.
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

import hippo
import gobject

from sugar.graphics import style
from sugar.graphics import animator

from jarabe.desktop.myicon import MyIcon

class _Animation(animator.Animation):
    def __init__(self, icon, start_size, end_size):
        animator.Animation.__init__(self, 0.0, 1.0)

        self._icon = icon
        self.start_size = start_size
        self.end_size = end_size

    def next_frame(self, current):
        d = (self.end_size - self.start_size) * current
        self._icon.props.size = self.start_size + d

class _Layout(gobject.GObject, hippo.CanvasLayout):
    __gtype_name__ = 'SugarTransitionBoxLayout'
    def __init__(self):
        gobject.GObject.__init__(self)
        self._box = None

    def do_set_box(self, box):
        self._box = box

    def do_get_height_request(self, for_width):
        return 0, 0

    def do_get_width_request(self):
        return 0, 0

    def do_allocate(self, x, y, width, height,
                    req_width, req_height, origin_changed):
        for child in self._box.get_layout_children():
            min_width, child_width = child.get_width_request()
            min_height, child_height = child.get_height_request(child_width)

            child.allocate(x + (width - child_width) / 2,
                           y + (height - child_height) / 2,
                           child_width, child_height, origin_changed)

class TransitionBox(hippo.Canvas):
    __gtype_name__ = 'SugarTransitionBox'
    
    __gsignals__ = {
        'completed': (gobject.SIGNAL_RUN_FIRST,
                      gobject.TYPE_NONE, ([]))
    }
    
    def __init__(self):
        gobject.GObject.__init__(self)

        self._box = hippo.CanvasBox()
        self._box.props.background_color = style.COLOR_WHITE.get_int()
        self.set_root(self._box)

        self._size = style.XLARGE_ICON_SIZE

        self._layout = _Layout()
        self._box.set_layout(self._layout)

        self._my_icon = MyIcon(self._size)
        self._box.append(self._my_icon)

        self._animator = animator.Animator(0.3)
        self._animator.connect('completed', self._animation_completed_cb)

    def _animation_completed_cb(self, anim):
        self.emit('completed')

    def set_size(self, size):
        self._animator.remove_all()
        self._animator.add(_Animation(self._my_icon, self._size, size))
        self._animator.start()
        
        self._size = size

