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

"""Taking a moment: the quick in-activity card that replaced the bench
talk on this dial.

A snapshot of the work right now, a caption, three marks - all
optional. The activity behind is never paused; it stays exactly as it
was.
"""

import base64
import logging
import math
import time
from gettext import gettext as _

import cairo
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import PangoCairo

from sugar3 import profile
from sugar3.datastore import datastore
from sugar3.graphics import style

from jarabe.journal import model
from jarabe.journal import reflectguard
from jarabe.journal import reflection
from jarabe.journal.joglyph import JoGlyph
from jarabe.journal import reflectstyle
from jarabe.journal import timeline


_CARD_WIDTH = style.zoom(600)
_CARD_BORDER = style.zoom(20)
_CARD_RADIUS = style.zoom(24)
_JO_HEADER = style.zoom(45)
_MAT_PAD = style.zoom(12)
_BAND_HEIGHT = style.zoom(86)
_ROTATE_MARGIN = style.zoom(10)
_TILT = -1.2 * math.pi / 180.0
_DISC_SIZE = style.zoom(64)
_CONTROL_HEIGHT = style.zoom(52)

# Big enough to stand in for the artwork when the entry view stages a
# moment, small enough that a shelf of these never dents the entry.
_SNAP_WIDTH = 960
_SNAP_HEIGHT = 600
_SNAP_QUALITY = '85'

SNAP_KEY = reflectguard.SNAP_KEY

_MAX_MOMENTS = reflectguard.MAX_MOMENTS

_MARKS = (('proud', _('proud')), ('tricky', _('tricky')),
          ('wonder', _('wonder')))

_TITLE = _('Taking a moment')
_CAPTION_HINT = _('write about this bit')
_MARK_LEAD = _('leave a mark, if you want')
_DISCARD_LABEL = _("Don't keep it")
_KEEP_LABEL = _('Keep it in my Journal')

_css_registered = False


def _register_css():
    global _css_registered
    if _css_registered:
        return
    _css_registered = True

    xo_color = profile.get_color()
    stroke = xo_color.get_stroke_color()
    r, g, b = (int(stroke.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    tint = '#%02X%02X%02X' % (r + (255 - r) * 9 // 10,
                              g + (255 - g) * 9 // 10,
                              b + (255 - b) * 9 // 10)

    px = reflectstyle.px

    css = ('''
.mc-card {
    background-color: %(paper)s;
    border: %(z1)dpx solid %(rim)s; border-radius: %(radius)dpx;
}
.mc-title {
    font-family: %(font_clear)s;
    font-weight: 700; font-size: %(z24)dpx; color: %(ink)s;
}
.mc-lead {
    font-family: %(font_clear)s;
    font-weight: 600; font-size: %(z16)dpx; color: %(ink_soft)s;
}
.mc-mark-label {
    font-family: %(font_clear)s;
    font-weight: 700; font-size: %(z17)dpx; color: %(ink_soft)s;
}
.mc-mark-label.selected { color: %(stroke)s; }
.mc-disc {
    background-color: %(card)s;
    border: %(z2)dpx solid %(rim)s; border-radius: %(z999)dpx;
}
.mc-disc.selected {
    background-color: %(tint)s; border: %(z3)dpx solid %(stroke)s;
}
.mc-caption {
    font-family: %(font_hand)s;
    font-size: %(z32)dpx; color: %(ink)s;
    background-color: transparent;
    border: none; box-shadow: none;
    caret-color: %(ink)s;
}
.mc-chip {
    background-color: transparent; background-image: none;
    border: none; box-shadow: none; padding: 0;
}
.mc-chip:active .mc-disc {
    background-color: %(tint)s; border-color: %(stroke)s;
}
.mc-discard {
    font-family: %(font_clear)s;
    font-weight: 700; font-size: %(z18)dpx; color: %(ink_soft)s;
    background-color: %(card)s; background-image: none;
    border: %(z2)dpx solid %(rim)s; border-radius: %(z999)dpx;
    padding: %(z12)dpx %(z22)dpx;
}
.mc-discard:active { background-color: %(rim)s; }
.mc-keep {
    font-family: %(font_clear)s;
    font-weight: 700; font-size: %(z18)dpx; color: %(card)s;
    background-color: %(stroke)s; background-image: none;
    border: none; border-radius: %(z999)dpx;
    padding: %(z12)dpx %(z26)dpx;
}
.mc-keep:active { background-color: %(tint)s; color: %(ink)s; }
''' % {
        'paper': reflectstyle.PAPER_PAGE,
        'card': reflectstyle.CARD,
        'ink': reflectstyle.INK_PAGE,
        'ink_soft': reflectstyle.INK_SOFT_PAGE,
        'rim': reflectstyle.RIM_MOMENT,
        'stroke': stroke,
        'tint': tint,
        'radius': _CARD_RADIUS,
        'font_hand': reflectstyle.FONT_HAND,
        'font_clear': reflectstyle.FONT_CLEAR,
        'z1': px(1), 'z2': px(2), 'z3': px(3), 'z12': px(12),
        'z16': px(16), 'z17': px(17), 'z18': px(18), 'z22': px(22),
        'z24': px(24), 'z26': px(26), 'z32': px(32), 'z999': px(999),
    }).encode('utf-8')

    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _class(widget, name):
    widget.get_style_context().add_class(name)
    return widget


def _set_source(cr, color):
    rgba = Gdk.RGBA()
    rgba.parse(color)
    Gdk.cairo_set_source_rgba(cr, rgba)


def _capture_screen():
    """Grab the whole screen right now. None on any failure - the card
    falls back to a plain paper placeholder rather than crash.
    """
    try:
        screen = Gdk.Screen.get_default()
        width, height = screen.get_width(), screen.get_height()
        root = Gdk.get_default_root_window()
        return Gdk.pixbuf_get_from_window(root, 0, 0, width, height)
    except Exception:
        logging.exception('momentcard: screen capture failed')
        return None


def _trim_activity(raw):
    """The activity alone: the Frame's toolbar row and the window's
    own edges cut away.
    """
    if raw is None:
        return None
    try:
        inset = style.zoom(4)
        top = style.GRID_CELL_SIZE + inset
        w = max(1, raw.get_width() - inset * 2)
        h = max(1, raw.get_height() - top - inset * 3)
        return raw.new_subpixbuf(inset, top, w, h)
    except Exception:
        logging.exception('momentcard: capture trim failed')
        return None


def _blur(pixbuf):
    """A cheap, convincing blur: collapse the image and stretch it
    back, letting bilinear filtering soften it both ways.
    """
    if pixbuf is None:
        return None
    w, h = pixbuf.get_width(), pixbuf.get_height()
    small = pixbuf.scale_simple(max(1, w // 8), max(1, h // 8),
                                GdkPixbuf.InterpType.BILINEAR)
    if small is None:
        return pixbuf
    soft = small.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
    return soft if soft is not None else pixbuf


def _encode_snap(pixbuf):
    """Scale the capture down to a shelf-sized JPEG, base64-wrapped so
    it survives the datastore's UTF-8-only metadata (all but 'preview').
    """
    if pixbuf is None:
        return None
    try:
        w, h = pixbuf.get_width(), pixbuf.get_height()
        scale = min(_SNAP_WIDTH / float(w), _SNAP_HEIGHT / float(h))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        scaled = pixbuf.scale_simple(new_w, new_h,
                                     GdkPixbuf.InterpType.BILINEAR)
        if scaled is None:
            return None
        ok, buf = scaled.save_to_bufferv('jpeg', ['quality'],
                                         [_SNAP_QUALITY])
        if not ok:
            return None
        return base64.b64encode(bytes(buf)).decode('ascii')
    except Exception:
        logging.exception('momentcard: snap encode failed')
        return None


def _add_moment(data, caption, mark):
    """Append a moment to the reflections record and return
    (moment, evicted_seqs). evicted_seqs lists every snap key
    number to drop from metadata, oldest first.
    """
    moments = list(data.get('moments', []))
    seq = data.get('moment_seq', 0)
    moment = {'caption': caption, 'mark': mark, 'ts': time.time(),
              'snap_seq': seq}
    moments.append(moment)
    evicted = []
    while len(moments) > _MAX_MOMENTS:
        evicted.append(moments.pop(0).get('snap_seq'))
    data['moments'] = moments
    data['moment_seq'] = seq + 1
    return moment, evicted


# Traced from sugarlabs/maze-activity's icon; re-traced to stay in sync.
_MAZE_WALLS = (
    (8.01, 6.04), (8.01, 2.09), (15.91, 2.09), (15.91, 8.01),
    (11.96, 8.01), (11.96, 6.04), (13.94, 6.04), (13.94, 4.06),
    (9.99, 4.06), (9.99, 8.01), (6.04, 8.01), (6.04, 11.96), (4.06, 11.96),
    (4.06, 13.94), (8.01, 13.94), (8.01, 9.99), (15.91, 9.99),
    (15.91, 15.91), (13.94, 15.91), (13.94, 11.96), (9.99, 11.96),
    (9.99, 13.94), (11.96, 13.94), (11.96, 15.91), (2.09, 15.91),
    (2.09, 9.99), (4.06, 9.99), (4.06, 4.06), (2.09, 4.06), (2.09, 2.09),
    (6.04, 2.09), (6.04, 6.04))


def draw_mark(cr, kind, color):
    """Draw a proud / tricky / wonder mark into an 18x18 unit box.

    The caller owns the transform: translate and scale cr so that the
    box lands where the mark should sit. Shared with the entry view,
    so a mark reads identically wherever the child left it. Tricky and
    wonder borrow Sugar's own artwork (the Maze activity icon and
    sugar-artwork's emblem-question); proud is ours in the same
    icon grammar - upstream has no flag.
    """
    _set_source(cr, color)
    if kind == 'proud':
        # Not a star: the Journal already spends the star on keep.
        cr.set_line_width(1.6)
        cr.set_line_cap(cairo.LineCap.SQUARE)
        cr.set_line_join(cairo.LineJoin.MITER)
        cr.move_to(4.8, 15.2)
        cr.line_to(4.8, 3.0)
        cr.stroke()
        cr.move_to(4.8, 3.2)
        cr.line_to(13.6, 5.9)
        cr.line_to(4.8, 8.6)
        cr.close_path()
        cr.fill_preserve()
        cr.set_line_width(1.2)
        cr.stroke()
    elif kind == 'tricky':
        cr.set_line_width(0.9)
        cr.set_line_cap(cairo.LineCap.SQUARE)
        cr.set_line_join(cairo.LineJoin.MITER)
        cr.move_to(*_MAZE_WALLS[0])
        for point in _MAZE_WALLS[1:]:
            cr.line_to(*point)
        cr.close_path()
        cr.stroke()
    else:
        # sugar-artwork's own question mark, filled, dot and all.
        cr.move_to(7.24, 8.67)
        cr.curve_to(7.24, 7.94, 8.05, 7.82, 8.89, 7.59)
        cr.curve_to(9.7, 7.37, 10.52, 7.04, 10.52, 5.86)
        cr.curve_to(10.52, 4.97, 9.68, 4.31, 8.83, 4.31)
        cr.curve_to(7.12, 4.31, 6.85, 6.33, 5.55, 6.33)
        cr.curve_to(4.81, 6.33, 4.3, 5.76, 4.3, 4.86)
        cr.curve_to(4.3, 2.72, 6.99, 1.5, 8.83, 1.5)
        cr.curve_to(11.46, 1.5, 13.7, 3.13, 13.7, 5.86)
        cr.curve_to(13.7, 8.12, 12.27, 9.45, 10.17, 9.98)
        cr.line_to(10.17, 10.71)
        cr.curve_to(10.17, 11.53, 9.56, 12.12, 8.71, 12.12)
        cr.curve_to(7.79, 12.12, 7.24, 11.53, 7.24, 10.71)
        cr.close_path()
        cr.fill()
        cr.arc(8.71, 14.91, 1.59, 0, 2 * math.pi)
        cr.fill()


def draw_star(cr, cx, cy, radius, lit, color):
    """The keep-star, shared across the Journal's surfaces."""
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.44
        angle = -math.pi / 2 + i * math.pi / 5
        points.append((cx + r * math.cos(angle),
                       cy + r * math.sin(angle)))
    cr.set_line_join(cairo.LineJoin.ROUND)
    cr.move_to(*points[0])
    for point in points[1:]:
        cr.line_to(*point)
    cr.close_path()
    # One outline weight at every size, scaled like the board's svg.
    line = max(1.2, radius * 0.17)
    if lit:
        _set_source(cr, color)
        cr.fill_preserve()
        _set_source(cr, reflectstyle.PAPER_PAGE)
        cr.set_line_width(line)
        cr.stroke()
    else:
        _set_source(cr, reflectstyle.INK_FAINT)
        cr.set_line_width(line)
        cr.stroke()


class FoldGlyph(Gtk.DrawingArea):
    """Two stacked cards: the Journal's shared "more underneath" sign."""

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.set_size_request(style.zoom(24), style.zoom(22))
        stroke = profile.get_color().get_stroke_color()
        red, green, blue = (int(stroke.lstrip('#')[i:i + 2], 16)
                            for i in (0, 2, 4))
        self._stroke = stroke
        self._tint = '#%02X%02X%02X' % (
            int(red + (255 - red) * 0.88),
            int(green + (255 - green) * 0.88),
            int(blue + (255 - blue) * 0.88))
        self.connect('draw', self.__draw_cb)

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        cr.scale(alloc.width / 26.0, alloc.height / 24.0)
        cr.set_line_width(2)
        _set_source(cr, reflectstyle.PAPER_PAGE)
        timeline.rounded_rect_path(cr, 5, 2, 18, 14, 3)
        cr.fill_preserve()
        _set_source(cr, reflectstyle.INK_SOFT_PAGE)
        cr.stroke()
        _set_source(cr, self._tint)
        timeline.rounded_rect_path(cr, 2, 7, 18, 14, 3)
        cr.fill_preserve()
        _set_source(cr, self._stroke)
        cr.stroke()
        return False


class _MarkGlyph(Gtk.DrawingArea):
    """A mark as a widget, for the card's own mark chips."""

    def __init__(self, kind, size):
        Gtk.DrawingArea.__init__(self)
        self._kind = kind
        self._color = reflectstyle.INK_PAGE
        self.set_size_request(size, size)
        self.connect('draw', self.__draw_cb)

    def set_color(self, color):
        self._color = color
        self.queue_draw()

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        s = min(alloc.width, alloc.height)
        cr.translate((alloc.width - s) / 2.0, (alloc.height - s) / 2.0)
        cr.scale(s / 18.0, s / 18.0)
        draw_mark(cr, self._kind, self._color)
        return False


class _Polaroid(Gtk.DrawingArea):
    """A just-taken photo: white frame, thick bottom band, a slight
    tilt - drawn whole in cairo, since GTK 3.24 has no CSS transform.
    """

    def __init__(self, width):
        Gtk.DrawingArea.__init__(self)
        self._pixbuf = None
        self._hint_visible = True
        self._dots_phase = 0
        self._dots_id = None
        self._pw = width
        self._snap_w = width - 2 * _MAT_PAD
        self.__set_ratio(322.0 / 548.0)
        self.connect('draw', self.__draw_cb)

    def __set_ratio(self, ratio):
        self._snap_h = int(self._snap_w * ratio)
        self._ph = _MAT_PAD * 2 + self._snap_h + _BAND_HEIGHT
        self.set_size_request(self._pw + 2 * _ROTATE_MARGIN,
                              self._ph + 2 * _ROTATE_MARGIN)

    def set_hint_visible(self, visible):
        if self._hint_visible != visible:
            self._hint_visible = visible
            self.queue_draw()
        if visible and self._dots_id is None:
            self._dots_id = GLib.timeout_add(350, self.__dots_tick_cb)
        elif not visible and self._dots_id is not None:
            GLib.source_remove(self._dots_id)
            self._dots_id = None

    def __dots_tick_cb(self):
        # Only the band strip repaints on a tick; the photo and
        # its shadow stack stay untouched between hops.
        self._dots_phase = (self._dots_phase + 1) % 4
        bx, by, bw, bh = self.band_rect()
        pad = style.zoom(12)
        self.queue_draw_area(int(bx - pad), int(by - pad),
                             int(bw + 2 * pad), int(bh + 2 * pad))
        return True

    def band_rect(self):
        """The band's rectangle in the widget's own (unrotated)
        coordinates, for the caption entry laid over this widget.
        """
        x = _ROTATE_MARGIN + _MAT_PAD
        y = _ROTATE_MARGIN + _MAT_PAD + self._snap_h
        w = self._pw - 2 * _MAT_PAD
        h = _BAND_HEIGHT
        return x, y, w, h

    def set_pixbuf(self, pixbuf):
        self._pixbuf = pixbuf
        if pixbuf is not None and pixbuf.get_width() > 0:
            # The mat takes the photo's own shape, within reason - a
            # polaroid never letterboxes its picture.
            ratio = pixbuf.get_height() / float(pixbuf.get_width())
            self.__set_ratio(max(0.30, min(0.75, ratio)))
        self.queue_draw()

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        cx, cy = alloc.width / 2.0, alloc.height / 2.0
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(_TILT)
        cr.translate(-self._pw / 2.0, -self._ph / 2.0)
        self.__draw_card(cr)
        cr.restore()
        return False

    def __draw_card(self, cr):
        pw, ph = self._pw, self._ph
        cr.set_source_rgba(0.227, 0.192, 0.149, 0.045)
        for i in range(1, 6):
            cr.rectangle(-i * 0.5, style.zoom(2) + i * 1.4,
                         pw + i, ph)
            cr.fill()

        _set_source(cr, reflectstyle.CARD)
        cr.rectangle(0, 0, pw, ph)
        cr.fill()
        _set_source(cr, reflectstyle.RIM_MOMENT)
        cr.set_line_width(1.0)
        cr.rectangle(0.5, 0.5, pw - 1, ph - 1)
        cr.stroke()

        cr.save()
        cr.rectangle(_MAT_PAD, _MAT_PAD, self._snap_w, self._snap_h)
        cr.clip()
        _set_source(cr, reflectstyle.PAPER_PAGE)
        cr.paint()
        if self._pixbuf is not None:
            sw = self._pixbuf.get_width()
            sh = self._pixbuf.get_height()
            # The whole canvas, undistorted and centred: cropping or
            # stretching would misrepresent what the child just made.
            scale = min(self._snap_w / float(sw), self._snap_h / float(sh))
            cr.translate(_MAT_PAD + (self._snap_w - sw * scale) / 2.0,
                         _MAT_PAD + (self._snap_h - sh * scale) / 2.0)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
            cr.get_source().set_filter(cairo.Filter.GOOD)
            cr.paint()
        cr.restore()

        # The band is where a polaroid gets written on: a warm wash,
        # a pencil waiting at its left, the invitation painted here
        # (not an entry placeholder) so the ready caret never hides
        # it.
        band_x = _MAT_PAD
        band_y = _MAT_PAD + self._snap_h
        band_w = self._pw - 2 * _MAT_PAD
        _set_source(cr, '#FDF6E8')
        cr.rectangle(band_x, band_y, band_w, _BAND_HEIGHT)
        cr.fill()

        pencil = style.zoom(24)
        cr.save()
        cr.translate(band_x + style.zoom(8),
                     band_y + (_BAND_HEIGHT - pencil) / 2.0)
        cr.scale(pencil / 18.0, pencil / 18.0)
        _set_source(cr, '#B97A1E')
        cr.set_line_width(1.8)
        cr.set_line_join(cairo.LineJoin.ROUND)
        cr.move_to(3.2, 14.8)
        cr.line_to(4.0, 11.8)
        cr.line_to(12.6, 3.2)
        cr.line_to(14.8, 5.4)
        cr.line_to(6.2, 14.0)
        cr.close_path()
        cr.stroke()
        cr.move_to(11.4, 4.4)
        cr.line_to(13.6, 6.6)
        cr.stroke()
        cr.restore()

        if self._hint_visible:
            layout = PangoCairo.create_layout(cr)
            layout.set_font_description(Pango.FontDescription(
                '%s 22' % reflectstyle.FONT_HAND_FAMILY))
            layout.set_text(_CAPTION_HINT, -1)
            _tw, th = layout.get_pixel_size()
            _set_source(cr, reflectstyle.INK_SOFT_PAGE)
            cr.move_to(band_x + style.zoom(52),
                       band_y + (_BAND_HEIGHT - th) / 2.0)
            PangoCairo.show_layout(cr, layout)

            dot_r = style.zoom(5)
            base_x = band_x + style.zoom(52) + _tw + style.zoom(18)
            base_y = band_y + _BAND_HEIGHT / 2.0 + style.zoom(3)
            _set_source(cr, '#B97A1E')
            for k in range(3):
                hop = style.zoom(6) if self._dots_phase == k else 0
                cr.arc(base_x + k * style.zoom(17), base_y - hop,
                       dot_r, 0, 2 * math.pi)
                cr.fill()


class MomentCard(Gtk.Window):
    """The moment card: a snapshot, a caption, three marks, two honest
    choices. One fullscreen toplevel, the same shape as the shell's
    LaunchWindow: the backdrop paints the activity blurred and
    quieted (Sugar runs no compositor), and the card itself is an
    ordinary child box - no second window to stack, shape or race.
    """

    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_app_paintable(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('realize', lambda w: self.set_type_hint(
            Gdk.WindowTypeHint.DIALOG))
        self.connect('key-press-event', self.__key_press_cb)
        self.connect('button-press-event', self.__backdrop_press_cb)
        self.connect('draw', self.__draw_backdrop_cb)

        _register_css()

        self._object_id = None
        self._metadata = None
        self._pixbuf = None
        self._backdrop = None
        self._card_rest = None
        self._mark = None
        self._mark_glyphs = {}
        self._mark_discs = {}
        self._mark_labels = {}
        self._settle_id = None
        self._departing = False
        self.connect('focus-out-event', self.__focus_out_cb)

        # The polaroid already carries _ROTATE_MARGIN of clearance on
        # every side, so the column's own spacing stays small or the
        # gaps around it read double.
        outer = Gtk.VBox()
        outer.set_border_width(_CARD_BORDER)
        outer.set_spacing(style.zoom(8))

        outer.pack_start(self.__build_header(), False, False, 0)
        outer.pack_start(self.__build_polaroid(), False, False, 0)
        outer.pack_start(self.__build_marks(), False, False, 0)
        footer = self.__build_footer()
        footer.set_margin_top(style.zoom(4))
        outer.pack_start(footer, False, False, 0)

        self._card_box = _class(Gtk.VBox(), 'mc-card')
        self._card_box.pack_start(outer, False, False, 0)
        self._card_box.set_size_request(_CARD_WIDTH, -1)
        self._fixed = Gtk.Fixed()
        self._fixed.put(self._card_box, 0, 0)
        self.add(self._fixed)

    def __build_header(self):
        bar = Gtk.HBox()
        bar.set_spacing(style.zoom(12))
        jo = JoGlyph(_JO_HEADER, breathing=True)
        jo.set_valign(Gtk.Align.CENTER)
        bar.pack_start(jo, False, False, 0)
        title = _class(Gtk.Label(label=_TITLE), 'mc-title')
        title.set_xalign(0.0)
        title.set_valign(Gtk.Align.CENTER)
        bar.pack_start(title, False, False, 0)
        return bar

    def __build_polaroid(self):
        # _Polaroid pads its own request by _ROTATE_MARGIN on every
        # side for tilt clearance, so its logical width must come in
        # narrower than the column or the card would overshoot
        # _CARD_WIDTH by twice that margin.
        width = _CARD_WIDTH - 2 * _CARD_BORDER - 2 * _ROTATE_MARGIN
        self._polaroid = _Polaroid(width)
        overlay = Gtk.Overlay()
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.add(self._polaroid)

        entry = _class(Gtk.Entry(), 'mc-caption')
        entry.set_max_length(120)
        entry.connect('changed', self.__caption_changed_cb)
        entry.set_has_frame(False)
        entry.set_halign(Gtk.Align.START)
        entry.set_valign(Gtk.Align.START)
        entry.connect('activate', self.__keep_cb)
        self._caption_entry = entry
        self.__place_caption()
        overlay.add_overlay(entry)
        return overlay

    def __caption_changed_cb(self, entry):
        # The painted invitation steps aside the moment real words
        # arrive, and comes back if they are all deleted.
        self._polaroid.set_hint_visible(not entry.get_text())

    def __place_caption(self):
        # The mat resizes to each capture, so the caption chases the
        # band wherever it lands; the pencil prop keeps the left edge.
        band_x, band_y, band_w, band_h = self._polaroid.band_rect()
        self._caption_entry.set_margin_start(band_x + style.zoom(44))
        self._caption_entry.set_margin_top(
            band_y + (band_h - _CONTROL_HEIGHT) // 2)
        self._caption_entry.set_size_request(
            band_w - style.zoom(16), _CONTROL_HEIGHT)

    def __build_marks(self):
        col = Gtk.VBox()
        col.set_spacing(style.zoom(12))
        lead = _class(Gtk.Label(label=_MARK_LEAD), 'mc-lead')
        col.pack_start(lead, False, False, 0)

        row = Gtk.HBox()
        row.set_spacing(style.zoom(18))
        row.set_halign(Gtk.Align.CENTER)
        for mark_id, label in _MARKS:
            chip = _class(Gtk.Button(), 'mc-chip')
            chip.set_relief(Gtk.ReliefStyle.NONE)
            chip.mark_id = mark_id
            chip_col = Gtk.VBox()
            chip_col.set_spacing(style.zoom(4))
            disc = _class(Gtk.EventBox(), 'mc-disc')
            disc.set_size_request(_DISC_SIZE, _DISC_SIZE)
            glyph = _MarkGlyph(mark_id, style.zoom(48))
            glyph.set_halign(Gtk.Align.CENTER)
            glyph.set_valign(Gtk.Align.CENTER)
            disc.add(glyph)
            chip_col.pack_start(disc, False, False, 0)
            mark_label = _class(Gtk.Label(label=label), 'mc-mark-label')
            chip_col.pack_start(mark_label, False, False, 0)
            chip.add(chip_col)
            chip.connect('clicked', self.__mark_clicked_cb)
            self._mark_glyphs[mark_id] = glyph
            self._mark_discs[mark_id] = disc
            self._mark_labels[mark_id] = mark_label
            row.pack_start(chip, False, False, 0)
        col.pack_start(row, False, False, 0)
        return col

    def __build_footer(self):
        row = Gtk.HBox()
        row.set_spacing(style.zoom(16))
        discard = _class(Gtk.Button(label=_DISCARD_LABEL), 'mc-discard')
        discard.set_relief(Gtk.ReliefStyle.NONE)
        discard.set_size_request(-1, _CONTROL_HEIGHT)
        discard.connect('clicked', self.__discard_cb)
        row.pack_start(discard, False, False, 0)

        keep = _class(Gtk.Button(label=_KEEP_LABEL), 'mc-keep')
        keep.set_relief(Gtk.ReliefStyle.NONE)
        keep.set_size_request(-1, _CONTROL_HEIGHT)
        keep.connect('clicked', self.__keep_cb)
        row.pack_end(keep, False, False, 0)
        return row

    def __deselect_marks(self):
        for mark_id in self._mark_discs:
            self._mark_discs[mark_id].get_style_context().remove_class(
                'selected')
            self._mark_labels[mark_id].get_style_context().remove_class(
                'selected')
            self._mark_glyphs[mark_id].set_color(reflectstyle.INK_PAGE)

    def __mark_clicked_cb(self, button):
        was_selected = self._mark == button.mark_id
        self.__deselect_marks()
        self._mark = None
        if not was_selected:
            self._mark = button.mark_id
            stroke = profile.get_color().get_stroke_color()
            self._mark_discs[self._mark].get_style_context().add_class(
                'selected')
            self._mark_labels[self._mark].get_style_context().add_class(
                'selected')
            self._mark_glyphs[self._mark].set_color(stroke)

    def __close(self):
        if self._settle_id is not None:
            GLib.source_remove(self._settle_id)
            self._settle_id = None
        self.hide()
        self._polaroid.set_hint_visible(False)
        # The card lives for the whole session; parked, it must not
        # keep two full-screen captures (~12MB) pinned in the shell.
        self._pixbuf = None
        self._backdrop = None
        self._polaroid.set_pixbuf(None)
        self._metadata = None

    def __backdrop_press_cb(self, widget, event):
        alloc = self._card_box.get_allocation()
        if (alloc.x <= event.x <= alloc.x + alloc.width and
                alloc.y <= event.y <= alloc.y + alloc.height):
            return False
        self.__close()
        return True

    def __focus_out_cb(self, widget, event):
        # Anything that takes the screen away - a click outside, F3 to
        # Home, another activity raising - ends the moment. Presenting
        # is sequenced on the Frame's retract completing, so no late
        # refocus is left to bounce against.
        if self.get_visible():
            self.__close()
        return False

    def __discard_cb(self, button):
        self.__close()

    def __keep_cb(self, button):
        if self._departing:
            return
        self._departing = True
        caption = self._caption_entry.get_text().strip()
        try:
            self.__store_moment(caption, self._mark)
        except Exception:
            # A failed keep must not strand the card with a dead
            # button - let the child try again or discard.
            logging.exception('momentcard: keep failed')
            self._departing = False
            return
        self.__depart()

    def __depart(self):
        # Keeping files the card away: it sinks off its shadow while
        # the scrim holds, then everything lets go. Discarding just
        # closes - only keeping earns the beat.
        if self._settle_id is not None:
            GLib.source_remove(self._settle_id)
            self._settle_id = None
        fx, fy = self._card_rest[:2] if self._card_rest else (0, 0)
        drop = style.zoom(40)
        start = time.monotonic()

        def tick():
            t = min(1.0, (time.monotonic() - start) / 0.16)
            self._fixed.move(self._card_box, fx, int(fy + drop * t * t))
            if t >= 1.0:
                self._settle_id = None
                self.__close()
                return False
            return True

        self._settle_id = GLib.timeout_add(16, tick)

    def __key_press_cb(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.__close()
            return True
        return False

    def __resolve_entry(self, activity_id):
        if not activity_id:
            return None, None
        try:
            # the find() wrapper consumes 'uid' to build object_id, so
            # it must be requested even though it never reaches metadata
            results, count = datastore.find(
                {'activity_id': activity_id, 'limit': 1},
                sorting=['-mtime'], properties=['uid'])
        except Exception:
            logging.exception('momentcard: datastore lookup failed')
            return None, None
        if not results:
            return None, None
        object_id = results[0].object_id
        results[0].destroy()
        try:
            return object_id, model.get(object_id)
        except Exception:
            logging.exception('momentcard: could not read entry %r',
                              object_id)
            return None, None

    def __store_moment(self, caption, mark):
        if not self._object_id or self._metadata is None:
            return
        # Merge onto the entry as it is NOW, not as it was when the
        # card opened - the activity may have saved fresh work while
        # the child typed, and update() prunes and reverts whatever
        # the writer sends stale.
        try:
            metadata = model.get(self._object_id)
        except Exception:
            logging.exception('momentcard: could not re-read entry %r',
                              self._object_id)
            metadata = self._metadata
        data = reflection.loads(metadata.get('reflections', ''))
        moment, evicted = _add_moment(data, caption, mark)
        metadata['reflections'] = reflection.dumps(data)
        for seq in evicted:
            if seq is not None:
                metadata.pop(SNAP_KEY % seq, None)
        snap = _encode_snap(self._pixbuf)
        if snap is not None:
            metadata[SNAP_KEY % moment['snap_seq']] = snap
        # Held in shell memory too: the running activity will later
        # save with the metadata it loaded at resume, wiping this
        # write; the reflections guard puts the state back when it
        # does.
        snaps = {}
        for m in data['moments']:
            key = SNAP_KEY % m.get('snap_seq', -1)
            if key in metadata:
                snaps[key] = metadata[key]
        reflectguard.get_guard().note_moments(self._object_id,
                                              data['moments'], snaps)
        try:
            model.write(metadata, update_mtime=False)
        except Exception:
            logging.exception('momentcard: could not write entry %r',
                              self._object_id)

    def __draw_backdrop_cb(self, widget, cr):
        if self._backdrop is not None:
            Gdk.cairo_set_source_pixbuf(cr, self._backdrop, 0, 0)
            cr.paint()
        cr.set_source_rgba(0.227, 0.192, 0.149, 0.40)
        cr.paint()
        # No compositor means no real shadow; paint one where the
        # card rests, heavier below.
        if self._card_rest is not None:
            x, y, w, h = self._card_rest
            rings = 16
            for i in range(rings, 0, -1):
                grow = i * 2
                alpha = 0.10 * (1.0 - i / float(rings + 1)) ** 2
                cr.set_source_rgba(0, 0, 0, alpha)
                cr.set_line_width(2.6)
                gx = x - grow
                gy = y - grow + i * 0.7
                gw = w + grow * 2
                gh = h + grow * 2
                gr = _CARD_RADIUS + grow
                timeline.rounded_rect_path(cr, gx, gy, gw, gh, gr)
                cr.stroke()
        return False

    def present_over_activity(self, event_time=0, activity_id=None):
        if self.get_visible():
            # A second tap through the re-raised Frame must not
            # photograph the card itself; just come forward.
            self.present_with_time(self.__server_time(event_time))
            return
        self._object_id, self._metadata = self.__resolve_entry(activity_id)

        self._mark = None
        self.__deselect_marks()
        self._caption_entry.set_text('')

        self._departing = False
        raw = _capture_screen()
        self._pixbuf = _trim_activity(raw)
        self._backdrop = _blur(raw)
        self._polaroid.set_pixbuf(self._pixbuf)
        self.__place_caption()

        screen = Gdk.Screen.get_default()
        sw, sh = screen.get_width(), screen.get_height()
        self.set_size_request(sw, sh)
        self.resize(sw, sh)
        self.move(0, 0)
        self.show_all()
        _minimum, natural = self._card_box.get_preferred_size()
        rest_x = (sw - natural.width) // 2
        rest_y = (sh - natural.height) // 2
        self._card_rest = (rest_x, rest_y, natural.width, natural.height)
        self.__settle(rest_x, rest_y)
        # A fresh server timestamp: the tap's own is stale once the
        # Frame has finished retracting, and a stale present loses to
        # focus-stealing prevention.
        self.present_with_time(self.__server_time(event_time))
        self.set_keep_above(True)
        self._polaroid.set_hint_visible(True)
        self._caption_entry.grab_focus()

    def __server_time(self, fallback):
        # Only X11 keeps a server clock; anywhere else the caller's own
        # stamp is already the right one. Silent on purpose - on a
        # Wayland session that is the normal answer, not a failure, and
        # a traceback would only mislead whoever reads the log.
        try:
            from gi.repository import GdkX11
            return GdkX11.x11_get_server_time(self.get_window())
        except Exception:
            return fallback

    def __settle(self, fx, fy):
        if self._settle_id is not None:
            GLib.source_remove(self._settle_id)
            self._settle_id = None
        rise = style.zoom(24)
        start = time.monotonic()

        def tick():
            t = min(1.0, (time.monotonic() - start) / 0.2)
            ease = 1.0 - (1.0 - t) ** 3
            self._fixed.move(self._card_box, fx,
                             int(fy + rise * (1.0 - ease)))
            if t >= 1.0:
                self._settle_id = None
                return False
            return True

        self._fixed.move(self._card_box, fx, fy + rise)
        self._settle_id = GLib.timeout_add(16, tick)
