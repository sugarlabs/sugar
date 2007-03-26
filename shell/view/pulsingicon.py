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
        'colors'  : (object, None, None,
                     gobject.PARAM_READWRITE),
        'pulsing' : (bool, None, None, False,
                     gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs):
        self._pulsing = False
        self._colors = None
        self._pulse_sid = 0
        self._pos = 0

        CanvasIcon.__init__(self, **kwargs)

    def do_set_property(self, pspec, value):
        CanvasIcon.do_set_property(self, pspec, value)

        if pspec.name == 'pulsing':
            self._pulsing = value
            if self._pulsing:
                self._start()
            else:
                self._stop()
        elif pspec.name == 'colors':
            self._colors = value
            self._pos = 0

    def do_get_property(self, pspec):
        CanvasIcon.do_get_property(self, pspec)

        if pspec.name == 'pulsing':
            return self._pulsing
        elif pspec.name == 'colors':
            return self._colors

    def _pulse_timeout(self):
        if not self._colors:
            return

        self.props.stroke_color = self._colors[self._pos][0]
        self.props.fill_color = self._colors[self._pos][1]

        self._pos += 1
        if self._pos == len(self._colors):
            self._pos = 0

        return True

    def _start(self):
        if self._pulse_sid == 0:
            self._pulse_sid = gobject.timeout_add(1000, self._pulse_timeout)

    def _stop(self):
        if self._pulse_sid:
            gobject.source_remove(self._pulse_sid)
            self._pulse_sid = 0
