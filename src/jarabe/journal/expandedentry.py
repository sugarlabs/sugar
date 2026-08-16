# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2008-2013, Sugar Labs
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

import base64
import logging
from gettext import gettext as _
import math
import time
import os

import cairo
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import PangoCairo
import json

from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.icon import CanvasIcon, Icon
from sugar3.graphics.alert import ConfirmationAlert
from sugar3.util import format_size
from sugar3.graphics.objectchooser import get_preview_pixbuf

from jarabe.journal.keepicon import KeepIcon
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import misc
from jarabe.journal import model
from jarabe.journal import journalwindow
from jarabe.journal import reflection
from jarabe.journal.momentcard import SNAP_KEY, draw_mark, \
    draw_star, FoldGlyph
from jarabe.journal.reflectionview import ReflectionView, RAIL_WIDTH
from jarabe.journal import reflectstyle


# The entry page's desk: kraft paper under white cards. Colors live
# in reflectstyle.

# The work mounted at a constant size: one box for every activity,
# the same one whether it holds artwork, a staged moment or words.
_ART_W = style.zoom(672)
_ART_H = style.zoom(336)
_MOUNT_PAD = style.zoom(14)
_MOUNT_BORDER = style.zoom(2)
_MOUNT_W = _ART_W + 2 * (_MOUNT_PAD + _MOUNT_BORDER)
_MOUNT_H = _ART_H + 2 * (_MOUNT_PAD + _MOUNT_BORDER)
_TAPE_L = style.zoom(88)
_TAPE_W = style.zoom(32)
_TAPE_IN = style.zoom(12)
_CORNER_PEEK = style.zoom(12)

_MINI_W = style.zoom(252)
_MINI_SNAP_W = style.zoom(234)
_MINI_SNAP_H = style.zoom(130)
_MINI_PAD = style.zoom(9)
_MINI_BAND_H = style.zoom(40)
_MINI_MARGIN = style.zoom(14)
_MINI_TILT = 1.1 * math.pi / 180.0

# A short shelf stays whole; only a longer one folds.
_RAIL_FOLD_AFTER = 6

_css_registered = False


def _blend_to_white(color, amount):
    r, g, b = (int(color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    return '#%02X%02X%02X' % (int(r + (255 - r) * amount),
                              int(g + (255 - g) * amount),
                              int(b + (255 - b) * amount))


def _kid_colors():
    stroke = profile.get_color().get_stroke_color()
    return stroke, _blend_to_white(stroke, 0.60), \
        _blend_to_white(stroke, 0.88)


def _ensure_css():
    global _css_registered
    if _css_registered:
        return
    _css_registered = True

    stroke, kid_fill, kid_tint = _kid_colors()

    px = reflectstyle.px

    css = ("""
        .journal-page {
            background-image: linear-gradient(to bottom,
                %(kraft)s, %(kraft_deep)s);
        }
        .journal-titlerow {
            background-color: %(paper)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z14)dpx;
            box-shadow: 0 2px 8px rgba(58, 50, 38, 0.09);
        }
        .journal-title-entry {
            font-family: %(font_hand)s;
            font-size: %(z28)dpx;
            color: %(ink)s;
            background-color: transparent;
            border: %(z2)dpx solid transparent;
            border-radius: %(z10)dpx;
            padding: %(z2)dpx %(z8)dpx;
            caret-color: %(ink)s;
        }
        .journal-title-entry:focus { border-color: %(rim)s; }
        .journal-when {
            font-family: %(font_clear)s;
            font-size: %(z15)dpx; color: %(ink_soft)s;
        }
        .journal-lead-label {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(z14)dpx;
            color: %(ink_soft)s; letter-spacing: 2px;
        }
        .journal-desc {
            background-color: %(paper)s;
            border: %(z2)dpx solid %(rim)s;
            border-top-width: 0;
            border-radius: 0 0 %(z10)dpx %(z10)dpx;
            box-shadow: 0 3px 8px rgba(58, 50, 38, 0.09);
        }
        .journal-desc-label {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(z13)dpx;
            color: %(ink_soft)s; letter-spacing: 1px;
        }
        .journal-desc-text, .journal-desc-text text {
            font-family: %(font_hand)s;
            font-size: %(z21)dpx; color: %(ink)s;
            background-color: transparent;
            caret-color: %(stroke)s;
        }
        .journal-none {
            font-family: %(font_hand)s;
            font-size: %(z22)dpx; color: %(ink_soft)s;
        }
        .journal-kq {
            font-family: %(font_hand)s;
            font-size: %(z26)dpx; color: %(stroke)s;
        }
        .journal-kq-soft {
            font-family: %(font_hand)s;
            font-size: %(z26)dpx; color: %(ink)s;
        }
        .journal-stagecap {
            font-family: %(font_hand)s;
            font-size: %(z19)dpx; color: %(ink)s;
        }
        .journal-back-pill {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: 12.5px;
            color: %(ink_soft)s; background-color: %(card)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z999)dpx; padding: %(z3)dpx %(z12)dpx;
        }
        .journal-back-pill:active { background-color: %(rim)s; }
        .journal-tag-add {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(z16)dpx;
            color: %(tag_add)s; background-color: transparent;
            border: %(z2)dpx dashed %(tag_add)s;
            border-radius: %(z8)dpx; padding: %(z5)dpx %(z14)dpx;
        }
        .journal-tag-input {
            font-family: %(font_hand)s;
            font-size: %(z17)dpx; color: %(ink)s;
            background-color: %(paper)s;
            border: %(z2)dpx solid %(tag_line)s;
            border-radius: %(z8)dpx; padding: %(z5)dpx %(z12)dpx;
            min-width: %(z2)dpx;
        }
        .journal-railfold {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: 13.5px;
            color: %(ink_soft)s; background-color: %(card)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z999)dpx; padding: %(z7)dpx %(z16)dpx;
        }
        .journal-railfold:active { background-color: %(rim)s; }
        .journal-comment {
            background-color: %(card)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z14)dpx;
            box-shadow: 0 2px 6px rgba(58, 50, 38, 0.09);
        }
        .journal-comment-who {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(z14)dpx; color: %(ink_soft)s;
        }
        .journal-comment-said {
            font-family: %(font_hand)s;
            font-size: %(z19)dpx; color: %(ink)s;
        }
        .journal-comment-erase {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(z18)dpx; color: %(ink_faint)s;
            background-color: transparent; background-image: none;
            border: none; box-shadow: none; padding: 0 %(z6)dpx;
        }
        .journal-comment-erase:active { color: %(stroke)s; }
        .journal-confirm-line {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(z13)dpx; color: %(ink_soft)s;
        }
        .journal-confirm-pill {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: 12.5px;
            color: %(ink_soft)s; background-color: %(card)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z999)dpx; padding: %(z2)dpx %(z12)dpx;
        }
        .journal-confirm-yes {
            color: %(stroke)s; border-color: %(stroke)s;
        }
        .journal-tech-line {
            font-family: %(font_clear)s;
            font-size: %(z12)dpx; color: %(ink_soft)s;
        }
        .journal-field-label {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(z12)dpx; color: %(ink_soft)s;
        }
        .journal-body, .journal-body text {
            font-family: %(font_clear)s;
            font-size: %(z14)dpx; color: %(ink)s;
        }
        .journal-page scrollbar { background-color: transparent; }
        .journal-page scrollbar trough {
            background-color: transparent; border: none;
        }
        .journal-page scrollbar slider {
            background-color: rgba(138, 128, 112, 0.35);
            border-radius: %(z999)dpx; min-width: %(z8)dpx; border: none;
        }
        .journal-page scrollbar slider:hover {
            background-color: rgba(138, 128, 112, 0.6);
        }
        """) % {
        'kraft': reflectstyle.KRAFT,
        'kraft_deep': reflectstyle.KRAFT_DEEP,
        'paper': reflectstyle.PAPER_PAGE,
        'card': reflectstyle.CARD,
        'rim': reflectstyle.RIM_PAGE,
        'ink': reflectstyle.INK_PAGE,
        'ink_soft': reflectstyle.INK_SOFT_PAGE,
        'ink_faint': reflectstyle.INK_FAINT,
        'stroke': stroke,
        'tag_line': reflectstyle.TAG_LINE,
        'tag_add': reflectstyle.TAG_ADD,
        'font_hand': reflectstyle.FONT_HAND,
        'font_clear': reflectstyle.FONT_CLEAR,
        'z2': px(2), 'z3': px(3), 'z5': px(5), 'z6': px(6), 'z7': px(7),
        'z8': px(8), 'z10': px(10), 'z12': px(12), 'z13': px(13),
        'z14': px(14), 'z15': px(15), 'z16': px(16), 'z17': px(17),
        'z18': px(18), 'z19': px(19), 'z21': px(21), 'z22': px(22),
        'z26': px(26), 'z28': px(28), 'z999': px(999),
    }

    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode('utf-8'))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _measure_text(text, font, width=None):
    """Text metrics from the same cairo rasterizer that paints,
    so a request never disagrees with what gets drawn - and never
    drifts between refreshes as font contexts warm up.
    """
    surface = cairo.ImageSurface(cairo.FORMAT_A8, 1, 1)
    context = cairo.Context(surface)
    layout = PangoCairo.create_layout(context)
    layout.set_font_description(Pango.FontDescription(font))
    if width is not None:
        layout.set_width(width * Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_text(text, -1)
    return layout.get_pixel_size()


def _rounded_path(cr, x, y, w, h, r):
    deg = math.pi / 180.0
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -90 * deg, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 90 * deg)
    cr.arc(x + r, y + h - r, r, 90 * deg, 180 * deg)
    cr.arc(x + r, y + r, r, 180 * deg, 270 * deg)
    cr.close_path()


def _soft_shadow(cr, x, y, w, h, r, drop, strength):
    """A shadow without blur: nested rounded layers stepping outward,
    each one fainter, so the edge fades instead of printing.
    """
    layers = 8
    unit = strength / float(layers * (layers + 1) // 2)
    for i in range(layers, 0, -1):
        spread = i * 1.5
        cr.set_source_rgba(0.227, 0.196, 0.149,
                           unit * (layers + 1 - i))
        _rounded_path(cr, x - spread, y + drop - spread / 2.0,
                      w + spread * 2, h + spread * 1.5, r + spread)
        cr.fill()


def _set_source(cr, color):
    rgba = Gdk.RGBA()
    rgba.parse(color)
    Gdk.cairo_set_source_rgba(cr, rgba)


def _reveal(widget):
    """Show a no-show-all widget and everything inside it.

    The detail view calls show_all() over the whole page on every
    refresh; no-show-all is what keeps our hidden faces hidden, and
    this is the matching way to bring one back.
    """
    for child in widget.get_children():
        child.show_all()
    widget.show()


def _replace_child(box, widget, padding=0):
    for child in box.get_children():
        box.remove(child)
    box.pack_start(widget, False, False, padding)
    box.show_all()


def _decode_snap(encoded):
    """A moment's stored snapshot back as a pixbuf, or None."""
    if not encoded:
        return None
    try:
        raw = base64.b64decode(encoded)
        loader = GdkPixbuf.PixbufLoader()
        loader.write(raw)
        loader.close()
        return loader.get_pixbuf()
    except Exception:
        logging.exception('expandedentry: snap decode failed')
        return None


def _trim_letterbox(pixbuf):
    """Cut the stored preview's grey letterbox bars away.

    Stock previews are letterboxed onto panel grey at save time;
    inside the mount those bars would double-mat the work.
    """
    if pixbuf is None:
        return None
    try:
        grey = style.COLOR_PANEL_GREY.get_html().lstrip('#')
        target = tuple(int(grey[i:i + 2], 16) for i in (0, 2, 4))
        width, height = pixbuf.get_width(), pixbuf.get_height()
        channels = pixbuf.get_n_channels()
        stride = pixbuf.get_rowstride()
        pixels = pixbuf.get_pixels()

        def bar(x, y):
            offset = y * stride + x * channels
            return all(abs(pixels[offset + i] - target[i]) <= 8
                       for i in range(3))

        def row_is_bar(y):
            return all(bar(x, y) for x in
                       (0, width // 4, width // 2, 3 * width // 4,
                        width - 1))

        def col_is_bar(x):
            return all(bar(x, y) for y in
                       (0, height // 4, height // 2, 3 * height // 4,
                        height - 1))

        top = 0
        while top < height // 3 and row_is_bar(top):
            top += 1
        bottom = height
        while bottom > height * 2 // 3 and row_is_bar(bottom - 1):
            bottom -= 1
        left = 0
        while left < width // 3 and col_is_bar(left):
            left += 1
        right = width
        while right > width * 2 // 3 and col_is_bar(right - 1):
            right -= 1
        if top == 0 and left == 0 and bottom == height and right == width:
            return pixbuf
        return pixbuf.new_subpixbuf(left, top, right - left, bottom - top)
    except Exception:
        logging.exception('expandedentry: letterbox trim failed')
        return pixbuf


class BuddyList(Gtk.Alignment):

    def __init__(self, buddies):
        Gtk.Alignment.__init__(self)
        self.set(0, 0, 0, 0)

        hbox = Gtk.HBox()
        for buddy in buddies:
            nick_, color = buddy
            icon = CanvasIcon(icon_name='computer-xo',
                              xo_color=XoColor(color),
                              pixel_size=style.STANDARD_ICON_SIZE)
            icon.set_palette(BuddyPalette(buddy))
            hbox.pack_start(icon, True, True, 0)
        self.add(hbox)


class TextView(Gtk.TextView):

    def __init__(self):
        Gtk.TextView.__init__(self)
        text_buffer = Gtk.TextBuffer()
        self.set_buffer(text_buffer)
        self.set_left_margin(style.DEFAULT_PADDING)
        self.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.get_style_context().add_class('journal-body')


class CommentsView(Gtk.VBox):
    """Comments from friends as little speech cards.

    Same stored JSON in, same JSON out on erase - only the face
    changed; nothing here writes a comment.
    """

    __gsignals__ = {
        'comments-changed': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
    }

    FROM = 'from'
    MESSAGE = 'message'
    ICON = 'icon'
    ICON_COLOR = 'icon-color'

    def __init__(self):
        Gtk.VBox.__init__(self)
        self.props.spacing = style.DEFAULT_PADDING
        self._comments = []
        self._editable = True

    def set_editable(self, editable):
        self._editable = editable

    def update_comments(self, comments):
        for child in self.get_children():
            self.remove(child)
        self._comments = []
        if comments:
            try:
                self._comments = json.loads(comments)
            except ValueError:
                logging.exception('expandedentry: bad comments JSON')
                self._comments = []
        for comment in self._comments:
            self.pack_start(self._create_card(comment), False, False, 0)
        self.show_all()

    def _create_card(self, comment):
        holder = Gtk.VBox()
        holder.set_halign(Gtk.Align.START)
        tail = Gtk.DrawingArea()
        tail.set_size_request(style.zoom(44), style.zoom(11))
        tail.set_halign(Gtk.Align.START)
        tail.connect('draw', self._tail_draw_cb)
        holder.pack_start(tail, False, False, 0)
        card = Gtk.EventBox()
        card.get_style_context().add_class('journal-comment')
        card.set_halign(Gtk.Align.START)
        row = Gtk.HBox()
        row.set_spacing(style.DEFAULT_PADDING)
        row.set_border_width(style.zoom(9))

        icon = Icon(icon_name=comment.get(self.ICON, 'computer-xo'),
                    pixel_size=style.SMALL_ICON_SIZE)
        icon.props.xo_color = XoColor(
            comment.get(self.ICON_COLOR, '#FFFFFF,#000000'))
        icon.set_valign(Gtk.Align.START)
        row.pack_start(icon, False, False, 0)

        column = Gtk.VBox()
        who = Gtk.Label(label=comment.get(self.FROM, ''))
        who.get_style_context().add_class('journal-comment-who')
        who.set_xalign(0)
        column.pack_start(who, False, False, 0)
        said = Gtk.Label(label=comment.get(self.MESSAGE, ''))
        said.get_style_context().add_class('journal-comment-said')
        said.set_xalign(0)
        said.set_line_wrap(True)
        said.set_max_width_chars(30)
        column.pack_start(said, False, False, 0)
        row.pack_start(column, True, True, 0)

        if self._editable:
            erase = Gtk.Button(label='×')
            erase.set_relief(Gtk.ReliefStyle.NONE)
            erase.get_style_context().add_class('journal-comment-erase')
            erase.set_valign(Gtk.Align.START)
            erase.connect('clicked', self._erase_comment_cb,
                          comment, column)
            row.pack_start(erase, False, False, 0)

        card.add(row)
        holder.pack_start(card, False, False, 0)
        return holder

    def _tail_draw_cb(self, widget, cr):
        _set_source(cr, reflectstyle.CARD)
        height = widget.get_allocated_height()
        apex = style.zoom(31)
        half = style.zoom(9)
        cr.move_to(apex - half, height)
        cr.line_to(apex, 0)
        cr.line_to(apex + half, height)
        cr.close_path()
        cr.fill()
        return False

    def _erase_comment_cb(self, button, comment, column):
        # The question stands inside the card itself, no dialog: the
        # same speech bubble asks whether it should go.
        if getattr(column, '_confirm_row', None) is not None:
            return
        confirm = Gtk.HBox()
        confirm.set_spacing(style.DEFAULT_PADDING)
        confirm.set_margin_top(style.zoom(6))
        line = Gtk.Label(label=_('erase this comment?'))
        line.get_style_context().add_class('journal-confirm-line')
        confirm.pack_start(line, False, False, 0)
        yes = Gtk.Button(label=_('erase'))
        yes.set_relief(Gtk.ReliefStyle.NONE)
        yes.get_style_context().add_class('journal-confirm-pill')
        yes.get_style_context().add_class('journal-confirm-yes')
        yes.connect('clicked', self._erase_confirmed_cb, comment)
        confirm.pack_start(yes, False, False, 0)
        keep = Gtk.Button(label=_('keep'))
        keep.set_relief(Gtk.ReliefStyle.NONE)
        keep.get_style_context().add_class('journal-confirm-pill')
        keep.connect('clicked', self._erase_kept_cb, column)
        confirm.pack_start(keep, False, False, 0)
        column._confirm_row = confirm
        column.pack_start(confirm, False, False, 0)
        confirm.show_all()

    def _erase_confirmed_cb(self, button, comment):
        if comment in self._comments:
            self._comments.remove(comment)
            self.update_comments(json.dumps(self._comments))
            self.emit('comments-changed', json.dumps(self._comments))

    def _erase_kept_cb(self, button, column):
        confirm = getattr(column, '_confirm_row', None)
        if confirm is not None:
            column.remove(confirm)
            column._confirm_row = None


class _MountFace(Gtk.DrawingArea):
    """The constant mount: white card, rim, photo corners, and inside
    it either the work itself or a staged moment - always the same
    box, whatever the activity made.
    """

    __gsignals__ = {
        'tapped': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self._pixbuf = None
        stroke, _fill, _tint = _kid_colors()
        self._corner = _blend_to_white(stroke, 0.30)
        self.set_size_request(_MOUNT_W + 2 * _CORNER_PEEK,
                              _MOUNT_H + 2 * _CORNER_PEEK)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('button-release-event',
                     lambda w, e: self.emit('tapped'))
        self.connect('draw', self.__draw_cb)

    def set_pixbuf(self, pixbuf):
        self._pixbuf = pixbuf
        self.queue_draw()

    def __draw_cb(self, widget, cr):
        radius = style.zoom(6)
        cr.translate(_CORNER_PEEK, _CORNER_PEEK)
        rgba = Gdk.RGBA()

        cr.set_source_rgba(0.227, 0.196, 0.149, 0.05)
        for i in range(1, 5):
            _rounded_path(cr, -i * 0.4, style.zoom(3) + i * 1.3,
                          _MOUNT_W + i, _MOUNT_H, radius)
            cr.fill()

        _set_source(cr, reflectstyle.CARD)
        _rounded_path(cr, 0, 0, _MOUNT_W, _MOUNT_H, radius)
        cr.fill()
        _set_source(cr, reflectstyle.RIM_PAGE)
        cr.set_line_width(_MOUNT_BORDER)
        _rounded_path(cr, 1, 1, _MOUNT_W - 2, _MOUNT_H - 2, radius)
        cr.stroke()

        art_x = _MOUNT_PAD + _MOUNT_BORDER
        art_y = _MOUNT_PAD + _MOUNT_BORDER
        _set_source(cr, reflectstyle.ART_BG)
        cr.rectangle(art_x, art_y, _ART_W, _ART_H)
        cr.fill()

        if self._pixbuf is not None:
            sw = self._pixbuf.get_width()
            sh = self._pixbuf.get_height()
            # Cover, never fit: the work fills the whole mount and a
            # mismatched shape loses its edges, not its presence.
            scale = max(_ART_W / float(sw), _ART_H / float(sh))
            dw, dh = sw * scale, sh * scale
            dx = art_x + (_ART_W - dw) / 2.0
            dy = art_y + (_ART_H - dh) / 2.0
            cr.save()
            cr.rectangle(art_x, art_y, _ART_W, _ART_H)
            cr.clip()
            cr.translate(dx, dy)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
            cr.get_source().set_filter(cairo.Filter.GOOD)
            cr.paint()
            cr.restore()

        # Tape across each corner: the child's colour thinned to a
        # film so the work still shows through it.
        rgba.parse(self._corner)
        for cx, cy, dx, dy in (
                (0, 0, 1, 1),
                (_MOUNT_W, 0, -1, 1),
                (0, _MOUNT_H, 1, -1),
                (_MOUNT_W, _MOUNT_H, -1, -1)):
            cr.save()
            cr.translate(cx, cy)
            cr.rotate(-math.pi / 4 if dx * dy > 0 else math.pi / 4)
            # slide inward so the strip laps over the picture edge
            # instead of stopping on the white rim
            cr.translate(0, dy * _TAPE_IN)
            cr.translate(style.zoom(1), style.zoom(1))
            self.__tape(cr)
            cr.set_source_rgba(0.18, 0.15, 0.11, 0.14)
            cr.fill()
            cr.translate(-style.zoom(1), -style.zoom(1))
            # White film first, then the colour: colour alone stains
            # three tones over dark artwork and reads as a ribbon.
            self.__tape(cr)
            cr.set_source_rgba(1, 1, 1, 0.55)
            cr.fill()
            self.__tape(cr)
            cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 0.35)
            cr.fill()
            cr.restore()
        return False

    def __tape(self, cr):
        tl, tw = _TAPE_L / 2.0, _TAPE_W / 2.0
        z = style.zoom(7)
        cr.move_to(-tl, -tw)
        cr.line_to(tl, -tw)
        cr.line_to(tl - z, -tw * 0.5)
        cr.line_to(tl + z * 0.6, 0)
        cr.line_to(tl - z * 0.8, tw * 0.5)
        cr.line_to(tl + z * 0.3, tw)
        cr.line_to(-tl, tw)
        cr.line_to(-tl + z * 0.8, tw * 0.5)
        cr.line_to(-tl - z * 0.6, 0)
        cr.line_to(-tl + z, -tw * 0.5)
        cr.close_path()


class _MomentMini(Gtk.DrawingArea):
    """One moment on the shelf: a tilted little card carrying the
    snap, the caption, the mark and a star - drawn whole in cairo,
    since GTK has no CSS transform.
    """

    __gsignals__ = {
        'stage-tapped': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'star-tapped': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, moment, pixbuf, tilt_right, editable):
        Gtk.DrawingArea.__init__(self)
        self._caption = moment.get('caption', '')
        self._mark = moment.get('mark')
        self._pixbuf = pixbuf
        self._tilt = _MINI_TILT if tilt_right else -_MINI_TILT
        self._editable = editable
        self._starred = False
        self._onstage = False
        self._hover = False
        stroke, fill, tint = _kid_colors()
        self._stroke, self._fill, self._tint = stroke, fill, tint
        self._card_h = _MINI_PAD + _MINI_SNAP_H + _MINI_BAND_H
        self.set_size_request(_MINI_W + 2 * _MINI_MARGIN,
                              self._card_h + 2 * _MINI_MARGIN)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect('draw', self.__draw_cb)
        self.connect('button-release-event', self.__release_cb)
        self.connect('enter-notify-event', self.__enter_cb)
        self.connect('leave-notify-event', self.__leave_cb)

    def set_starred(self, starred):
        self._starred = starred
        self.queue_draw()

    def set_onstage(self, onstage):
        self._onstage = onstage
        self.queue_draw()

    def __enter_cb(self, widget, event):
        self._hover = True
        self.queue_draw()

    def __leave_cb(self, widget, event):
        self._hover = False
        self.queue_draw()

    def __star_rect(self):
        size = style.zoom(34)
        return (_MINI_W - _MINI_PAD - size,
                _MINI_PAD + _MINI_SNAP_H + (_MINI_BAND_H - size) / 2.0,
                size, size)

    def __release_cb(self, widget, event):
        # The tilt is a degree; hit zones ignore it.
        x = event.x - _MINI_MARGIN
        y = event.y - _MINI_MARGIN
        if not (0 <= x <= _MINI_W and 0 <= y <= self._card_h):
            return False
        if self._editable and self._caption:
            sx, sy, sw, sh = self.__star_rect()
            if sx <= x <= sx + sw and sy <= y <= sy + sh:
                self.emit('star-tapped')
                return True
        self.emit('stage-tapped')
        return True

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        cr.translate(alloc.width / 2.0, alloc.height / 2.0)
        cr.rotate(self._tilt)
        cr.translate(-_MINI_W / 2.0, -self._card_h / 2.0)

        radius = style.zoom(4)

        if self._onstage:
            _set_source(cr, self._fill)
            cr.set_line_width(style.zoom(3))
            _rounded_path(cr, -style.zoom(4), -style.zoom(4),
                          _MINI_W + style.zoom(8),
                          self._card_h + style.zoom(8),
                          radius + style.zoom(3))
            cr.stroke()

        _soft_shadow(cr, 0, 0, _MINI_W, self._card_h, radius,
                     style.zoom(3), 0.20 if self._hover else 0.13)

        _set_source(cr, reflectstyle.CARD)
        _rounded_path(cr, 0, 0, _MINI_W, self._card_h, radius)
        cr.fill()
        _set_source(cr, reflectstyle.RIM_PAGE)
        cr.set_line_width(2)
        _rounded_path(cr, 1, 1, _MINI_W - 2, self._card_h - 2, radius)
        cr.stroke()

        snap_x = _MINI_PAD
        snap_y = _MINI_PAD
        _set_source(cr, reflectstyle.ART_BG)
        cr.rectangle(snap_x, snap_y, _MINI_SNAP_W, _MINI_SNAP_H)
        cr.fill()
        if self._pixbuf is not None:
            sw = self._pixbuf.get_width()
            sh = self._pixbuf.get_height()
            scale = min(_MINI_SNAP_W / float(sw),
                        _MINI_SNAP_H / float(sh))
            dw, dh = sw * scale, sh * scale
            cr.save()
            cr.rectangle(snap_x, snap_y, _MINI_SNAP_W, _MINI_SNAP_H)
            cr.clip()
            cr.translate(snap_x + (_MINI_SNAP_W - dw) / 2.0,
                         snap_y + (_MINI_SNAP_H - dh) / 2.0)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
            cr.get_source().set_filter(cairo.Filter.GOOD)
            cr.paint()
            cr.restore()
        elif self._mark:
            size = style.zoom(50)
            cr.save()
            cr.translate(snap_x + (_MINI_SNAP_W - size) / 2.0,
                         snap_y + (_MINI_SNAP_H - size) / 2.0)
            cr.scale(size / 18.0, size / 18.0)
            draw_mark(cr, self._mark, reflectstyle.RIM_PAGE)
            cr.restore()

        if self._caption:
            layout = PangoCairo.create_layout(cr)
            layout.set_font_description(
                Pango.FontDescription(
                    '%s 12' % reflectstyle.FONT_HAND_FAMILY))
            star_room = style.zoom(40) if self._editable else _MINI_PAD
            layout.set_width(
                (_MINI_W - _MINI_PAD * 2 - star_room) * Pango.SCALE)
            layout.set_ellipsize(Pango.EllipsizeMode.END)
            layout.set_text(self._caption, -1)
            _tw, th = layout.get_pixel_size()
            _set_source(cr, reflectstyle.INK_PAGE)
            cr.move_to(_MINI_PAD + style.zoom(2),
                       _MINI_PAD + _MINI_SNAP_H +
                       (_MINI_BAND_H - th) / 2.0)
            PangoCairo.show_layout(cr, layout)

        if self._editable and self._caption:
            sx, sy, sw, sh = self.__star_rect()
            draw_star(cr, sx + sw / 2.0, sy + sh / 2.0,
                      style.zoom(9), self._starred,
                      self._stroke)

        if self._mark:
            badge_r = style.zoom(17)
            bx = _MINI_W - style.zoom(9)
            by = style.zoom(9)
            _set_source(cr, self._tint)
            cr.arc(bx, by, badge_r, 0, 2 * math.pi)
            cr.fill()
            _set_source(cr, self._stroke)
            cr.set_line_width(2)
            cr.arc(bx, by, badge_r, 0, 2 * math.pi)
            cr.stroke()
            size = badge_r * 1.9
            cr.save()
            cr.translate(bx - size / 2.0, by - size / 2.0)
            cr.scale(size / 18.0, size / 18.0)
            draw_mark(cr, self._mark, self._stroke)
            cr.restore()
        return False


class _TagSticker(Gtk.DrawingArea):
    """One tag as a paper label tied to the work; hovering shows the
    way to remove it.
    """

    __gsignals__ = {
        'remove-tapped': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    _PAD_L = style.zoom(26)
    _PAD_H = style.zoom(16)
    _PAD_V = style.zoom(7)
    _SLOT = style.zoom(18)
    _MARGIN = style.zoom(6)

    def __init__(self, tag, tilt_right, editable):
        Gtk.DrawingArea.__init__(self)
        self._tag = tag
        self._tilt = (1.0 if tilt_right else -1.4) * math.pi / 180.0
        self._editable = editable
        self._hover = False
        self._flash = False
        self._flash_sid = None
        self.connect('destroy', self.__destroy_cb)
        text_w, text_h = _measure_text(
            tag, '%s 13' % reflectstyle.FONT_HAND_FAMILY)
        # A single label never grows past the mount's width; a
        # too-long word trails off instead.
        slot = self._SLOT if editable else 0
        self._text_limit = _MOUNT_W - 2 * self._MARGIN - \
            self._PAD_L - self._PAD_H - slot
        text_w = min(text_w, self._text_limit)
        self._card_w = text_w + self._PAD_L + self._PAD_H + slot
        self._card_h = text_h + 2 * self._PAD_V
        self.set_size_request(self._card_w + 2 * self._MARGIN,
                              self._card_h + 2 * self._MARGIN)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect('draw', self.__draw_cb)
        self.connect('button-release-event', self.__release_cb)
        self.connect('enter-notify-event', self.__enter_cb)
        self.connect('leave-notify-event', self.__leave_cb)

    def __enter_cb(self, widget, event):
        self._hover = True
        self.queue_draw()

    def __leave_cb(self, widget, event):
        self._hover = False
        self.queue_draw()

    def flash(self):
        # Retyping an existing tag flashes it instead of doing nothing.
        self._flash = True
        self.queue_draw()
        self._flash_sid = GLib.timeout_add(900, self.__flash_off_cb)

    def __flash_off_cb(self):
        self._flash_sid = None
        self._flash = False
        self.queue_draw()
        return False

    def __destroy_cb(self, widget):
        # A rebuild can drop this sticker before the flash finishes;
        # the pending timeout must never fire on a dead widget.
        if self._flash_sid is not None:
            GLib.source_remove(self._flash_sid)
            self._flash_sid = None

    def __release_cb(self, widget, event):
        if not (self._editable and self._hover):
            return False
        x = event.x - self._MARGIN
        y = event.y - self._MARGIN
        if x >= self._card_w - self._SLOT - self._PAD_H / 2 and \
                0 <= y <= self._card_h:
            self.emit('remove-tapped')
            return True
        return False

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        cr.translate(alloc.width / 2.0, alloc.height / 2.0)
        cr.rotate(self._tilt)
        cr.translate(-self._card_w / 2.0, -self._card_h / 2.0)

        _soft_shadow(cr, 0, 0, self._card_w, self._card_h,
                     style.zoom(8), style.zoom(1), 0.07)
        _set_source(cr, reflectstyle.PAPER_PAGE)
        _rounded_path(cr, 0, 0, self._card_w, self._card_h,
                      style.zoom(8))
        cr.fill()
        _set_source(cr, _kid_colors()[0] if self._flash
                    else reflectstyle.RIM_PAGE)
        cr.set_line_width(2)
        _rounded_path(cr, 1, 1, self._card_w - 2, self._card_h - 2,
                      style.zoom(8))
        cr.stroke()

        _set_source(cr, reflectstyle.KRAFT)
        cr.arc(style.zoom(13), self._card_h / 2.0, style.zoom(4.5),
               0, 2 * math.pi)
        cr.fill()
        _set_source(cr, reflectstyle.TAG_LINE)
        cr.set_line_width(2)
        cr.arc(style.zoom(13), self._card_h / 2.0, style.zoom(4.5),
               0, 2 * math.pi)
        cr.stroke()

        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(
            Pango.FontDescription('%s 13' % reflectstyle.FONT_HAND_FAMILY))
        layout.set_width(self._text_limit * Pango.SCALE)
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_text(self._tag, -1)
        _set_source(cr, reflectstyle.INK_PAGE)
        cr.move_to(self._PAD_L, self._PAD_V)
        PangoCairo.show_layout(cr, layout)

        if self._editable and self._hover:
            reach = style.zoom(4)
            cx = self._card_w - self._PAD_H / 2 - self._SLOT / 2
            cy = self._card_h / 2.0
            _set_source(cr, reflectstyle.INK_FAINT)
            cr.set_line_width(2)
            cr.set_line_cap(cairo.LineCap.ROUND)
            cr.move_to(cx - reach, cy - reach)
            cr.line_to(cx + reach, cy + reach)
            cr.move_to(cx + reach, cy - reach)
            cr.line_to(cx - reach, cy + reach)
            cr.stroke()
        return False


class _KeptSlip(Gtk.DrawingArea):
    """One kept line as its own card; tapping its star removes it."""

    __gsignals__ = {
        'star-tapped': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    _PAD_L = style.zoom(14)
    _PAD_V = style.zoom(5)
    _STAR_ROOM = style.zoom(34)
    _MARGIN = style.zoom(6)

    def __init__(self, text, tilt_right, editable, max_width):
        Gtk.DrawingArea.__init__(self)
        self._text = text
        self._tilt = (0.5 if tilt_right else -0.6) * math.pi / 180.0
        self._editable = editable
        stroke, fill, _tint = _kid_colors()
        self._stroke, self._fill = stroke, fill
        limit = max_width - self._PAD_L - self._STAR_ROOM - \
            2 * self._MARGIN
        text_w, text_h = _measure_text(
            text, '%s 14' % reflectstyle.FONT_HAND_FAMILY, limit)
        self._card_w = min(text_w, limit) + self._PAD_L + self._STAR_ROOM
        self._card_h = text_h + 2 * self._PAD_V
        self.set_size_request(self._card_w + 2 * self._MARGIN,
                              self._card_h + 2 * self._MARGIN)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('draw', self.__draw_cb)
        self.connect('button-release-event', self.__release_cb)

    def __release_cb(self, widget, event):
        if not self._editable:
            return False
        x = event.x - self._MARGIN
        y = event.y - self._MARGIN
        if x >= self._card_w - self._STAR_ROOM and \
                0 <= y <= self._card_h:
            self.emit('star-tapped')
            return True
        return False

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        cr.translate(alloc.width / 2.0, alloc.height / 2.0)
        cr.rotate(self._tilt)
        cr.translate(-self._card_w / 2.0, -self._card_h / 2.0)

        radius = style.zoom(8)
        _soft_shadow(cr, 0, 0, self._card_w, self._card_h, radius,
                     style.zoom(1), 0.07)
        _set_source(cr, reflectstyle.CARD)
        _rounded_path(cr, 0, 0, self._card_w, self._card_h, radius)
        cr.fill()
        _set_source(cr, self._fill)
        cr.set_line_width(2)
        _rounded_path(cr, 1, 1, self._card_w - 2, self._card_h - 2,
                      radius)
        cr.stroke()

        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(
            Pango.FontDescription('%s 14' % reflectstyle.FONT_HAND_FAMILY))
        layout.set_width((self._card_w - self._PAD_L - self._STAR_ROOM) *
                         Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_text(self._text, -1)
        _set_source(cr, self._stroke)
        cr.move_to(self._PAD_L, self._PAD_V)
        PangoCairo.show_layout(cr, layout)

        draw_star(cr, self._card_w - self._STAR_ROOM / 2.0 - style.zoom(2),
                  self._card_h / 2.0, style.zoom(9), True, self._stroke)
        return False


class BaseExpandedEntry(GObject.GObject):

    def __init__(self):
        # Create a header
        self._keep_icon = None
        self._keep_sid = None
        self._icon = None
        self._icon_box = None
        self._title = None
        self._date = None

    def create_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self._keep_icon = self._create_keep_icon()
        header.pack_start(self._keep_icon, False, False, style.DEFAULT_SPACING)

        self._icon_box = Gtk.HBox()
        header.pack_start(self._icon_box, False, False, style.DEFAULT_SPACING)

        self._title = self._create_title()
        header.pack_start(self._title, True, True, 0)

        # TODO: create a version list popup instead of a date label
        self._date = self._create_date()
        header.pack_start(self._date, False, False, style.DEFAULT_SPACING)

        return header

    def _create_keep_icon(self):
        keep_icon = KeepIcon()
        return keep_icon

    def _create_title(self):
        entry = Gtk.Entry()
        return entry

    def _create_date(self):
        date = Gtk.Label()
        return date


class ExpandedEntry(Gtk.EventBox, BaseExpandedEntry):

    def __init__(self, journalactivity):
        BaseExpandedEntry.__init__(self)
        self._journalactivity = journalactivity
        Gtk.EventBox.__init__(self)
        _ensure_css()
        self.get_style_context().add_class('journal-page')

        self.in_focus = False
        self._metadata = None
        self._update_title_sid = None
        self._staged_seq = None
        self._rail_open = False
        self._kept_texts = []
        self._minis = []
        self._sidecol_moments = []
        self._sidecol_editable = False
        self._tag_commit = None
        self._tag_stickers = {}
        self._snap_cache = {}
        self._artwork_key = None
        self._artwork_pix = None
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('button-press-event', self.__page_press_cb)

        # Layout: the work and the child's words on the left, moments
        # and comments beside them, the talk with Jo as its own rail
        # on the right.
        page = Gtk.HBox()
        self.add(page)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.NONE)
        page.pack_start(scrolled, True, True, 0)

        main = Gtk.VBox()
        main.set_margin_top(style.zoom(24))
        main.set_margin_bottom(style.zoom(24))
        main.set_margin_start(style.zoom(44))
        main.set_margin_end(style.zoom(12))
        scrolled.add(main)

        header = self._create_titlerow()
        main.pack_start(header, False, False, 0)

        row = Gtk.HBox()
        row.set_spacing(style.zoom(32))
        row.set_margin_top(style.zoom(24))
        main.pack_start(row, False, False, 0)

        self._workcol = Gtk.VBox()
        self._workcol.set_size_request(_MOUNT_W, -1)
        row.pack_start(self._workcol, False, False, 0)

        self._sidecol = Gtk.VBox()
        self._sidecol.set_spacing(style.DEFAULT_PADDING)
        row.pack_start(self._sidecol, True, True, 0)

        self._build_workcol()

        foot = Gtk.HBox()
        foot.set_margin_top(style.DEFAULT_SPACING)
        self._technical_box = Gtk.VBox()
        foot.pack_start(self._technical_box, False, False, 0)
        self._buddy_list = Gtk.VBox()
        foot.pack_end(self._buddy_list, False, False, 0)
        main.pack_start(foot, False, False, 0)

        self._reflection = ReflectionView()
        self._reflection.connect('reflections-changed',
                                 self._reflections_changed_cb)
        self._reflection.connect('keep-toggled',
                                 self._reflection_keep_toggled_cb)
        page.pack_start(self._reflection, False, False, 0)

        self.show_all()
        if ReflectionView.rail_shut():
            self._reflection.hide()

    def set_rail_shown(self, shown):
        """The toolbar's word: show the talk or put it away. The
        choice holds for the whole session and is never written into
        the entry.
        """
        ReflectionView.set_rail_shut(not shown)
        # Order matters: the moments must narrow BEFORE the talk
        # returns, or their grid holds the width open and the talk
        # maps past the screen edge.
        if shown:
            if self._metadata is not None:
                self._refresh_sidecol(self._sidecol_moments,
                                      self._sidecol_editable)
            self._reflection.set_visible(True)
        else:
            self._reflection.set_visible(False)
            if self._metadata is not None:
                self._refresh_sidecol(self._sidecol_moments,
                                      self._sidecol_editable)

    def _create_titlerow(self):
        box = Gtk.EventBox()
        box.get_style_context().add_class('journal-titlerow')
        row = Gtk.HBox()
        row.set_spacing(style.DEFAULT_SPACING)
        row.set_border_width(style.zoom(4))
        box.add(row)

        self._icon_box = Gtk.HBox()
        self._icon_box.set_margin_start(style.zoom(16))
        row.pack_start(self._icon_box, False, False, 0)

        self._title = Gtk.Entry()
        self._title.get_style_context().add_class('journal-title-entry')
        self._title.connect('activate', self._title_entered)
        self._title.connect('focus-out-event', self._focus_out_cb)
        self._title.connect('focus-in-event', self._focus_in_cb)
        row.pack_start(self._title, True, True, 0)

        self._keep_icon = KeepIcon()
        # The only ember-colored star on the page.
        self._keep_icon.set_xo_color(
            XoColor('%s,%s' % (reflectstyle.EMBER, reflectstyle.EMBER)))
        self._keep_sid = self._keep_icon.connect(
            'toggled', self._keep_icon_toggled_cb)
        row.pack_start(self._keep_icon, False, False, 0)

        self._date = Gtk.Label()
        self._date.get_style_context().add_class('journal-when')
        self._date.set_margin_end(style.zoom(12))
        row.pack_start(self._date, False, False, 0)

        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            for child in row.get_children():
                row.reorder_child(child, 0)
        return box

    def _build_workcol(self):
        self._mount = _MountFace()
        self._mount.connect('tapped', self._mount_tapped_cb)
        overlay = Gtk.Overlay()
        overlay.add(self._mount)
        self._words_face = Gtk.VBox()
        self._words_face.set_spacing(style.zoom(22))
        self._words_face.set_halign(Gtk.Align.CENTER)
        self._words_face.set_valign(Gtk.Align.CENTER)
        self._words_face.set_no_show_all(True)
        overlay.add_overlay(self._words_face)
        overlay.set_overlay_pass_through(self._words_face, True)
        self._workcol.pack_start(overlay, False, False, 0)

        self._stagecap = Gtk.HBox()
        self._stagecap.set_spacing(style.DEFAULT_PADDING)
        self._stagecap.set_halign(Gtk.Align.CENTER)
        self._stagecap.set_margin_top(style.zoom(8))
        self._stagecap.set_no_show_all(True)
        self._workcol.pack_start(self._stagecap, False, False, 0)

        sheet = Gtk.EventBox()
        sheet.get_style_context().add_class('journal-desc')
        # anchored, not centered: centering re-seats the sheet any
        # time something momentarily widens the column
        sheet.set_halign(Gtk.Align.START)
        sheet.set_margin_start(style.zoom(21))
        sheet.set_size_request(style.zoom(668), -1)
        sheet.set_no_show_all(True)
        self._desc_sheet = sheet
        inner = Gtk.VBox()
        inner.set_border_width(style.zoom(12))
        sheet.add(inner)

        label = Gtk.Label(label=_('DESCRIPTION'))
        label.get_style_context().add_class('journal-desc-label')
        label.set_xalign(0)
        label.set_margin_start(style.zoom(10))
        inner.pack_start(label, False, False, 0)

        self._description = Gtk.TextView()
        self._description.set_buffer(Gtk.TextBuffer())
        self._description.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._description.set_left_margin(style.zoom(12))
        self._description.set_right_margin(style.zoom(12))
        self._description.set_pixels_below_lines(style.zoom(9))
        # room inside the view for the inviting blank line; anything
        # drawn past the allocation is clipped away
        self._description.set_bottom_margin(style.zoom(44))
        self._description.get_style_context().add_class('journal-desc-text')
        self._description.connect('focus-in-event', self._focus_in_cb)
        self._description.connect('focus-out-event',
                                  self._description_focus_out_event_cb)
        self._description.connect_after('draw', self._description_rules_cb)
        inner.pack_start(self._description, False, False, 0)

        self._kept_box = Gtk.VBox()
        self._kept_box.set_margin_top(style.zoom(6))
        self._kept_box.set_margin_bottom(style.zoom(4))
        self._kept_box.set_no_show_all(True)
        inner.pack_start(self._kept_box, False, False, 0)

        self._workcol.pack_start(sheet, False, False, 0)

        self._tagrow = Gtk.VBox()
        self._tagrow.set_spacing(style.zoom(4))
        self._tagrow.set_margin_top(style.zoom(16))
        self._tagrow.set_margin_start(style.zoom(18))
        self._tagrow.set_margin_end(style.zoom(18))
        self._workcol.pack_start(self._tagrow, False, False, 0)

    def set_metadata(self, metadata):
        if self._metadata == metadata:
            return
        first_look = self._metadata is None or \
            metadata.get('uid') != self._metadata.get('uid')
        self._metadata = metadata
        if first_look:
            self._staged_seq = None
            self._rail_open = False
            self._snap_cache.clear()
            self._artwork_key = None
            self._artwork_pix = None

        self._keep_icon.handler_block(self._keep_sid)
        self._keep_icon.set_active(int(metadata.get('keep', 0)) == 1)
        self._keep_icon.handler_unblock(self._keep_sid)

        self._icon = self._create_icon()
        _replace_child(self._icon_box, self._icon)

        self._date.set_text(misc.get_date(metadata))
        # A background save echoing back must never rewrite the field
        # under the child's cursor.
        if first_look or not self.in_focus:
            self._title.set_text(metadata.get('title', _('Untitled')))
        self._title.set_editable(model.is_editable(metadata))

        self._refresh_page()

        _replace_child(self._technical_box, self._create_technical(),
                       style.DEFAULT_SPACING)
        _replace_child(self._buddy_list, self._create_buddy_list(),
                       style.DEFAULT_SPACING)

        self._reflection.set_metadata(metadata)
        GLib.idle_add(self._reflection.focus_entry)

    def _refresh_page(self):
        """Everything below the title that follows the metadata:
        mount, staging, description zones, tags, moments, comments.
        """
        metadata = self._metadata
        editable = model.is_editable(metadata)
        moments = self._moments()
        if self._staged_seq is not None and \
                not any(m.get('snap_seq') == self._staged_seq
                        for m in moments):
            self._staged_seq = None

        self._refresh_mount(moments)
        self._refresh_description(editable)
        self._refresh_tags(editable)
        self._refresh_sidecol(moments, editable)

    def _moments(self):
        data = reflection.loads(self._metadata.get('reflections', ''))
        return list(reversed(data.get('moments', [])))

    def _staged_moment(self, moments):
        for moment in moments:
            if moment.get('snap_seq') == self._staged_seq:
                return moment
        return None

    def _snap_pixbuf(self, seq):
        # Snaps never change under a seq; decoding base64 JPEG on
        # every echo refresh is what made the page drag.
        if seq not in self._snap_cache:
            self._snap_cache[seq] = _decode_snap(
                self._metadata.get(SNAP_KEY % seq, ''))
        return self._snap_cache[seq]

    def _refresh_mount(self, moments):
        for child in self._stagecap.get_children():
            self._stagecap.remove(child)
        for child in self._words_face.get_children():
            self._words_face.remove(child)

        staged = self._staged_moment(moments)
        if staged is not None:
            snap = self._snap_pixbuf(staged.get('snap_seq'))
            self._mount.set_pixbuf(snap)
            self._words_face.hide()
            if staged.get('mark'):
                glyph = Gtk.DrawingArea()
                # Badge scale: below this the maze mark reads as a blob.
                size = style.zoom(32)
                glyph.set_size_request(size, size)
                glyph.connect('draw', self._stage_mark_draw_cb,
                              staged['mark'])
                self._stagecap.pack_start(glyph, False, False, 0)
            if staged.get('caption'):
                cap = Gtk.Label(label=staged['caption'])
                cap.get_style_context().add_class('journal-stagecap')
                cap.set_ellipsize(Pango.EllipsizeMode.END)
                cap.set_max_width_chars(40)
                self._stagecap.pack_start(cap, False, False, 0)
            back = Gtk.Button(label=_('back to the work'))
            back.set_relief(Gtk.ReliefStyle.NONE)
            back.get_style_context().add_class('journal-back-pill')
            back.connect('clicked', self._unstage_cb)
            self._stagecap.pack_start(back, False, False, 0)
            _reveal(self._stagecap)
            self._desc_sheet.hide()
            return

        self._stagecap.hide()
        _reveal(self._desc_sheet)

        artwork = self._artwork_pixbuf()
        if artwork is None:
            thumb = get_preview_pixbuf(self._metadata.get('preview', ''))
            artwork = _trim_letterbox(thumb)
        if artwork is not None:
            self._mount.set_pixbuf(artwork)
            self._words_face.hide()
            return

        # Not a picture: the honest face is the activity's own icon
        # and the child's kept words, inside the same mount.
        self._mount.set_pixbuf(None)
        icon = Icon(pixel_size=style.zoom(88))
        icon.props.file = misc.get_icon_name(self._metadata)
        icon.props.xo_color = misc.get_icon_color(self._metadata)
        self._words_face.pack_start(icon, False, False, 0)
        kepts = reflection.kept_lines(
            self._metadata.get('reflections', ''),
            self._metadata.get('description', ''), limit=2)
        if not kepts:
            none = Gtk.Label(label=_('nothing kept here yet'))
            none.get_style_context().add_class('journal-none')
            self._words_face.pack_start(none, False, False, 0)
        for position, line in enumerate(kepts):
            quote = Gtk.Label(label='“%s”' % line)
            quote.set_line_wrap(True)
            quote.set_max_width_chars(38)
            quote.set_justify(Gtk.Justification.CENTER)
            quote.get_style_context().add_class(
                'journal-kq' if position == 0 else 'journal-kq-soft')
            self._words_face.pack_start(quote, False, False, 0)
        _reveal(self._words_face)

    def _stage_mark_draw_cb(self, widget, cr, kind):
        size = min(widget.get_allocated_width(),
                   widget.get_allocated_height())
        cr.scale(size / 18.0, size / 18.0)
        draw_mark(cr, kind, _kid_colors()[0])
        return False

    def _mount_tapped_cb(self, widget):
        # Only active when a moment is staged: tapping again puts
        # the work back.
        if self._staged_seq is not None:
            self._staged_seq = None
            self._refresh_page()

    def _unstage_cb(self, button):
        self._staged_seq = None
        self._refresh_page()

    def _kept_sources(self):
        """Every text the child has starred somewhere: talk lines and
        moment captions.
        """
        data = reflection.loads(self._metadata.get('reflections', ''))
        texts = set()
        for session in data.get('sessions', []):
            for turn in session.get('turns', []):
                if turn.get('role') == reflection.ROLE_CHILD and \
                        turn.get('text'):
                    texts.add(turn['text'])
        for moment in data.get('moments', []):
            if moment.get('caption'):
                texts.add(moment['caption'])
        return texts

    def _split_description(self, description):
        """The two zones: the child's own writing, and the kept lines
        clustered at the tail.
        """
        sources = self._kept_sources()
        lines = (description or '').split('\n')
        kept = []
        while lines and lines[-1] and lines[-1] in sources:
            kept.insert(0, lines.pop())
        return '\n'.join(lines), kept

    def _full_description(self):
        bounds = self._description.get_buffer().get_bounds()
        typed = self._description.get_buffer().get_text(
            bounds[0], bounds[1], include_hidden_chars=False)
        typed = typed.rstrip('\n')
        if not self._kept_texts:
            return typed
        kept = '\n'.join(self._kept_texts)
        return (typed + '\n' + kept) if typed else kept

    def _refresh_description(self, editable):
        typed, kept = self._split_description(
            self._metadata.get('description', ''))
        self._kept_texts = kept
        # Trailing blanks collapse; the ruled paper offers its own
        # inviting blank line instead. While the child is typing, an
        # echo may refresh everything else, but never the words under
        # the cursor.
        if not self.in_focus:
            self._description.get_buffer().set_text(typed.rstrip('\n'))
        self._description.set_editable(editable)
        self._description.set_cursor_visible(editable)

        for child in self._kept_box.get_children():
            self._kept_box.remove(child)
        # Kept words came from the talk and the moments, starred by
        # the child - each is its own slip pasted under the writing,
        # tilted like everything else stuck to this desk. Short
        # slips share a row instead of each hoarding a whole line.
        max_width = style.zoom(600)
        row = None
        used = 0
        for position, text in enumerate(kept):
            slip = _KeptSlip(text, position % 2 == 1, editable,
                             max_width)
            slip.connect('star-tapped', self._kept_star_cb, text)
            slip.set_valign(Gtk.Align.START)
            need = slip.get_size_request()[0]
            if row is None or used + need > max_width:
                row = Gtk.HBox()
                self._kept_box.pack_start(row, False, False, 0)
                used = 0
            row.pack_start(slip, False, False, 0)
            used += need
        if kept:
            _reveal(self._kept_box)
        else:
            self._kept_box.hide()
        if not editable and not typed and not kept:
            self._desc_sheet.hide()

    def _description_rules_cb(self, text_view, cr):
        """Ruled paper under the child's writing: one line per line of
        text and one inviting blank below.
        """
        if not text_view.get_editable():
            return False
        buffer = text_view.get_buffer()
        alloc = text_view.get_allocation()
        _set_source(cr, reflectstyle.RULE_PAGE)
        cr.set_line_width(2)
        seen_y = []
        end = buffer.get_end_iter()
        line_iter = buffer.get_start_iter()
        while True:
            rect = text_view.get_iter_location(line_iter)
            wx, wy = text_view.buffer_to_window_coords(
                Gtk.TextWindowType.TEXT, rect.x, rect.y + rect.height)
            if not seen_y or wy > seen_y[-1]:
                seen_y.append(wy)
            if not text_view.forward_display_line(line_iter):
                break
        rect = text_view.get_iter_location(end)
        _wx, last_bottom = text_view.buffer_to_window_coords(
            Gtk.TextWindowType.TEXT, rect.x, rect.y + rect.height)
        step = style.zoom(36)
        rules = list(seen_y)
        if buffer.get_char_count():
            rules.append(last_bottom + step)
        for wy in rules:
            y = wy + style.zoom(4)
            if 0 <= y <= alloc.height:
                cr.move_to(style.zoom(2), y)
                cr.line_to(alloc.width - style.zoom(2), y)
                cr.stroke()
        return False

    def _commit_description(self, description, new_description, sync=False):
        if new_description != description:
            self._metadata['description'] = new_description
            self._write_entry()
            self._refresh_page()
            if sync:
                self._reflection.sync_kept(new_description)

    def _kept_star_cb(self, star, text):
        # Letting a kept line go un-stars it wherever it was starred.
        description = self._full_description()
        new_description = reflection.unkeep_from_description(
            description, text)
        self._commit_description(description, new_description, sync=True)

    def _refresh_tags(self, editable):
        # A background echo may rebuild this row while the child is
        # mid-word in the tag input; their word is saved first, never
        # destroyed under the cursor.
        if self._tag_commit is not None:
            commit = self._tag_commit
            self._tag_commit = None
            commit()
        for child in self._tagrow.get_children():
            self._tagrow.remove(child)
        pieces = []
        self._tag_stickers = {}
        tags = (self._metadata.get('tags', '') or '').split()
        for position, tag in enumerate(tags):
            sticker = _TagSticker(tag, position % 2 == 1, editable)
            sticker.connect('remove-tapped', self._tag_remove_cb, tag)
            self._tag_stickers[tag] = sticker
            pieces.append(sticker)
        if editable:
            add = Gtk.Button(label='+')
            add.set_relief(Gtk.ReliefStyle.NONE)
            add.get_style_context().add_class('journal-tag-add')
            add.set_can_focus(False)
            add.connect('clicked', self._tag_add_cb)
            add.set_valign(Gtk.Align.CENTER)
            pieces.append(add)

        # Hand-wrapped rows: the stickers keep their natural widths.
        # Stickers carry exact size requests; the theme sizes the + button
        # itself (and lies before realization), so it gets a
        # generous reservation - wrapping early is harmless,
        # allocating wide nudges the whole desk. The budget is the
        # mount's width minus this box's own side margins: the row
        # box re-adds them to whatever the widest row asks for.
        limit = _MOUNT_W + 2 * _CORNER_PEEK - 2 * style.zoom(18)
        row = None
        used = 0
        self._tag_plus_need = style.zoom(96)
        for piece in pieces:
            need = piece.get_size_request()[0]
            if need < 0:
                need = self._tag_plus_need
            if row is None or used + need > limit:
                row = Gtk.HBox()
                self._tagrow.pack_start(row, False, False, 0)
                used = 0
            row.pack_start(piece, False, False, 0)
            used += need
        self._tag_row_used = used
        self._tagrow.show_all()

    def _tag_remove_cb(self, sticker, tag):
        tags = (self._metadata.get('tags', '') or '').split()
        if tag in tags:
            tags.remove(tag)
            self._metadata['tags'] = ' '.join(tags)
            self._write_entry()
        self._refresh_tags(model.is_editable(self._metadata))

    def _tag_add_cb(self, button):
        entry = Gtk.Entry()
        entry.get_style_context().add_class('journal-tag-input')
        entry.set_placeholder_text(_('tag…'))
        entry.set_width_chars(8)
        entry.set_max_width_chars(8)
        row = button.get_parent()
        row.remove(button)
        # the input is a little wider than the +; only when it truly
        # would not fit does it take a fresh row (it paints ~90 wide
        # under the css cap - measured live, not guessed)
        if self._tag_row_used - self._tag_plus_need + \
                style.zoom(100) > \
                _MOUNT_W + 2 * _CORNER_PEEK - 2 * style.zoom(18):
            row = Gtk.HBox()
            self._tagrow.pack_start(row, False, False, 0)
            row.show()
        row.pack_start(entry, False, False, 0)
        entry.show()
        # after allocation, or the scroll-to-focus jumps to a stale
        # (0, 0) and yanks the page to the top
        GLib.idle_add(entry.grab_focus)
        done = [False]

        def close(save):
            if done[0]:
                return
            done[0] = True
            self._tag_commit = None
            already_here = None
            if save:
                value = '-'.join(entry.get_text().split())
                if value:
                    tags = (self._metadata.get('tags', '') or '').split()
                    if value not in tags:
                        tags.append(value)
                        self._metadata['tags'] = ' '.join(tags)
                        self._write_entry()
                    else:
                        already_here = value
            self._refresh_tags(model.is_editable(self._metadata))
            if already_here is not None:
                sticker = self._tag_stickers.get(already_here)
                if sticker is not None:
                    sticker.flash()

        def key_cb(widget, event):
            if event.keyval == Gdk.KEY_Escape:
                close(save=False)
                return True
            return False

        entry.connect('activate', lambda w: close(save=True))
        entry.connect('focus-out-event', lambda w, e: close(save=True))
        entry.connect('key-press-event', key_cb)
        # a tap anywhere else on the page also lets the entry go
        self._tag_commit = lambda: close(save=True)

    def _refresh_sidecol(self, moments, editable):
        self._sidecol_moments = moments
        self._sidecol_editable = editable
        for child in self._sidecol.get_children():
            self._sidecol.remove(child)
        self._minis = []

        # With the talk put away, the moments spread into its
        # width. Computed from the fixed page geometry, never from
        # allocations: a wide grid holds the window open, so its own
        # measure can never be trusted to shrink it again.
        side_w = Gdk.Screen.get_default().get_width() \
            - style.zoom(44 + 12 + 32) - (_MOUNT_W + 2 * _CORNER_PEEK)
        if not ReflectionView.rail_shut():
            side_w -= RAIL_WIDTH
        mini_w = _MINI_W + 2 * _MINI_MARGIN
        columns = max(2, int(round(side_w / float(mini_w))))
        description = self._metadata.get('description', '')
        if moments:
            lead = Gtk.Label(label=_('MOMENTS'))
            lead.get_style_context().add_class('journal-lead-label')
            lead.set_xalign(0)
            lead.set_margin_start(style.zoom(4))
            self._sidecol.pack_start(lead, False, False, 0)

            rail = Gtk.Grid()
            rail.set_column_spacing(0)
            rail.set_row_spacing(0)
            shown = moments if self._rail_open \
                else moments[:_RAIL_FOLD_AFTER]
            for position, moment in enumerate(shown):
                pixbuf = self._snap_pixbuf(moment.get('snap_seq'))
                mini = _MomentMini(moment, pixbuf,
                                   position % columns == columns - 1,
                                   editable)
                mini.set_onstage(
                    moment.get('snap_seq') == self._staged_seq)
                if moment.get('caption'):
                    mini.set_starred(reflection.has_kept_line(
                        description, moment['caption']))
                mini.connect('stage-tapped', self._mini_stage_cb, moment)
                mini.connect('star-tapped', self._mini_star_cb, moment)
                rail.attach(mini, position % columns,
                            position // columns, 1, 1)
                self._minis.append(mini)
            self._sidecol.pack_start(rail, False, False, 0)

            if len(moments) > _RAIL_FOLD_AFTER:
                fold = Gtk.Button()
                face = Gtk.HBox()
                face.set_spacing(style.DEFAULT_PADDING)
                face.pack_start(FoldGlyph(), False, False, 0)
                face.pack_start(Gtk.Label(
                    label=_('fewer') if self._rail_open
                    else _('the rest of your moments')), False, False, 0)
                fold.add(face)
                fold.set_relief(Gtk.ReliefStyle.NONE)
                fold.get_style_context().add_class('journal-railfold')
                fold.set_halign(Gtk.Align.START)
                fold.set_margin_start(style.zoom(15))
                fold.connect('clicked', self._railfold_cb)
                self._sidecol.pack_start(fold, False, False, 0)

        comments = CommentsView()
        comments.set_editable(editable)
        comments.connect('comments-changed', self._comments_changed_cb)
        comments.set_margin_start(style.zoom(15))
        comments.update_comments(self._metadata.get('comments', ''))
        self._sidecol.pack_start(comments, False, False, 0)
        self._sidecol.show_all()

    def _railfold_cb(self, button):
        self._rail_open = not self._rail_open
        self._refresh_page()

    def _mini_stage_cb(self, mini, moment):
        seq = moment.get('snap_seq')
        self._staged_seq = None if self._staged_seq == seq else seq
        self._refresh_page()

    def _mini_star_cb(self, mini, moment):
        caption = moment.get('caption', '')
        if not caption:
            return
        description = self._full_description()
        if reflection.has_kept_line(description, caption):
            new_description = reflection.unkeep_from_description(
                description, caption)
        else:
            new_description = reflection.keep_in_description(
                description, caption)
        self._commit_description(description, new_description, sync=True)

    def _create_icon(self):
        icon = CanvasIcon(file_name=misc.get_icon_name(self._metadata))
        icon.connect_after('activate', self.__icon_activate_cb)

        if misc.is_activity_bundle(self._metadata):
            xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                          style.COLOR_TRANSPARENT.get_svg()))
        else:
            xo_color = misc.get_icon_color(self._metadata)
        icon.props.xo_color = xo_color

        icon.set_palette(ObjectPalette(self._journalactivity, self._metadata))

        return icon

    def _artwork_pixbuf(self):
        # The stored preview is a small thumbnail; for image work the
        # saved file IS the artwork, so the mount reads it at real
        # quality and only falls back to the thumbnail. Re-read only
        # when the work itself changed, not on every echo.
        mime = self._metadata.get('mime_type', '') or ''
        if not mime.startswith('image/'):
            return None
        key = (self._metadata.get('uid'),
               self._metadata.get('timestamp'))
        if key == self._artwork_key:
            return self._artwork_pix
        pixbuf = None
        try:
            path = model.get_file(self._metadata['uid'])
            if path:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
        except GLib.Error:
            pixbuf = None
        except Exception:
            logging.exception('Artwork lookup failed')
            pixbuf = None
        if pixbuf is not None:
            limit_w, limit_h = style.zoom(1280), style.zoom(760)
            if pixbuf.get_width() > limit_w or \
                    pixbuf.get_height() > limit_h:
                scale = min(limit_w / float(pixbuf.get_width()),
                            limit_h / float(pixbuf.get_height()))
                pixbuf = pixbuf.scale_simple(
                    int(pixbuf.get_width() * scale),
                    int(pixbuf.get_height() * scale),
                    GdkPixbuf.InterpType.BILINEAR)
        self._artwork_key = key
        self._artwork_pix = pixbuf
        return pixbuf

    def _create_technical(self):
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        if 'filesize' in self._metadata:
            filesize = self._metadata['filesize']
        else:
            filesize = model.get_file_size(self._metadata['uid'])

        lines = [
            _('Kind: %s') % (self._metadata.get('mime_type') or _('Unknown'),),
            _('Date: %s') % (self._format_date(),),
            _('Size: %s') % (format_size(int(filesize)))
        ]

        text = Gtk.Label(label=' · '.join(lines))
        text.get_style_context().add_class('journal-tech-line')
        text.set_xalign(0)
        vbox.pack_start(text, False, False, 0)

        return vbox

    def _format_date(self):
        if 'timestamp' in self._metadata:
            try:
                timestamp = float(self._metadata['timestamp'])
            except (ValueError, TypeError):
                logging.warning('Invalid timestamp for %r: %r',
                                self._metadata['uid'],
                                self._metadata['timestamp'])
            else:
                return time.strftime('%x', time.localtime(timestamp))
        return _('No date')

    def _create_buddy_list(self):
        # No orphan heading: the label appears only when somebody
        # actually worked on this together with the child.
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        buddies = []
        if self._metadata.get('buddies'):
            buddies = list(json.loads(self._metadata['buddies']).values())
        if not buddies:
            return vbox

        text = Gtk.Label(label=_('Participants'))
        text.get_style_context().add_class('journal-field-label')
        halign = Gtk.Alignment.new(0, 0, 0, 0)
        halign.add(text)
        vbox.pack_start(halign, False, False, 0)

        vbox.pack_start(BuddyList(buddies), False, False, 0)
        return vbox

    def reveal_reflection(self):
        # Hands the talk the keyboard, bringing it back first if it
        # was put away.
        if ReflectionView.rail_shut():
            self.set_rail_shown(True)
        GLib.idle_add(self._reflection.focus_entry)

    def _focus_in_cb(self, widget, event):
        self.in_focus = True

    def _focus_out_cb(self, widget, event):
        self.in_focus = False

    def _title_entered(self, widget):
        self._title_changed_event_cb(widget)
        self._title.hide()
        self._title.show()

    def _title_notify_text_cb(self, entry, pspec):
        if not self._update_title_sid:
            self._update_title_sid = \
                GLib.timeout_add_seconds(1,
                                         self._update_title_cb)

    def _title_changed_event_cb(self, widget):
        old_title = self._metadata.get('title', None)
        new_title = self._title.get_text()
        if old_title != new_title:
            if new_title == '' or new_title.isspace():
                alert = ConfirmationAlert()
                alert.props.title = _('Empty title')
                alert.props.msg = _('The title is usually not left empty')
                alert.connect(
                    'response',
                    self._title_alert_response_cb,
                    old_title,
                    self._metadata.get('title_set_by_user', 0)
                )
                journalwindow.get_journal_window().add_alert(alert)
                alert.show()

            self._update_entry()

    def _title_alert_response_cb(self, alert, response_id, old_title,
                                 old_title_set_by_user):
        journalwindow.get_journal_window().remove_alert(alert)

        if response_id is Gtk.ResponseType.CANCEL:
            self._title.set_text(old_title)
            self._icon.palette.props.primary_text = old_title
            self._metadata['title'] = old_title
            self._metadata['title_set_by_user'] = old_title_set_by_user
            self._update_entry(needs_update=True)

    def _description_focus_out_event_cb(self, text_view, event):
        self._update_entry()

    def _comments_changed_cb(self, event, comments):
        self._metadata['comments'] = comments
        self._write_entry()

    def _reflections_changed_cb(self, view, reflections, next_steps):
        self._metadata['reflections'] = reflections
        # Unconditional: a retired note clears only if '' is written.
        self._metadata['next_steps'] = next_steps
        self._write_entry()
        # New moments or turns may have landed; the shelf follows.
        self._refresh_page()

    def _reflection_keep_toggled_cb(self, view, text, kept):
        description = self._full_description()
        if kept:
            new_description = reflection.keep_in_description(
                description, text)
        else:
            new_description = reflection.unkeep_from_description(
                description, text)
        self._commit_description(description, new_description)

    def _update_entry(self, needs_update=False):
        self.in_focus = False
        if not model.is_editable(self._metadata):
            return

        old_title = self._metadata.get('title', None)
        new_title = self._title.get_text()
        if old_title != new_title:
            self._icon.palette.props.primary_text = new_title
            self._metadata['title'] = new_title
            self._metadata['title_set_by_user'] = '1'
            needs_update = True

        old_description = self._metadata.get('description', None)
        new_description = self._full_description()
        if old_description != new_description:
            self._metadata['description'] = new_description
            needs_update = True

        if needs_update:
            self._write_entry()

        self._update_title_sid = None

    def _write_entry(self):
        if self._metadata.get('mountpoint', '/') == '/':
            model.write(self._metadata, update_mtime=False)
        else:
            old_file_path = os.path.join(
                self._metadata['mountpoint'],
                model.get_file_name(self._metadata['title'],
                                    self._metadata['mime_type']))
            model.write(self._metadata, file_path=old_file_path,
                        update_mtime=False)

    def _keep_icon_toggled_cb(self, keep_icon):
        if keep_icon.get_active():
            self._metadata['keep'] = '1'
        else:
            self._metadata['keep'] = '0'
        self._update_entry(needs_update=True)

    def __icon_activate_cb(self, button):
        misc.resume(self._metadata,
                    alert_window=journalwindow.get_journal_window())
        return True

    def __page_press_cb(self, widget, event):
        if self._tag_commit is not None:
            self._tag_commit()
        return False
