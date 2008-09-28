# Copyright (C) 2008 One Laptop Per Child
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

import math

import gobject

from sugar.graphics.icon import Icon, CanvasIcon
from sugar.graphics.style import Color

_INTERVAL = 100
_STEP = math.pi / 10  # must be a fraction of pi, for clean caching

class Pulser(object):
    def __init__(self, icon):
        self._pulse_hid = None
        self._icon = icon
        self._level = 0
        self._phase = 0

    def start(self, restart=False):
        if restart:
            self._phase = 0
        if self._pulse_hid is None:
            self._pulse_hid = gobject.timeout_add(_INTERVAL, self.__pulse_cb)

    def stop(self):
        if self._pulse_hid is not None:
            gobject.source_remove(self._pulse_hid)
            self._pulse_hid = None
        self._icon.xo_color = self._icon.base_color

    def update(self):
        if self._icon.pulsing:
            base_color = self._icon.base_color
            pulse_color = self._icon.pulse_color

            base_stroke = self._get_as_rgba(base_color.get_stroke_color())
            pulse_stroke = self._get_as_rgba(pulse_color.get_stroke_color())
            base_fill = self._get_as_rgba(base_color.get_fill_color())
            pulse_fill = self._get_as_rgba(pulse_color.get_fill_color())

            self._icon.stroke_color = \
                    self._get_color(base_stroke, pulse_stroke).get_svg()
            self._icon.fill_color = \
                    self._get_color(base_fill, pulse_fill).get_svg()
        else:
            self._icon.xo_color = self._icon.base_color

    def _get_as_rgba(self, html_color):
        if html_color == 'none':
            return Color('#FFFFFF', alpha=1.0).get_rgba()
        else:
            return Color(html_color).get_rgba()

    def _get_color(self, orig_color, target_color):
        next_point = (orig_color[0] +
                      self._level * (target_color[0] - orig_color[0]),
                      orig_color[1] +
                      self._level * (target_color[1] - orig_color[1]),
                      orig_color[2] +
                      self._level * (target_color[2] - orig_color[2]))

        return Color('#%02x%02x%02x' % (int(next_point[0] * 255),
                                        int(next_point[1] * 255),
                                        int(next_point[2] * 255)))

    def __pulse_cb(self):
        self._phase += _STEP
        self._level = (math.sin(self._phase) + 1) / 2
        self.update()

        return True

class PulsingIcon(Icon):
    __gtype_name__ = 'SugarPulsingIcon'

    def __init__(self, **kwargs):
        self._pulser = Pulser(self)
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

    pulse_color = gobject.property(
        type=object, getter=get_pulse_color, setter=set_pulse_color)

    def set_base_color(self, base_color):
        self._base_color = base_color
        self._pulser.update()

    def get_base_color(self):
        return self._base_color

    base_color = gobject.property(
        type=object, getter=get_base_color, setter=set_base_color)

    def set_paused(self, paused):
        self._paused = paused

        if self._paused:
            self._pulser.stop()
        else:
            self._pulser.start(restart=False)

    def get_paused(self):
        return self._paused

    paused = gobject.property(
        type=bool, default=False, getter=get_paused, setter=set_paused)

    def set_pulsing(self, pulsing):
        self._pulsing = pulsing

        if self._pulsing:
            self._pulser.start(restart=True)
        else:
            self._pulser.stop()    

    def get_pulsing(self):
        return self._pulsing

    pulsing = gobject.property(
        type=bool, default=False, getter=get_pulsing, setter=set_pulsing)

    def _get_palette(self):
        return self._palette

    def _set_palette(self, palette):
        if self._palette is not None:
            self._palette.props.invoker = None
        self._palette = palette

    palette = property(_get_palette, _set_palette)

    def __destroy_cb(self, icon):
        if self._palette is not None:
            self._palette.destroy()

class CanvasPulsingIcon(CanvasIcon):
    __gtype_name__ = 'SugarCanvasPulsingIcon'

    def __init__(self, **kwargs):
        self._pulser = Pulser(self)
        self._base_color = None
        self._pulse_color = None
        self._paused = False
        self._pulsing = False

        CanvasIcon.__init__(self, **kwargs)

    def set_pulse_color(self, pulse_color):
        self._pulse_color = pulse_color
        self._pulser.update()

    def get_pulse_color(self):
        return self._pulse_color

    pulse_color = gobject.property(
        type=object, getter=get_pulse_color, setter=set_pulse_color)

    def set_base_color(self, base_color):
        self._base_color = base_color
        self._pulser.update()

    def get_base_color(self):
        return self._base_color

    base_color = gobject.property(
        type=object, getter=get_base_color, setter=set_base_color)

    def set_paused(self, paused):
        self._paused = paused

        if self._paused:
            self._pulser.stop()
        else:
            self._pulser.start(restart=False)

    def get_paused(self):
        return self._paused

    paused = gobject.property(
        type=bool, default=False, getter=get_paused, setter=set_paused)

    def set_pulsing(self, pulsing):
        self._pulsing = pulsing

        if self._pulsing:
            self._pulser.start(restart=True)
        else:
            self._pulser.stop()    

    def get_pulsing(self):
        return self._pulsing

    pulsing = gobject.property(
        type=bool, default=False, getter=get_pulsing, setter=set_pulsing)
