# Copyright (C) 2008, Red Hat, Inc.
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
import logging

from sugar.graphics import style
from sugar.graphics import animator
from sugar.graphics.xocolor import XoColor

from model import shellmodel
from view.pulsingicon import CanvasPulsingIcon

class LaunchBox(hippo.CanvasBox):
    def __init__(self):
        gobject.GObject.__init__(
                self, background_color=style.COLOR_WHITE.get_int())

        self._activity_icon = CanvasPulsingIcon()

        # FIXME support non-xo colors in CanvasPulsingIcon
        self._activity_icon.props.base_color = \
            XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                               style.COLOR_TRANSPARENT.get_svg()))

        vbox = hippo.CanvasBox(orientation=hippo.ORIENTATION_VERTICAL)
        vbox.append(self._activity_icon, hippo.PACK_EXPAND)
        self.append(vbox, hippo.PACK_EXPAND)

        self._animator = animator.Animator(1.0)

        self._home = shellmodel.get_instance().get_home()
        self._home.connect('active-activity-changed',
                           self.__active_activity_changed_cb)

        self._update_icon()

    def zoom_in(self):
        logging.debug('zooming in to activity')

        self._activity_icon.props.size = style.STANDARD_ICON_SIZE

        self._animator.remove_all()
        self._animator.add(_Animation(self._activity_icon,
                                      style.STANDARD_ICON_SIZE,
                                      style.XLARGE_ICON_SIZE))
        self._animator.start()

        logging.debug('starting pulse')

        self._activity_icon.props.pulsing = True

    def suspend(self):
        self._activity_icon.props.paused = True

    def resume(self):
        self._activity_icon.props.paused = False

    def _update_icon(self):
        activity = self._home.get_active_activity()
        if activity:
            self._activity_icon.props.file_name = activity.get_icon_path()
            self._activity_icon.props.pulse_color = activity.get_icon_color()
        else:
            self._activity_icon.props.file_name = None

    def __active_activity_changed_cb(self, model, activity):
        self._update_icon()

class _Animation(animator.Animation):
    def __init__(self, icon, start_size, end_size):
        animator.Animation.__init__(self, 0.0, 1.0)

        self._icon = icon
        self.start_size = start_size
        self.end_size = end_size

    def next_frame(self, current):
        d = (self.end_size - self.start_size) * current
        self._icon.props.size = self.start_size + d
