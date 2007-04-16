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

from sugar.graphics import units
from sugar.graphics import animator
from sugar.graphics.spreadbox import SpreadBox

from view.home.MyIcon import MyIcon

class _Animation(animator.Animation):
    def __init__(self, icon, start_scale, end_scale):
        animator.Animation.__init__(self, 0.0, 1.0)

        self._icon = icon
        self.start_scale = start_scale
        self.end_scale = end_scale

    def next_frame(self, current):
        d = (self.end_scale - self.start_scale) * current
        self._icon.props.scale = self.start_scale + d

class TransitionBox(SpreadBox):
    __gtype_name__ = 'SugarTransitionBox'
    
    __gsignals__ = {
        'completed': (gobject.SIGNAL_RUN_FIRST,
                      gobject.TYPE_NONE, ([]))
    }
    
    def __init__(self):
        SpreadBox.__init__(self, background_color=0xe2e2e2ff)

        self._scale = units.XLARGE_ICON_SCALE

        self._my_icon = MyIcon(self._scale)
        self.set_center_item(self._my_icon)

        self._animator = animator.Animator(0.3, 30)
        self._animator.connect('completed', self._animation_completed_cb)

    def _animation_completed_cb(self, anim):
        self.emit('completed')

    def set_scale(self, scale):
        self._animator.remove_all()
        self._animator.add(_Animation(self._my_icon, self._scale, scale))
        self._animator.start()
        
        self._scale = scale

