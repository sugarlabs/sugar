# Copyright (C) 2026, Sugar Labs (Shubham Sharma)
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

"""Jo's one face, shared by every surface.

Jo is the little robot: an unpainted body on a quiet cool disc,
wearing its one warm light as the visor. This module keeps the
panel, the entry view, the tray and the invite drawing the same one.
"""

import math

import cairo
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from jarabe.journal import reflectstyle

# All geometry lives in the 75-unit box data/icons/reflectjo.svg uses.
_VISOR_X = 37.5
_VISOR_Y = 40.0
_VISOR_W = 29.0
_VISOR_H = 13.0
_VISOR_ARC = 6.5
_EYE_DX = 6.5
_EYE_R = 3.2
_GLOW_R = 26.0

_BREATH_PERIOD_US = 2000000.0

MOOD_RESTING = 'resting'
MOOD_THINKING = 'thinking'
MOOD_QUIET = 'quiet'

_MOODS = {
    # (ember scale, core alpha, glow alpha, room alpha, body alpha,
    #  breathes, ghost rings)
    MOOD_RESTING: (1.0, 0.95, 0.30, 1.0, 1.0, True, 0),
    MOOD_THINKING: (1.12, 1.0, 0.42, 1.0, 1.0, False, 2),
    MOOD_QUIET: (0.90, 0.95, 0.16, 0.35, 0.50, False, 0),
}

# The thinking rings' alphas, innermost first.
_RING_ALPHAS = (0.28, 0.12)


def animations_enabled():
    settings = Gtk.Settings.get_default()
    if settings is None:
        return False
    return bool(settings.get_property('gtk-enable-animations'))


def _set_source(cr, color, alpha=1.0):
    rgba = Gdk.RGBA()
    rgba.parse(color)
    rgba.alpha = alpha
    Gdk.cairo_set_source_rgba(cr, rgba)


class JoGlyph(Gtk.DrawingArea):
    """Jo, drawn live. breathing=True is for the one Jo present in
    the room (a header); avatars riding old turns stay still.
    """

    def __init__(self, pixel_size, breathing=False):
        Gtk.DrawingArea.__init__(self)
        self.set_size_request(pixel_size, pixel_size)
        self._breathing = breathing
        self._mood = MOOD_RESTING
        self._tick_id = None
        self._breath = 0.0
        self.connect('draw', self.__draw_cb)
        self.connect('map', self.__map_cb)
        self.connect('unmap', self.__unmap_cb)

    def set_mood(self, mood):
        if mood not in _MOODS or mood == self._mood:
            return
        self._mood = mood
        self.__sync_tick()
        self.queue_draw()

    def __wants_tick(self):
        if not self._breathing or not _MOODS[self._mood][5]:
            return False
        return self.get_mapped() and animations_enabled()

    def __sync_tick(self):
        if self.__wants_tick():
            if self._tick_id is None:
                self._tick_id = self.add_tick_callback(self.__tick_cb)
        elif self._tick_id is not None:
            self.remove_tick_callback(self._tick_id)
            self._tick_id = None
            self._breath = 0.0

    def __map_cb(self, widget):
        self.__sync_tick()

    def __unmap_cb(self, widget):
        self.__sync_tick()

    def __tick_cb(self, widget, frame_clock):
        t = frame_clock.get_frame_time() % _BREATH_PERIOD_US
        self._breath = math.sin(2 * math.pi * t / _BREATH_PERIOD_US)
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def __draw_cb(self, widget, cr):
        allocation = widget.get_allocation()
        size = min(allocation.width, allocation.height)
        cr.translate((allocation.width - size) / 2.0,
                     (allocation.height - size) / 2.0)
        cr.scale(size / 75.0, size / 75.0)

        scale, core_alpha, glow_alpha, room_alpha, body_alpha, \
            _breathes, rings = _MOODS[self._mood]

        _set_source(cr, reflectstyle.JO_DISC_FILL, room_alpha)
        cr.arc(37.5, 37.5, 35, 0, 2 * math.pi)
        cr.fill_preserve()
        _set_source(cr, reflectstyle.JO_DISC_LINE, room_alpha)
        cr.set_line_width(1.5)
        cr.stroke()

        # The body's optical mass sits below its geometric center;
        # lift the whole robot so it reads centered in the disc.
        cr.translate(0, -2.0)

        self.__body_path(cr)
        _set_source(cr, reflectstyle.CARD, body_alpha)
        cr.fill_preserve()
        _set_source(cr, reflectstyle.INK_PANEL, body_alpha)
        cr.set_line_width(3.5)
        cr.stroke()

        cr.save()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(2.5)
        cr.move_to(37.5, 13.4)
        cr.line_to(37.5, 18.0)
        cr.stroke()
        cr.move_to(29.5, 55.0)
        cr.curve_to(34.8, 58.3, 40.2, 58.3, 45.5, 55.0)
        cr.stroke()
        cr.restore()

        scale += 0.06 * self._breath
        core_alpha = min(1.0, core_alpha + 0.05 * self._breath)

        ember = Gdk.RGBA()
        ember.parse(reflectstyle.EMBER)
        glow = cairo.RadialGradient(
            _VISOR_X, _VISOR_Y, _GLOW_R * 0.25 * scale,
            _VISOR_X, _VISOR_Y, _GLOW_R * scale)
        glow.add_color_stop_rgba(0.0, ember.red, ember.green, ember.blue,
                                 glow_alpha)
        glow.add_color_stop_rgba(1.0, ember.red, ember.green, ember.blue,
                                 0.0)
        cr.set_source(glow)
        cr.arc(_VISOR_X, _VISOR_Y, _GLOW_R * scale, 0, 2 * math.pi)
        cr.fill()

        cr.set_line_width(1.8)
        for step in range(rings):
            cr.set_source_rgba(ember.red, ember.green, ember.blue,
                               _RING_ALPHAS[step])
            cr.arc(_VISOR_X, _VISOR_Y, 27.5 + step * 5.0,
                   0, 2 * math.pi)
            cr.stroke()

        cr.save()
        cr.translate(_VISOR_X, _VISOR_Y)
        cr.scale(scale, scale)
        cr.translate(-_VISOR_X, -_VISOR_Y)
        self.__visor_path(cr)
        cr.set_source_rgba(ember.red, ember.green, ember.blue, core_alpha)
        cr.fill()
        _set_source(cr, reflectstyle.CARD, core_alpha)
        for side in (-1, 1):
            cr.arc(_VISOR_X + side * _EYE_DX, _VISOR_Y, _EYE_R,
                   0, 2 * math.pi)
            cr.fill()
        cr.restore()
        return False

    def __body_path(self, cr):
        cr.arc(37.5, 9.2, 4.2, 0, 2 * math.pi)
        cr.new_sub_path()
        cr.move_to(17.5, 38.0)
        cr.arc(37.5, 38.0, 20.0, math.pi, 2 * math.pi)
        cr.line_to(57.5, 60.0)
        cr.arc(52.7, 60.0, 4.8, 0, 0.5 * math.pi)
        cr.line_to(22.3, 64.8)
        cr.arc(22.3, 60.0, 4.8, 0.5 * math.pi, math.pi)
        cr.close_path()

    def __visor_path(self, cr):
        left = _VISOR_X - _VISOR_W / 2.0
        top = _VISOR_Y - _VISOR_H / 2.0
        arc = _VISOR_ARC
        cr.new_sub_path()
        cr.arc(left + arc, top + arc, arc, math.pi, 1.5 * math.pi)
        cr.arc(left + _VISOR_W - arc, top + arc, arc,
               1.5 * math.pi, 2 * math.pi)
        cr.arc(left + _VISOR_W - arc, top + _VISOR_H - arc, arc,
               0, 0.5 * math.pi)
        cr.arc(left + arc, top + _VISOR_H - arc, arc,
               0.5 * math.pi, math.pi)
        cr.close_path()
