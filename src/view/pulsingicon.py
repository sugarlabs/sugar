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

def _get_as_rgba(self, html_color):
    if html_color == 'none':
        return Color('#FFFFFF', alpha=1.0).get_rgba()
    else:
        return Color(html_color).get_rgba()

def _update_colors(self):
    if self._pulsing:
        base_stroke = self._get_as_rgba(self._base_color.get_stroke_color())
        pulse_stroke = self._get_as_rgba(self._pulse_color.get_stroke_color())
        base_fill = self._get_as_rgba(self._base_color.get_fill_color())
        pulse_fill = self._get_as_rgba(self._pulse_color.get_fill_color())

        self.props.stroke_color = \
                self._get_color(base_stroke, pulse_stroke).get_svg()
        self.props.fill_color = \
                self._get_color(base_fill, pulse_fill).get_svg()
    else:
        self.props.xo_color = self._base_color

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

class PulsingIcon(Icon):
    __gtype_name__ = 'SugarPulsingIcon'

    __gproperties__ = {
        'base-color'  : (object, None, None, gobject.PARAM_READWRITE),
        'pulse-color' : (object, None, None, gobject.PARAM_READWRITE),
        'pulsing'     : (bool, None, None, False, gobject.PARAM_READWRITE),
        'paused'      : (bool, None, None, False, gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs):
        self._base_color = None
        self._pulse_color = None
        self._pulse_hid = None
        self._paused = False
        self._pulsing = False
        self._level = 0
        self._phase = 0

        Icon.__init__(self, **kwargs)

        self._palette = None
        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette is not None:
            self._palette.destroy()

    # Hack for sharing code between CanvasPulsingIcon and PulsingIcon
    _get_as_rgba = _get_as_rgba
    _update_colors = _update_colors
    _get_color = _get_color

    def _start_pulsing(self, restart=False):
        if restart:
            self._phase = 0
        if self._pulse_hid is None:
            self._pulse_hid = gobject.timeout_add(_INTERVAL, self.__pulse_cb)

    def _stop_pulsing(self):
        if self._pulse_hid is not None:
            gobject.source_remove(self._pulse_hid)
            self._pulse_hid = None
        self.props.xo_color = self._base_color

    def __pulse_cb(self):
        self._phase += _STEP
        self._level = (math.sin(self._phase) + 1) / 2
        self._update_colors()

        return True

    def do_set_property(self, pspec, value):
        if pspec.name == 'base-color':
            if self._base_color != value:
                self._base_color = value
                self._update_colors()
        elif pspec.name == 'pulse-color':
            if self._pulse_color != value:
                self._pulse_color = value
                self._update_colors()
        elif pspec.name == 'pulsing':
            if self._pulsing != value:
                self._pulsing = value
                if self._pulsing:
                    self._start_pulsing(restart=True)
                else:
                    self._stop_pulsing()
        elif pspec.name == 'paused':
            if self._paused != value:
                self._paused = value
                if self._paused:
                    self._stop_pulsing()
                else:
                    self._start_pulsing(restart=False)
        else:
            Icon.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'base-color':
            return self._base_color
        elif pspec.name == 'pulse-color':
            return self._pulse_color
        elif pspec.name == 'pulsing':
            return self._pulsing
        elif pspec.name == 'paused':
            return self._paused
        else:
            return Icon.do_get_property(self, pspec)

    def _get_palette(self):
        return self._palette

    def _set_palette(self, palette):
        if self._palette is not None:
            self._palette.props.invoker = None
        self._palette = palette

    palette = property(_get_palette, _set_palette)

class CanvasPulsingIcon(CanvasIcon):
    __gtype_name__ = 'SugarCanvasPulsingIcon'

    __gproperties__ = {
        'base-color'  : (object, None, None, gobject.PARAM_WRITABLE),
        'pulse-color' : (object, None, None, gobject.PARAM_WRITABLE),
        'pulsing'     : (bool, None, None, False, gobject.PARAM_WRITABLE),
        'paused'      : (bool, None, None, False, gobject.PARAM_WRITABLE)
    }

    def __init__(self, **kwargs):
        self._base_color = None
        self._pulse_color = None
        self._pulse_hid = None
        self._paused = False
        self._pulsing = False
        self._level = 0
        self._phase = 0

        CanvasIcon.__init__(self, **kwargs)

    # Hack for sharing code between CanvasPulsingIcon and PulsingIcon
    _get_as_rgba = _get_as_rgba
    _update_colors = _update_colors
    _get_color = _get_color

    def _start_pulsing(self, restart=False):
        if restart:
            self._phase = 0
        if self._pulse_hid is None:
            self._pulse_hid = gobject.timeout_add(_INTERVAL, self.__pulse_cb)

    def _stop_pulsing(self):
        if self._pulse_hid is not None:
            gobject.source_remove(self._pulse_hid)
            self._pulse_hid = None
        self.props.xo_color = self._base_color

    def __pulse_cb(self):
        self._phase += _STEP
        self._level = (math.sin(self._phase) + 1) / 2
        self._update_colors()

        return True

    def do_set_property(self, pspec, value):
        if pspec.name == 'base-color':
            if self._base_color != value:
                self._base_color = value
                self._update_colors()
        elif pspec.name == 'pulse-color':
            if self._pulse_color != value:
                self._pulse_color = value
                self._update_colors()
        elif pspec.name == 'pulsing':
            if self._pulsing != value:
                self._pulsing = value
                if self._pulsing:
                    self._start_pulsing(restart=True)
                else:
                    self._stop_pulsing()
        elif pspec.name == 'paused':
            if self._paused != value:
                self._paused = value
                if self._paused:
                    self._stop_pulsing()
                else:
                    self._start_pulsing(restart=False)
        else:
            CanvasIcon.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'base-color':
            return self._base_color
        elif pspec.name == 'pulse-color':
            return self._pulse_color
        elif pspec.name == 'pulsing':
            return self._pulsing
        elif pspec.name == 'paused':
            return self._paused
        else:
            return CanvasIcon.do_get_property(self, pspec)
