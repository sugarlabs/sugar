# Copyright (C) 2008 One Laptop Per Child
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

import math

from gi.repository import GObject

from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon


_INTERVAL = 100
_STEP = math.pi / 10  # must be a fraction of pi, for clean caching
_MINIMAL_ALPHA_VALUE = 0.33


class Pulser(object):

    def __init__(self, icon, interval=_INTERVAL):
        self._pulse_hid = None
        self._icon = icon
        self._interval = interval
        self._phase = 0
        self._start_scale = 1.0
        self._end_scale = 1.0
        self._zoom_steps = 1
        self._current_zoom_step = 1
        self._current_scale_step = 1

    def set_zooming(self, start_scale, end_scale, zoom_steps):
        """ Set start and end scale and number of steps in zoom animation """
        self._start_scale = start_scale
        self._end_scale = end_scale
        self._zoom_steps = zoom_steps
        self._current_scale_step = abs(self._start_scale - self._end_scale) / \
            self._zoom_steps
        self._icon.scale = self._start_scale

    def start(self, restart=False):
        if restart:
            self._phase = 0
        if self._pulse_hid is None:
            self._pulse_hid = GObject.timeout_add(self._interval,
                                                  self.__pulse_cb)
        if self._start_scale != self._end_scale:
            self._icon.scale = self._start_scale + \
                self._current_scale_step * self._current_zoom_step

    def stop(self):
        if self._pulse_hid is not None:
            GObject.source_remove(self._pulse_hid)
            self._pulse_hid = None
        self._icon.xo_color = self._icon.get_base_color()
        self._phase = 0
        self._icon.alpha = 1.0

    def update(self):
        self._icon.xo_color = self._icon.base_color
        self._icon.alpha = _MINIMAL_ALPHA_VALUE + \
            (1 - _MINIMAL_ALPHA_VALUE) * (math.cos(self._phase) + 1) / 2

    def __pulse_cb(self):
        self._phase += _STEP
        if self._current_zoom_step <= self._zoom_steps and \
                self._start_scale != self._end_scale:
            self._icon.scale = self._start_scale + \
                self._current_scale_step * self._current_zoom_step
            self._current_zoom_step += 1
        self.update()
        return True


class PulsingIcon(Icon):
    __gtype_name__ = 'SugarPulsingIcon'

    def __init__(self, interval=_INTERVAL, **kwargs):
        self._pulser = Pulser(self, interval)
        self._base_color = None
        self._pulse_color = None
        self._paused = False
        self._pulsing = False

        Icon.__init__(self, **kwargs)

        self._palette = None
        self.connect('destroy', self.__destroy_cb)

    def set_pulse_color(self, pulse_color):
        self._pulse_color = pulse_color
        self._pulser.update()

    def get_pulse_color(self):
        return self._pulse_color

    pulse_color = GObject.property(
        type=object, getter=get_pulse_color, setter=set_pulse_color)

    def set_base_color(self, base_color):
        self._base_color = base_color
        self._pulser.update()

    def get_base_color(self):
        return self._base_color

    def set_zooming(self, start_size=style.SMALL_ICON_SIZE,
                    end_size=style.XLARGE_ICON_SIZE,
                    zoom_steps=10):
        if start_size > end_size:
            start_scale = 1.0
            end_scale = float(end_size) / start_size
        else:
            start_scale = float(start_size) / end_size
            end_scale = 1.0
        self._pulser.set_zooming(start_scale, end_scale, zoom_steps)

    base_color = GObject.property(
        type=object, getter=get_base_color, setter=set_base_color)

    def set_paused(self, paused):
        self._paused = paused

        if self._paused:
            self._pulser.stop()
        else:
            self._pulser.start(restart=False)

    def get_paused(self):
        return self._paused

    paused = GObject.property(
        type=bool, default=False, getter=get_paused, setter=set_paused)

    def set_pulsing(self, pulsing):
        self._pulsing = pulsing

        if self._pulsing:
            self._pulser.start(restart=True)
        else:
            self._pulser.stop()

    def get_pulsing(self):
        return self._pulsing

    pulsing = GObject.property(
        type=bool, default=False, getter=get_pulsing, setter=set_pulsing)

    def _get_palette(self):
        return self._palette

    def _set_palette(self, palette):
        if self._palette is not None:
            self._palette.props.invoker = None
        self._palette = palette

    palette = property(_get_palette, _set_palette)

    def __destroy_cb(self, icon):
        self._pulser.stop()
        if self._palette is not None:
            self._palette.destroy()


class EventPulsingIcon(CanvasIcon):
    __gtype_name__ = 'SugarEventPulsingIcon'

    def __init__(self, interval=_INTERVAL, **kwargs):
        self._pulser = Pulser(self, interval)
        self._base_color = None
        self._pulse_color = None
        self._paused = False
        self._pulsing = False

        CanvasIcon.__init__(self, **kwargs)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, box):
        self._pulser.stop()

    def set_pulse_color(self, pulse_color):
        self._pulse_color = pulse_color
        self._pulser.update()

    def get_pulse_color(self):
        return self._pulse_color

    pulse_color = GObject.property(
        type=object, getter=get_pulse_color, setter=set_pulse_color)

    def set_base_color(self, base_color):
        self._base_color = base_color
        self._pulser.update()

    def get_base_color(self):
        return self._base_color

    base_color = GObject.property(
        type=object, getter=get_base_color, setter=set_base_color)

    def set_paused(self, paused):
        self._paused = paused

        if self._paused:
            self._pulser.stop()
        elif self._pulsing:
            self._pulser.start(restart=False)

    def get_paused(self):
        return self._paused

    paused = GObject.property(
        type=bool, default=False, getter=get_paused, setter=set_paused)

    def set_pulsing(self, pulsing):
        self._pulsing = pulsing
        if self._paused:
            return

        if self._pulsing:
            self._pulser.start(restart=True)
        else:
            self._pulser.stop()

    def get_pulsing(self):
        return self._pulsing

    pulsing = GObject.property(
        type=bool, default=False, getter=get_pulsing, setter=set_pulsing)
