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

import gobject

from sugar.graphics.canvasicon import CanvasIcon

class PulsingIcon(CanvasIcon):
    __gproperties__ = {
        'paused'     : (bool, None, None, False,
                        gobject.PARAM_READWRITE),
        'colors'     : (object, None, None,
                        gobject.PARAM_READWRITE),
        'pulse-time' : (float, None, None,
                        0.0, 500.0, 0.0,
                        gobject.PARAM_READWRITE),
    }

    def __init__(self, **kwargs):
        self._paused = False
        self._pulse_time = 0.0
        self._colors = None
        self._pulse_sid = 0
        self._pos = 0

        CanvasIcon.__init__(self, **kwargs)

    def do_set_property(self, pspec, value):
        CanvasIcon.do_set_property(self, pspec, value)

        if pspec.name == 'pulse-time':
            self._pulse_time = value
            self._stop()
            if not self._paused and self._pulse_time > 0.0:
                self._start()
        elif pspec.name == 'colors':
            self._colors = value
            self._pos = 0
            self._update_colors()
        elif pspec.name == 'paused':
            self._paused = value
            if not self._paused and self._pulse_time > 0.0:
                self._start()
            else:
                self._stop()

    def do_get_property(self, pspec):
        CanvasIcon.do_get_property(self, pspec)

        if pspec.name == 'pulse-time':
            return self._pulse_time
        elif pspec.name == 'colors':
            return self._colors

    def _update_colors(self):
        self.props.stroke_color = self._colors[self._pos][0]
        self.props.fill_color = self._colors[self._pos][1]

    def _pulse_timeout(self):
        if self._colors:
            self._update_colors()

        self._pos += 1
        if self._pos == len(self._colors):
            self._pos = 0

        return True

    def _start(self):
        if self._pulse_sid == 0:
            self._pulse_sid = gobject.timeout_add(
                    int(self._pulse_time * 1000), self._pulse_timeout)

    def _stop(self):
        if self._pulse_sid:
            gobject.source_remove(self._pulse_sid)
            self._pulse_sid = 0
