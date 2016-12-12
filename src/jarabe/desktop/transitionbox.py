# Copyright (C) 2007, Red Hat, Inc.
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

from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics import animator
from sugar3.graphics.icon import Icon

from jarabe.model.buddy import get_owner_instance
from jarabe.desktop.viewcontainer import ViewContainer
from jarabe.desktop.favoriteslayout import SpreadLayout


class _Animation(animator.Animation):

    def __init__(self, icon, start_size, end_size):
        animator.Animation.__init__(self, 0.0, 1.0)

        self._icon = icon
        self.start_size = start_size
        self.end_size = end_size

    def next_frame(self, current):
        d = (self.end_size - self.start_size) * current
        self._icon.props.pixel_size = int(self.start_size + d)


class TransitionBox(ViewContainer):
    __gtype_name__ = 'SugarTransitionBox'

    __gsignals__ = {
        'completed': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        layout = SpreadLayout()

        # Round off icon size to an even number to ensure that the icon
        owner = get_owner_instance()
        self._owner_icon = Icon(icon_name='computer-xo',
                                xo_color=owner.get_color(),
                                pixel_size=style.XLARGE_ICON_SIZE & ~1)
        ViewContainer.__init__(self, layout, self._owner_icon)

        self._animator = animator.Animator(0.3, widget=self)
        self._animator.connect('completed', self._animation_completed_cb)

    def _animation_completed_cb(self, anim):
        self.emit('completed')

    def start_transition(self, start_size, end_size):
        self._animator.remove_all()
        self._animator.add(_Animation(self._owner_icon, start_size, end_size))
        self._animator.start()
