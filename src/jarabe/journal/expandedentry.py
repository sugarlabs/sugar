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
from sugar3.graphics.icon import CanvasIcon, get_icon_file_name
from sugar3.graphics.icon import Icon, CellRendererIcon
from sugar3.graphics.alert import Alert, ConfirmationAlert
from sugar3.util import format_size
from sugar3.graphics.objectchooser import get_preview_pixbuf
from sugar3.activity.activity import PREVIEW_SIZE

from jarabe.journal.keepicon import KeepIcon
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import misc
from jarabe.journal import model
from jarabe.journal import journalwindow
from jarabe.journal.momentcard import draw_mark, draw_star
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


class Separator(Gtk.VBox):

    def __init__(self, orientation):
        Gtk.VBox.__init__(
            self, background_color=style.COLOR_PANEL_GREY.get_gdk_color())


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


class CommentsView(Gtk.TreeView):
    __gsignals__ = {
        'comments-changed': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
        'clicked': (GObject.SignalFlags.RUN_FIRST, None, [object]),
    }

    FROM = 'from'
    MESSAGE = 'message'
    ICON = 'icon'
    ICON_COLOR = 'icon-color'
    COMMENT_ICON = 0
    COMMENT_ICON_COLOR = 1
    COMMENT_FROM = 2
    COMMENT_MESSAGE = 3
    COMMENT_ERASE_ICON = 4
    COMMENT_ERASE_ICON_COLOR = 5

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.set_headers_visible(False)
        self._store = Gtk.ListStore(str, object, str, str, str, object)
        self._comments = []
        self._init_model()

    def update_comments(self, comments):
        self._store.clear()

        if comments:
            self._comments = json.loads(comments)
            for comment in self._comments:
                self._add_row(comment.get(self.FROM, ''),
                              comment.get(self.MESSAGE, ''),
                              comment.get(self.ICON, 'computer-xo'),
                              comment.get(self.ICON_COLOR, '#FFFFFF,#000000'))

    def _get_selected_row(self):
        selection = self.get_selection()
        return selection.get_selected()

    def _add_row(self, sender, message, icon_name, icon_color):
        self._store.append((get_icon_file_name(icon_name),
                            XoColor(icon_color),
                            sender,
                            message,
                            get_icon_file_name('list-remove'),
                            XoColor('#FFFFFF,#000000')))

    def _init_model(self):
        self.set_model(self._store)
        col = Gtk.TreeViewColumn()

        who_icon = CellRendererCommentIcon()
        col.pack_start(who_icon, False)
        col.add_attribute(who_icon, 'file-name', self.COMMENT_ICON)
        col.add_attribute(who_icon, 'xo-color', self.COMMENT_ICON_COLOR)

        who_text = Gtk.CellRendererText()
        col.pack_start(who_text, True)
        col.add_attribute(who_text, 'text', self.COMMENT_FROM)

        comment_text = Gtk.CellRendererText()
        col.pack_start(comment_text, True)
        col.add_attribute(comment_text, 'text', self.COMMENT_MESSAGE)

        erase_icon = CellRendererCommentIcon()
        erase_icon.connect('clicked', self._erase_comment_cb)
        col.pack_start(erase_icon, False)
        col.add_attribute(erase_icon, 'file-name', self.COMMENT_ERASE_ICON)
        col.add_attribute(
            erase_icon, 'xo-color', self.COMMENT_ERASE_ICON_COLOR)

        self.append_column(col)

    def _erase_comment_cb(self, widget, event):
        alert = Alert()

        entry = self.get_selection().get_selected()[1]
        erase_string = _('Erase')
        alert.props.title = erase_string
        alert.props.msg = _('Do you want to permanently erase \"%s\"?') \
            % self._store[entry][self.COMMENT_MESSAGE]

        icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), icon)
        icon.show()

        ok_icon = Icon(icon_name='dialog-ok')
        alert.add_button(Gtk.ResponseType.OK, erase_string, ok_icon)
        ok_icon.show()

        alert.connect('response', self._erase_alert_response_cb, entry)

        journalwindow.get_journal_window().add_alert(alert)
        alert.show()

    def _erase_alert_response_cb(self, alert, response_id, entry):
        journalwindow.get_journal_window().remove_alert(alert)

        if response_id is Gtk.ResponseType.OK:
            self._store.remove(entry)

            # Regenerate comments from current contents of store
            self._comments = []
            for entry in self._store:
                self._comments.append({
                    self.FROM: entry[self.COMMENT_FROM],
                    self.MESSAGE: entry[self.COMMENT_MESSAGE],
                    self.ICON: entry[self.COMMENT_ICON],
                    self.ICON_COLOR: '[%s]' % (
                        entry[self.COMMENT_ICON_COLOR].to_string()),
                })

            self.emit('comments-changed', json.dumps(self._comments))


class CellRendererCommentIcon(CellRendererIcon):

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.SMALL_ICON_SIZE
        self.props.height = style.SMALL_ICON_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_BLACK.get_svg()
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE


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
        self._vbox = Gtk.VBox()
        self.add(self._vbox)

        self.in_focus = False
        self._metadata = None
        self._update_title_sid = None

        self.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        self._header = self.create_header()
        self._vbox.pack_start(self._header, False, False,
                              style.DEFAULT_SPACING * 2)
        self._keep_sid = self._keep_icon.connect(
            'toggled', self._keep_icon_toggled_cb)
        self._title.connect('activate', self._title_entered)
        self._title.connect(
            'focus-out-event', self._focus_out_cb)
        self._title.connect(
            'focus-in-event', self._focus_in_cb)

        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            # Reverse header children.
            for child in self._header.get_children():
                self._header.reorder_child(child, 0)

        # Create a two-column body
        body_box = Gtk.EventBox()
        body_box.set_border_width(style.DEFAULT_SPACING)
        body_box.modify_bg(Gtk.StateType.NORMAL,
                           style.COLOR_WHITE.get_gdk_color())
        self._vbox.pack_start(body_box, True, True, 0)
        body = Gtk.HBox()
        body_box.add(body)

        first_column = Gtk.VBox()
        body.pack_start(first_column, False, False, style.DEFAULT_SPACING)

        second_column = Gtk.VBox()
        body.pack_start(second_column, True, True, 0)

        # First body column
        self._preview_box = Gtk.Frame()
        style_context = self._preview_box.get_style_context()
        style_context.add_class('journal-preview-box')
        first_column.pack_start(self._preview_box, False, True, 0)

        self._technical_box = Gtk.VBox()
        first_column.pack_start(self._technical_box, False, False, 0)

        # Second body column
        description_box, self._description = self._create_description()
        second_column.pack_start(description_box, True, True,
                                 style.DEFAULT_SPACING)

        tags_box, self._tags = self._create_tags()
        second_column.pack_start(tags_box, True, True,
                                 style.DEFAULT_SPACING)

        comments_box, self._comments = self._create_comments()
        second_column.pack_start(comments_box, True, True,
                                 style.DEFAULT_SPACING)

        self._buddy_list = Gtk.VBox()
        second_column.pack_start(self._buddy_list, True, False, 0)
        self.show_all()

    def set_metadata(self, metadata):
        if self._metadata == metadata:
            return
        self._metadata = metadata

        self._keep_icon.handler_block(self._keep_sid)
        self._keep_icon.set_active(int(metadata.get('keep', 0)) == 1)
        self._keep_icon.handler_unblock(self._keep_sid)

        self._icon = self._create_icon()
        for child in self._icon_box.get_children():
            self._icon_box.remove(child)
            # FIXME: self._icon_box.foreach(self._icon_box.remove)
        self._icon_box.pack_start(self._icon, False, False, 0)

        self._date.set_text(misc.get_date(metadata))

        self._title.set_text(metadata.get('title', _('Untitled')))

        if self._preview_box.get_child():
            self._preview_box.remove(self._preview_box.get_child())
        self._preview_box.add(self._create_preview())

        for child in self._technical_box.get_children():
            self._technical_box.remove(child)
            # FIXME: self._technical_box.foreach(self._technical_box.remove)
        self._technical_box.pack_start(self._create_technical(),
                                       False, False, style.DEFAULT_SPACING)

        for child in self._buddy_list.get_children():
            self._buddy_list.remove(child)
            # FIXME: self._buddy_list.foreach(self._buddy_list.remove)
        self._buddy_list.pack_start(self._create_buddy_list(), False, False,
                                    style.DEFAULT_SPACING)

        description = metadata.get('description', '')
        self._description.get_buffer().set_text(description)
        tags = metadata.get('tags', '')
        self._tags.get_buffer().set_text(tags)
        comments = metadata.get('comments', '')
        self._comments.update_comments(comments)

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

    def _create_preview(self):

        box = Gtk.EventBox()
        box.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        metadata = self._metadata
        pixbuf = get_preview_pixbuf(metadata.get('preview', ''))
        has_preview = pixbuf is not None

        if has_preview:
            im = Gtk.Image()
            im.set_from_pixbuf(pixbuf)
            box.add(im)
            im.show()
        else:
            label = Gtk.Label()
            label.set_text(_('No preview'))
            width, height = PREVIEW_SIZE[0], PREVIEW_SIZE[1]
            label.set_size_request(width, height)
            box.add(label)
            label.show()

        box.connect_after('button-release-event',
                          self._preview_box_button_release_event_cb)
        return box

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

        for line in lines:
            linebox = Gtk.HBox()
            vbox.pack_start(linebox, False, False, 0)

            text = Gtk.Label()
            text.set_markup('<span foreground="%s">%s</span>' % (
                style.COLOR_BUTTON_GREY.get_html(), line))
            linebox.pack_start(text, False, False, 0)

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

        text = Gtk.Label()
        text.set_markup('<span foreground="%s">%s</span>' % (
            style.COLOR_BUTTON_GREY.get_html(), _('Participants:')))
        halign = Gtk.Alignment.new(0, 0, 0, 0)
        halign.add(text)
        vbox.pack_start(halign, False, False, 0)

        vbox.pack_start(BuddyList(buddies), False, False, 0)
        return vbox

    def _create_scrollable(self, widget, label=None):
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        if label is not None:
            text = Gtk.Label()
            text.set_markup('<span foreground="%s">%s</span>' % (
                style.COLOR_BUTTON_GREY.get_html(), label))

            halign = Gtk.Alignment.new(0, 0, 0, 0)
            halign.add(text)
            vbox.pack_start(halign, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        scrolled_window.add(widget)
        vbox.pack_start(scrolled_window, True, True, 0)

        return vbox

    def _create_description(self):
        widget = TextView()
        widget.connect('focus-in-event', self._focus_in_cb)
        widget.connect('focus-out-event',
                       self._description_tags_focus_out_event_cb)
        return self._create_scrollable(widget, label=_('Description:')), widget

    def _create_tags(self):
        widget = TextView()
        widget.connect('focus-in-event', self._focus_in_cb)
        widget.connect('focus-out-event',
                       self._description_tags_focus_out_event_cb)
        return self._create_scrollable(widget, label=_('Tags:')), widget

    def _create_comments(self):
        widget = CommentsView()
        widget.connect('comments-changed', self._comments_changed_cb)
        widget.connect('focus-in-event', self._focus_in_cb)
        widget.connect('focus-out-event', self._focus_out_cb)
        return self._create_scrollable(widget, label=_('Comments:')), widget

    def _focus_in_cb(self, widget, event):
        self.in_focus = True

    def _focus_out_cb(self, widget, event):
        self.in_focus = False

    def _title_entered(self, widget):
        self._update_entry()
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

    def _title_alert_response_cb(self, alert, response_id, old_title, old_title_set_by_user):
        journalwindow.get_journal_window().remove_alert(alert)

        if response_id is Gtk.ResponseType.CANCEL:
            self._title.set_text(old_title)
            self._icon.palette.props.primary_text = old_title
            self._metadata['title'] = old_title
            self._metadata['title_set_by_user'] = old_title_set_by_user
            self._update_entry(needs_update=True)

    def _description_tags_focus_out_event_cb(self, text_view, event):
        self._update_entry()

    def _comments_changed_cb(self, event, comments):
        self._metadata['comments'] = comments
        self._write_entry()

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


        bounds = self._tags.get_buffer().get_bounds()
        old_tags = self._metadata.get('tags', None)
        new_tags = self._tags.get_buffer().get_text(bounds[0], bounds[1],
                                                    include_hidden_chars=False)

        if old_tags != new_tags:
            self._metadata['tags'] = new_tags
            needs_update = True

        bounds = self._description.get_buffer().get_bounds()
        old_description = self._metadata.get('description', None)
        new_description = self._description.get_buffer().get_text(
            bounds[0], bounds[1], include_hidden_chars=False)
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

    def _preview_box_button_release_event_cb(self, button, event):
        logging.debug('_preview_box_button_release_event_cb')
        misc.resume(self._metadata,
                    alert_window=journalwindow.get_journal_window())
        return True
