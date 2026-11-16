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

import math
import time
from gettext import gettext as _

import cairo

from sugar3 import profile
from sugar3.graphics import style


def safe_timestamp(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    try:
        time.localtime(number)
    except (ValueError, OverflowError, OSError):
        return default
    return number


def band_kind(timestamp):
    if not timestamp:
        return 'earlier'
    hour = time.localtime(timestamp).tm_hour
    if hour >= 21:
        return 'night'
    if hour >= 17:
        return 'evening'
    if hour >= 12:
        return 'afternoon'
    if hour >= 5:
        return 'morning'
    return 'early_hours'


def band_label(kind):
    return {
        'night': _('night'),
        'evening': _('evening'),
        'afternoon': _('afternoon'),
        'morning': _('morning'),
        'early_hours': _('early hours'),
    }.get(kind, '')


def day_label(day_ymd, now):
    year, month, day = day_ymd
    epoch = time.mktime((year, month, day, 12, 0, 0, 0, 0, -1))
    when = time.localtime(epoch)

    today = time.localtime(now)
    if day_ymd == today[:3]:
        return _('Today')

    today_epoch = time.mktime(today[:3] + (12, 0, 0, 0, 0, -1))
    days_ago = int(round((today_epoch - epoch) / 86400))
    if days_ago == 1:
        return _('Yesterday')
    if 0 <= days_ago <= 6:
        return time.strftime('%A', when)

    year = '' if when.tm_year == today.tm_year else ' %d' % when.tm_year
    return '%s, %d %s%s' % (time.strftime('%A', when), when.tm_mday,
                            time.strftime('%B', when), year)


def is_date_sort(order_by):
    if not order_by:
        return True
    return order_by[0][1:] in ('timestamp', 'creation_time')


def sort_field(order_by):
    if order_by and order_by[0][1:] == 'creation_time':
        return 'creation_time'
    return 'timestamp'


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgb01(hex_color):
    return tuple(component / 255. for component in hex_to_rgb(hex_color))


# These colours have no @define-color yet in sugar-artwork's gtk.css.
PAGE_BG = '#faf8f2'
DAY_INK = '#16150f'

SPINE_COLOR = '#DDD4BD'

SCROLLBAR_WIDTH = style.zoom(14)
SCROLLBAR_REST = '#d8d2c4'
SCROLLBAR_HOVER = '#b9b2a0'

FOLD_TINT = '#f1ebda'
CONTROL_HOVER_TINT = '#e7dfcd'
CONTROL_PRESS_TINT = '#d6c9a8'

META_INK = '#6b6558'

# Not style.COLOR_INACTIVE_STROKE -- that's a disabled button's outline
# colour, not running text.
BAND_INK = '#7b7565'


_owner_stroke_color = None


def owner_stroke_color():
    # HACK: cache on first use, not at import, so accents don't each draw a
    # different random pair when org.sugarlabs.user is unset.
    global _owner_stroke_color
    if _owner_stroke_color is None:
        _owner_stroke_color = profile.get_color().get_stroke_color()
    return _owner_stroke_color


BAND_SKY = {
    'early_hours': '#2E3B72',
    'morning': '#FFD98A',
    'afternoon': '#8FBEE8',
    'evening': '#E8896B',
    'night': '#0F1420',
}
BAND_BODY = {
    'early_hours': '#CFD6E8',
    'morning': '#FF8F00',
    'afternoon': '#FFC13B',
    'evening': '#9E3418',
    'night': '#F2E9C8',
}

DAY_TITLE_SIZE = style.zoom(34)
BAND_NAME_SIZE = style.zoom(19)

SWATCH_UNITS = 30.
SWATCH_INSET = 3
SWATCH_SIZE = 24
SWATCH_RADIUS = 7

GLYPH_SIZE = style.zoom(30)

SWATCH_HALF = (SWATCH_SIZE / 2.) * (GLYPH_SIZE / SWATCH_UNITS)

GLYPH_CLEARANCE = style.zoom(8)


def rounded_rect_path(cr, x, y, width, height, radius):
    radius = min(radius, width / 2., height / 2.)
    cr.new_sub_path()
    cr.arc(x + width - radius, y + radius, radius, -0.5 * math.pi, 0)
    cr.arc(x + width - radius, y + height - radius, radius, 0, 0.5 * math.pi)
    cr.arc(x + radius, y + height - radius, radius, 0.5 * math.pi, math.pi)
    cr.arc(x + radius, y + radius, radius, math.pi, 1.5 * math.pi)
    cr.close_path()


def _draw_crescent(cr, ox, oy, color):
    # HACK: even-odd fill turns solid here since the cut circle is
    # bigger than the outer one; use two arcs instead.
    radius = 12.4
    cut_radius, offset, tilt = 15.0, 9.7, math.radians(-38)
    px = (offset * offset - cut_radius * cut_radius +
          radius * radius) / (2 * offset)
    py = math.sqrt(max(radius * radius - px * px, 0.))
    theta = math.atan2(py, px)
    phi = math.atan2(py, px - offset)

    cr.save()
    cr.translate(ox, oy)
    cr.rotate(tilt)
    cr.translate(-ox, -oy)
    cr.new_path()
    cr.arc(ox, oy, radius, theta, 2 * math.pi - theta)
    cr.arc_negative(ox + offset, oy, cut_radius, -phi, phi - 2 * math.pi)
    cr.close_path()
    cr.set_source_rgb(*hex_to_rgb01(color))
    cr.fill()
    cr.restore()


def draw_swatch(cr, kind, size):
    if kind not in BAND_SKY:
        return
    cr.save()
    cr.scale(size / SWATCH_UNITS, size / SWATCH_UNITS)
    cr.set_antialias(cairo.ANTIALIAS_BEST)
    rounded_rect_path(cr, SWATCH_INSET, SWATCH_INSET,
                      SWATCH_SIZE, SWATCH_SIZE, SWATCH_RADIUS)
    cr.clip_preserve()
    cr.set_source_rgb(*hex_to_rgb01(BAND_SKY[kind]))
    cr.fill()

    body = BAND_BODY[kind]
    if kind in ('early_hours', 'night'):
        cr.save()
        cr.translate(17.0, 12.5)
        cr.scale(0.48, 0.48)
        cr.translate(-15.0, -17.0)
        _draw_crescent(cr, 15.0, 17.0, body)
        cr.restore()
    elif kind == 'afternoon':
        cr.set_source_rgb(*hex_to_rgb01(body))
        cr.arc(15, 15, 6, 0, 2 * math.pi)
        cr.fill()
    else:
        cr.new_sub_path()
        cr.arc(15, 27, 6, math.pi, 2 * math.pi)
        cr.close_path()
        cr.set_source_rgb(*hex_to_rgb01(body))
        cr.fill()
    cr.restore()


# Not folded into style.zoom(30): zoom() floors, so the two diverge.
PAGE_INSET = style.DEFAULT_SPACING * 2

SPINE_SLOT_WIDTH = style.zoom(78)
SPINE_WIDTH = style.zoom(3)

# listview.py adds _CARD_LEFT_GAP and gridview.py adds _SHADOW_MARGIN
# beyond this.
COLUMN_WIDTH = PAGE_INSET + SPINE_SLOT_WIDTH


def glyph_left_in_slot(glyph_size=GLYPH_SIZE):
    # Floored: the grid bead is a real widget and GTK only allocates it
    # at an integer offset.
    return (SPINE_SLOT_WIDTH - glyph_size) // 2


def spine_centre_in_slot(glyph_size=GLYPH_SIZE):
    # zoom() floors, so the two drift apart if derived separately.
    return glyph_left_in_slot(glyph_size) + glyph_size / 2.


def bead_gap(centre, glyph_size=GLYPH_SIZE):
    half = (SWATCH_SIZE / 2.) * (glyph_size / SWATCH_UNITS)
    return (centre - half - GLYPH_CLEARANCE,
            centre + half + GLYPH_CLEARANCE)


def draw_spine(cr, x, start, end, bead_centres, glyph_size=GLYPH_SIZE):
    cr.set_source_rgb(*hex_to_rgb01(SPINE_COLOR))
    cr.set_line_width(SPINE_WIDTH)
    y = start
    for centre in bead_centres:
        if centre is None:
            continue
        gap_top, gap_bottom = bead_gap(centre, glyph_size)
        if gap_top > y:
            cr.move_to(x, y)
            cr.line_to(x, gap_top)
            cr.stroke()
        y = max(y, gap_bottom)
    if end > y:
        cr.move_to(x, y)
        cr.line_to(x, end)
        cr.stroke()


FOLD_MIN_CARDS = 2
