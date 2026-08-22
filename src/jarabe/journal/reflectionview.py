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

"""Jo's talk as the entry page's right-hand rail.

The scrollback is the whole history - nothing folds.
"""

import logging
import threading
import time
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gtk

from sugar3 import profile
from sugar3.graphics import style

from jarabe.journal import model
from jarabe.journal import reflection
from jarabe.journal import reflectguard
from jarabe.journal.momentcard import draw_star, FoldGlyph
from jarabe.journal.joglyph import (JoGlyph, MOOD_QUIET, MOOD_THINKING,
                                    animations_enabled)
from jarabe.journal import reflectstyle


# At most two starters; finishing the thought answers for the child.
STARTER_CHIPS = [
    _('The tricky part was...'),
    _('I think...'),
]

# Chips come down after this many answers in a session.
CHIPS_HIDE_AFTER = 2


SESSION_OVER_LINE = _('Jo said goodbye for now.')

QUIET_LINE = _('Nothing to ask right now. Jo will read what you '
               'leave here.')

READ_ONLY_LINE = _('You can read this one, but not write on it.')
COPY_IN_LINE = _('Copy this into your Journal to talk about it '
                 'with Jo.')

_css_registered = False

RAIL_WIDTH = style.zoom(560)


def _ensure_css():
    """Load the talk rail's chrome once per process. Every rule is
    scoped by a reflection-* class; the child's own XO color is fixed
    for the life of the shell, so it is safe to bake in.
    """
    global _css_registered
    if _css_registered:
        return
    _css_registered = True

    stroke = profile.get_color().get_stroke_color()
    r, g, b = (int(stroke.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))

    def toward_white(amount):
        return '#%02X%02X%02X' % (int(r + (255 - r) * amount),
                                  int(g + (255 - g) * amount),
                                  int(b + (255 - b) * amount))

    kid_fill = toward_white(0.60)
    kid_tint = toward_white(0.88)

    def to_rgba(color, alpha):
        hr, hg, hb = (int(color.lstrip('#')[i:i + 2], 16)
                      for i in (0, 2, 4))
        return 'rgba(%d, %d, %d, %s)' % (hr, hg, hb, alpha)

    shadow_rgba = to_rgba(reflectstyle.INK_PAGE, 0.3)
    scrollbar_rgba = to_rgba(reflectstyle.INK_SOFT_PAGE, 0.35)

    px = reflectstyle.px
    pxf = reflectstyle.pxf

    css = ("""
        .reflection-rail {
            background-color: %(paper)s;
            border-left: %(z2)dpx solid %(rim)s;
        }
        .reflection-margin { background-color: %(margin_red)s; }
        .reflection-thread { background-color: transparent; }
        .reflection-turn-row {
            background-color: transparent;
            background-image: none;
        }
        .reflection-sessmark {
            font-family: %(font_clear)s;
            font-weight: 400; font-size: %(sessmark_size).1fpx;
            color: %(mark_ink)s; letter-spacing: %(sessmark_track).1fpx;
        }
        .reflection-jo {
            font-family: %(font_clear)s;
            font-size: %(jo_size).1fpx; color: %(ink)s;
        }
        .reflection-jo-bubble {
            background-color: %(card)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z14)dpx;
        }
        .reflection-note {
            font-family: %(font_clear)s;
            font-size: %(z14)dpx; color: %(ink_soft)s;
        }
        .reflection-kid-bubble {
            background-color: %(kid_tint)s;
            border: %(z2)dpx solid %(kid_fill)s;
            border-radius: %(z12)dpx;
        }
        .reflection-kid-words {
            font-family: %(font_hand)s;
            font-size: %(z19)dpx; color: %(stroke)s;
        }
        .reflection-now-bubble {
            background-color: %(card)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z18)dpx;
        }
        .reflection-now-words {
            font-family: %(font_clear)s;
            font-size: %(now_words_size).1fpx; color: %(ink)s;
        }
        .reflection-chip {
            font-family: %(font_clear)s;
            font-weight: 700; font-size: %(chip_size).1fpx;
            background-color: %(card)s;
            color: %(ink_soft)s;
            border: %(z2)dpx solid %(rim)s;
            border-radius: %(z999)dpx;
            padding: %(z8)dpx %(z16)dpx;
        }
        .reflection-chip:active { background-color: %(kid_tint)s; }
        .reflection-entry {
            font-family: %(font_hand)s;
            font-size: %(z21)dpx; color: %(ink)s;
            background-color: transparent;
            border: none; box-shadow: none;
            border-bottom: %(z3)dpx solid %(rule)s;
            border-radius: 0;
            padding: %(z8)dpx %(z6)dpx;
            caret-color: %(stroke)s;
        }
        .reflection-entry:disabled {
            background-color: transparent;
            border-bottom-color: %(rim)s;
        }
        .reflection-send {
            background-color: %(stroke)s;
            border: none;
            border-radius: %(z999)dpx;
            box-shadow: 0 4px 9px %(shadow_rgba)s;
        }
        .reflection-rail scrollbar { background-color: transparent; }
        .reflection-rail scrollbar trough {
            background-color: transparent; border: none;
        }
        .reflection-rail scrollbar slider {
            background-color: %(scrollbar_rgba)s;
            border-radius: %(z999)dpx; min-width: %(z8)dpx; border: none;
        }
        """) % {
        'paper': reflectstyle.PAPER_PAGE,
        'card': reflectstyle.CARD,
        'rim': reflectstyle.RIM_PAGE,
        'ink': reflectstyle.INK_PAGE,
        'ink_soft': reflectstyle.INK_SOFT_PAGE,
        'mark_ink': reflectstyle.MARK_INK,
        'margin_red': reflectstyle.MARGIN_RED,
        'rule': reflectstyle.RULE_PAGE,
        'stroke': stroke,
        'kid_fill': kid_fill,
        'kid_tint': kid_tint,
        'font_hand': reflectstyle.FONT_HAND,
        'font_clear': reflectstyle.FONT_CLEAR,
        'shadow_rgba': shadow_rgba,
        'scrollbar_rgba': scrollbar_rgba,
        'sessmark_size': pxf(10.5), 'sessmark_track': pxf(1.5),
        'jo_size': pxf(16.5), 'now_words_size': pxf(18.5),
        'chip_size': pxf(13.5),
        'z2': px(2), 'z3': px(3), 'z6': px(6), 'z8': px(8), 'z12': px(12),
        'z14': px(14), 'z16': px(16), 'z18': px(18), 'z19': px(19),
        'z21': px(21), 'z999': px(999),
    }

    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode('utf-8'))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _set_source(cr, color):
    rgba = Gdk.RGBA()
    rgba.parse(color)
    Gdk.cairo_set_source_rgba(cr, rgba)


def _draw_tail(widget, cr):
    _set_source(cr, reflectstyle.CARD)
    width = widget.get_allocated_width()
    height = widget.get_allocated_height()
    cr.move_to(width, 0)
    cr.line_to(0, height / 2.0)
    cr.line_to(width, height)
    cr.close_path()
    cr.fill()
    return False


def _when_label(timestamp):
    """Today, yesterday, a weekday for the near past, else the date."""
    try:
        timestamp = int(timestamp)
    except (TypeError, ValueError):
        return ''
    if timestamp <= 0:
        return ''
    now = time.localtime()
    then = time.localtime(timestamp)
    today = time.mktime((now.tm_year, now.tm_mon, now.tm_mday,
                         0, 0, 0, 0, 0, -1))
    days = int((today - time.mktime((then.tm_year, then.tm_mon,
                                     then.tm_mday, 0, 0, 0, 0, 0, -1))) //
               86400)
    if days <= 0:
        return _('TODAY')
    if days == 1:
        return _('YESTERDAY')
    if days < 7:
        return time.strftime('%A', then).upper()
    return time.strftime('%x', then).upper()


class _SendArrow(Gtk.DrawingArea):
    """The send button's arrow, white on the child's own stroke color."""

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        size = style.zoom(18)
        self.set_size_request(size, size)
        self.connect('draw', self.__draw_cb)

    def __draw_cb(self, widget, cr):
        allocation = widget.get_allocation()
        size = min(allocation.width, allocation.height)
        cr.save()
        cr.translate((allocation.width - size) / 2.0 + size * 0.08,
                     (allocation.height - size) / 2.0)
        cr.scale(size / 18.0, size / 18.0)
        cr.set_source_rgb(1, 1, 1)
        cr.move_to(3, 3.5)
        cr.line_to(15.5, 9)
        cr.line_to(3, 14.5)
        cr.close_path()
        cr.fill()
        cr.restore()
        return False


class _TalkStar(Gtk.DrawingArea):
    """The keep-star at a bubble's shoulder, lit in the child's color."""

    __gsignals__ = {
        'toggled': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        size = style.zoom(30)
        self.set_size_request(size, size)
        self._active = False
        self._stroke = profile.get_color().get_stroke_color()
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('button-release-event', self.__release_cb)
        self.connect('draw', self.__draw_cb)

    def get_active(self):
        return self._active

    def set_active_quiet(self, active):
        self._active = active
        self.queue_draw()

    def __release_cb(self, widget, event):
        self._active = not self._active
        self.queue_draw()
        self.emit('toggled')
        return True

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        draw_star(cr, alloc.width / 2.0, alloc.height / 2.0,
                  style.zoom(12), self._active, self._stroke)
        return False


class _TurnRow(Gtk.ListBoxRow):
    """One turn in the chat: Jo plain on the left, the child a bubble
    on the right. The keep-star shows when kept or hovered.
    """

    def __init__(self, role, text, star_cb=None, kept=False,
                 animate=True):
        Gtk.ListBoxRow.__init__(self)
        self.set_selectable(False)
        self.set_activatable(False)
        self.get_style_context().add_class('reflection-turn-row')
        self.text = text
        self._star = None
        self._star_cb = star_cb
        self._kept = kept
        self._fade_tick = None

        if role == reflection.ROLE_JO:
            pair = Gtk.HBox()
            pair.set_halign(Gtk.Align.START)
            pair.set_margin_bottom(style.zoom(10))
            pair.set_margin_end(style.zoom(40))
            tail = Gtk.DrawingArea()
            tail.set_size_request(style.zoom(11), style.zoom(16))
            tail.set_valign(Gtk.Align.START)
            tail.set_margin_top(style.zoom(12))
            tail.connect('draw', _draw_tail)
            pair.pack_start(tail, False, False, 0)
            bubble = Gtk.EventBox()
            bubble.get_style_context().add_class('reflection-jo-bubble')
            label = Gtk.Label(label=text)
            label.get_style_context().add_class('reflection-jo')
            label.set_line_wrap(True)
            label.set_xalign(0)
            label.set_max_width_chars(38)
            label.set_margin_top(style.zoom(7))
            label.set_margin_bottom(style.zoom(7))
            label.set_margin_start(style.zoom(15))
            label.set_margin_end(style.zoom(15))
            bubble.add(label)
            pair.pack_start(bubble, False, False, 0)
            outer = pair
        else:
            hover = Gtk.EventBox()
            hover.get_style_context().add_class('reflection-turn-row')
            hover.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                             Gdk.EventMask.LEAVE_NOTIFY_MASK)
            row = Gtk.HBox()
            row.set_spacing(style.DEFAULT_PADDING)
            row.set_halign(Gtk.Align.END)
            row.set_margin_bottom(style.zoom(16))
            row.set_margin_end(style.zoom(12))
            if star_cb is not None:
                self._star = _TalkStar()
                self._star.set_valign(Gtk.Align.CENTER)
                if kept:
                    self._star.set_active_quiet(True)
                self._star.connect('toggled', self.__star_toggled_cb)
                self._star.set_opacity(1.0 if kept else 0.0)
                row.pack_start(self._star, False, False, 0)
            bubble = Gtk.EventBox()
            bubble.get_style_context().add_class('reflection-kid-bubble')
            words = Gtk.Label(label=text)
            words.get_style_context().add_class('reflection-kid-words')
            words.set_line_wrap(True)
            words.set_xalign(0)
            words.set_max_width_chars(30)
            words.set_margin_top(style.zoom(9))
            words.set_margin_bottom(style.zoom(9))
            words.set_margin_start(style.zoom(16))
            words.set_margin_end(style.zoom(16))
            bubble.add(words)
            row.pack_start(bubble, False, False, 0)
            hover.add(row)
            hover.connect('enter-notify-event', self.__enter_cb)
            hover.connect('leave-notify-event', self.__leave_cb)
            outer = hover

        self._revealer = Gtk.Revealer()
        self._revealer.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_UP
            if animate and animations_enabled()
            else Gtk.RevealerTransitionType.NONE)
        self._revealer.set_transition_duration(200)
        self._revealer.add(outer)
        self.add(self._revealer)
        self.show_all()
        GLib.idle_add(self._revealer.set_reveal_child, True)

    def set_kept(self, kept):
        """Light or dim the star without re-writing anything."""
        if self._star is None or kept == self._kept:
            return
        self._kept = kept
        self._star.set_active_quiet(kept)
        self._star.set_opacity(1.0 if kept else 0.0)

    def __fade_star(self, target):
        # With animations off, the star appears instantly.
        star = self._star
        if star is None:
            return
        if not animations_enabled():
            star.set_opacity(target)
            return
        if self._fade_tick is not None:
            star.remove_tick_callback(self._fade_tick)
            self._fade_tick = None
        start = star.get_opacity()
        if abs(start - target) < 0.01:
            star.set_opacity(target)
            return
        beat = {'start': None}

        def tick(widget, clock):
            if beat['start'] is None:
                beat['start'] = clock.get_frame_time()
            gone = (clock.get_frame_time() - beat['start']) / 140000.0
            if gone >= 1.0:
                widget.set_opacity(target)
                self._fade_tick = None
                return False
            widget.set_opacity(start + (target - start) * gone)
            return True

        self._fade_tick = star.add_tick_callback(tick)

    def __enter_cb(self, widget, event):
        # The bubble and star own their own windows, so crossing onto
        # them fires an INFERIOR event on this row - ignore it.
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        self.__fade_star(1.0)

    def __leave_cb(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        if not self._kept:
            self.__fade_star(0.0)

    def __star_toggled_cb(self, star):
        self._kept = star.get_active()
        self._star.set_opacity(1.0 if self._kept else 0.0)
        if self._star_cb is not None:
            self._star_cb(star, self.text)


class _FoldRow(Gtk.ListBoxRow):
    """The older talk, folded: everything is kept, one pill away."""

    __gsignals__ = {
        'fold-tapped': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Gtk.ListBoxRow.__init__(self)
        self.set_activatable(False)
        button = Gtk.Button()
        face = Gtk.HBox()
        face.set_spacing(style.DEFAULT_PADDING)
        face.pack_start(FoldGlyph(), False, False, 0)
        self._label = Gtk.Label(label=_('the talk from before'))
        face.pack_start(self._label, False, False, 0)
        button.add(face)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('journal-railfold')
        button.set_can_focus(False)
        button.connect('clicked', lambda widget: self.emit('fold-tapped'))
        holder = Gtk.HBox()
        holder.pack_start(button, False, False, 0)
        holder.set_margin_bottom(style.zoom(12))
        self.add(holder)
        self.show_all()

    def set_open(self, is_open):
        self._label.set_text(
            _('fewer') if is_open else _('the talk from before'))


class _MarkRow(Gtk.ListBoxRow):
    """The date between sessions, centered."""

    def __init__(self, text):
        Gtk.ListBoxRow.__init__(self)
        self.set_selectable(False)
        self.set_activatable(False)
        self.get_style_context().add_class('reflection-turn-row')
        label = Gtk.Label(label=text)
        label.get_style_context().add_class('reflection-sessmark')
        label.set_halign(Gtk.Align.CENTER)
        label.set_margin_top(style.zoom(22))
        label.set_margin_bottom(style.zoom(14))
        self.add(label)
        self.show_all()


class _NowRow(Gtk.ListBoxRow):
    """Jo's current question; dims and drops its bubble when over."""

    def __init__(self, text=None, thinking=False, over=False):
        Gtk.ListBoxRow.__init__(self)
        self.set_selectable(False)
        self.set_activatable(False)
        self.get_style_context().add_class('reflection-turn-row')
        self.text = text

        row = Gtk.HBox()
        row.set_spacing(style.zoom(16))
        row.set_margin_top(style.zoom(8))
        row.set_margin_bottom(style.zoom(8))

        self.glyph = JoGlyph(style.zoom(76))
        self.glyph.set_valign(Gtk.Align.START)
        if thinking:
            self.glyph.set_mood(MOOD_THINKING)
        if over:
            self.glyph.set_mood(MOOD_QUIET)
            self.glyph.set_opacity(0.45)
        row.pack_start(self.glyph, False, False, 0)

        if text and not thinking:
            tail = Gtk.DrawingArea()
            tail.set_size_request(style.zoom(13), style.zoom(18))
            tail.set_valign(Gtk.Align.START)
            tail.set_margin_top(style.zoom(26))
            tail.connect('draw', _draw_tail)
            pair = Gtk.HBox()
            pair.pack_start(tail, False, False, 0)
            # An EventBox's window is a rectangle - it squares off
            # rounded corners. A plain Box keeps the style windowless.
            bubble = Gtk.Box()
            bubble.get_style_context().add_class('reflection-now-bubble')
            bubble.set_valign(Gtk.Align.START)
            words = Gtk.Label(label=text)
            words.get_style_context().add_class('reflection-now-words')
            words.set_line_wrap(True)
            words.set_xalign(0)
            words.set_max_width_chars(28)
            words.set_margin_top(style.zoom(15))
            words.set_margin_bottom(style.zoom(15))
            words.set_margin_start(style.zoom(22))
            words.set_margin_end(style.zoom(22))
            bubble.add(words)
            pair.pack_start(bubble, False, False, 0)
            row.pack_start(pair, False, False, 0)

        self.add(row)
        self.show_all()


class ReflectionView(Gtk.EventBox):
    """Jo's talk rail for one Journal entry.

    All persistence goes through signals, so the entry's metadata
    keeps a single owner.
    """

    __gsignals__ = {
        'reflections-changed': (GObject.SignalFlags.RUN_FIRST, None,
                                ([str, str])),
        'keep-toggled': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, bool])),
    }

    # Shut on one page stays shut on the next. The switch lives in
    # the detail toolbar; this is only the memory.
    _shut = False

    @classmethod
    def rail_shut(cls):
        return cls._shut

    @classmethod
    def set_rail_shut(cls, shut):
        cls._shut = shut

    def __init__(self):
        Gtk.EventBox.__init__(self)
        _ensure_css()
        self.get_style_context().add_class('reflection-rail')

        self._metadata = None
        self._data = reflection.empty_conversation()
        self._session = None
        self._generation = 0
        self._request_active = False
        self._session_over = False
        self._opener_hint = None
        self._now_turn = None
        self._turn_rows = []
        self._fold_revealer = None
        self._fold_open = False
        self._answers_this_session = 0
        self._artifact_visible = False
        self._known_raw = None
        self._wants_focus = False
        self._editable = True
        self._now_row = None

        self.set_size_request(RAIL_WIDTH, -1)

        outer = Gtk.HBox()
        self.add(outer)

        margin_line = Gtk.EventBox()
        margin_line.get_style_context().add_class('reflection-margin')
        margin_line.set_size_request(style.zoom(2), -1)
        margin_line.set_margin_start(style.zoom(10))
        margin_line.set_margin_top(style.zoom(18))
        margin_line.set_margin_bottom(style.zoom(18))
        margin_line.set_opacity(0.55)
        outer.pack_start(margin_line, False, False, 0)

        column = Gtk.VBox()
        column.set_margin_top(style.zoom(24))
        column.set_margin_bottom(style.zoom(22))
        column.set_margin_start(style.zoom(14))
        column.set_margin_end(style.zoom(24))
        outer.pack_start(column, True, True, 0)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._listbox.get_style_context().add_class('reflection-thread')
        # A short talk sits at the bottom; a long one grows upward.
        anchor = Gtk.VBox()
        anchor.pack_end(self._listbox, False, False, 0)
        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_policy(Gtk.PolicyType.NEVER,
                                  Gtk.PolicyType.AUTOMATIC)
        self._scrolled.set_shadow_type(Gtk.ShadowType.NONE)
        self._scrolled.add(anchor)
        column.pack_start(self._scrolled, True, True, 0)
        self._at_bottom = True
        self._last_upper = 0.0
        self._fold_anchor = False
        adjustment = self._scrolled.get_vadjustment()
        adjustment.connect('value-changed', self.__scroll_value_cb)
        adjustment.connect('changed', self.__scroll_grew_cb)

        foot = Gtk.VBox()
        foot.set_spacing(style.DEFAULT_PADDING)
        foot.set_margin_top(style.zoom(14))
        column.pack_start(foot, False, False, 0)

        self._chips_row = Gtk.FlowBox()
        self._chips_row.set_selection_mode(Gtk.SelectionMode.NONE)
        self._chips_row.set_max_children_per_line(4)
        self._chips_row.set_column_spacing(style.zoom(10))
        self._chips_row.set_row_spacing(style.zoom(10))
        for chip_text in STARTER_CHIPS:
            chip = Gtk.Button(label=chip_text)
            chip.set_relief(Gtk.ReliefStyle.NONE)
            chip.get_style_context().add_class('reflection-chip')
            chip.connect('clicked', self.__chip_clicked_cb, chip_text)
            self._chips_row.add(chip)
        for child in self._chips_row.get_children():
            child.set_can_focus(False)
        foot.pack_start(self._chips_row, False, False, 0)

        self._input_row = Gtk.HBox()
        self._input_row.set_spacing(style.zoom(14))
        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text(_('type here...'))
        self._entry.get_style_context().add_class('reflection-entry')
        self._entry.connect('activate', self.__send_cb)
        self._input_row.pack_start(self._entry, True, True, 0)
        self._send_button = Gtk.Button()
        self._send_button.set_relief(Gtk.ReliefStyle.NONE)
        self._send_button.get_style_context().add_class('reflection-send')
        self._send_button.set_size_request(style.zoom(52), style.zoom(52))
        self._send_button.set_tooltip_text(_('Send'))
        self._send_button.add(_SendArrow())
        self._send_button.connect('clicked', self.__send_cb)
        self._input_row.pack_start(self._send_button, False, False, 0)
        foot.pack_start(self._input_row, False, False, 0)

        self._quiet_label = Gtk.Label()
        self._quiet_label.get_style_context().add_class('reflection-note')
        self._quiet_label.set_xalign(0)
        self._quiet_label.set_line_wrap(True)
        foot.pack_start(self._quiet_label, False, False, 0)

        self.show_all()
        self.set_no_show_all(True)
        self._quiet_label.hide()

    def focus_entry(self):
        """Focus the entry once a fresh page settles. The wish
        survives until the field is actually ready.
        """
        if not self._wants_focus:
            return False
        if self._entry.get_visible() and self._entry.get_sensitive():
            self._entry.grab_focus()
            self._wants_focus = False
        return False

    def sync_kept(self, description):
        """The description changed under the talk: re-light every
        star from what actually sits there now.
        """
        for row in self._turn_rows:
            row.set_kept(reflection.has_kept_line(description,
                                                  row.text))

    def set_metadata(self, metadata):
        # Metadata re-feeds on every datastore update, including this
        # view's own writes echoing back - a live talk must not
        # restart itself over its own echo.
        raw = metadata.get('reflections', '') or ''
        same_entry = self._metadata is not None and \
            metadata.get('uid') == self._metadata.get('uid')
        if same_entry and raw == self._known_raw:
            # A rename lands here (the talk is untouched): the opener
            # hint must follow the child's newest words, not quote a
            # title they just replaced.
            self._metadata = metadata
            self._opener_hint = self._build_opener_hint(metadata)
            return
        speak = not same_entry
        self._wants_focus = speak
        # An outside write (the running activity, the moment card)
        # re-enters here mid-question. The spoken-but-unanswered
        # question lives only in memory; carry it over the reload or
        # it vanishes from the rail and its answer opens a headless
        # session that defeats the wire latch.
        pending = None
        if same_entry and not self._session_over:
            pending = self._now_turn
            if pending is None and self._session is not None:
                turns = self._session.get('turns', [])
                if turns and all(t.get('role') == reflection.ROLE_JO
                                 for t in turns):
                    pending = dict(turns[-1])

        self._metadata = metadata
        self._known_raw = raw
        self._generation += 1
        self._request_active = False
        self._session_over = False
        self._answers_this_session = 0
        self._session = None
        self._now_row = None
        self._now_turn = None
        # New talk belongs only in the Journal's own store.
        self._editable = metadata.get('mountpoint', '/') == '/'
        self._data = reflection.loads(raw)
        self._artifact_visible = bool(metadata.get('preview'))
        self._opener_hint = self._build_opener_hint(metadata)

        for row in self._listbox.get_children():
            self._listbox.remove(row)
        self._show_history()

        self._quiet_label.hide()
        if self._editable:
            self._input_row.show()
            self._chips_row.show()
        else:
            # Read-only: no input, no chips, Jo asks nothing new. An
            # entry from another mount gets its own line instead -
            # its title may still be editable, so "can't write on
            # it" would read false there.
            self._input_row.hide()
            self._chips_row.hide()
            if metadata.get('mountpoint', '/') != '/':
                self._quiet_label.set_text(COPY_IN_LINE)
            else:
                self._quiet_label.set_text(READ_ONLY_LINE)
            self._quiet_label.show()
            self._scroll_to_newest()
            return

        if not speak:
            # An outside write mid-request lands here with the input
            # switched off for the dropped request; switch it back on.
            if pending is not None:
                self._now_turn = pending
                self._set_now(pending.get('text', ''))
            self._set_input_active(True)
            self._scroll_to_newest()
            return

        # Opening order: the intro once ever, then the hanging
        # question, then the peer/together/nearby openers, then the
        # engine.
        if not reflection.state_flag('intro'):
            reflection.mark_state('intro')
            self._speak(reflection.INTRO_LINE)
            return
        # A record ending on an unanswered Jo question re-presents
        # it; nothing else speaks until it has its answer.
        hanging = reflection.hanging_question(self._data)
        if hanging is not None:
            last_row = self._listbox.get_children()[-1]
            self._listbox.remove(last_row)
            # The re-presented question lives only in the old saved
            # session; the answer will open a new one. Carry the turn
            # (with its people/local latch) so the answer's session
            # starts with the question it answers - otherwise the
            # wire sees a headless reply and the latch never arms.
            saved = self._saved_turns()
            self._now_turn = dict(saved[-1]) if saved else \
                {'role': reflection.ROLE_JO, 'text': hanging}
            self._set_now(hanging)
            self._set_input_active(True)
            self._scroll_to_newest()
            return
        peer = reflection.peer_question(
            self._metadata.get('comments', ''),
            reflection.jo_texts(self._data))
        if peer is not None:
            self._speak(peer, peer=True)
            return
        used = reflection.used_floor_questions(self._data)
        together = reflection.together_question(self._metadata, used)
        if together is not None:
            self._speak(together)
            return
        follow = reflection.nearby_followup(used, self._data)
        if follow is not None:
            self._speak(follow)
            return
        self._request_next_turn()

    def _activity_id(self):
        return self._metadata.get('activity', '')

    def _build_opener_hint(self, metadata):
        """The child's own words for the floor's opener slot, if any.

        A title counts only when the toolkit flag says the child set
        it - auto "%s Activity" names carry the flag as '0'. Failing
        that, the newest moment caption; captions live inside the
        private reflections blob, so an opener quoting one is marked
        local and never rides the wire. The engine substitutes the
        hint only where the floor would open - a live server writes
        its own opener from richer context.
        """
        title = (metadata.get('title', '') or '').strip()
        if title and str(metadata.get('title_set_by_user', '0')) == '1':
            return {'text': reflection.titled_opener(title),
                    'q': reflection.opener_slot_id(
                        metadata.get('activity', ''))}
        for moment in reversed(self._data.get('moments', [])):
            caption = (moment.get('caption', '') or '').strip()
            if caption:
                return {'text': reflection.titled_opener(caption),
                        'q': reflection.opener_slot_id(
                            metadata.get('activity', '')),
                        'local': True}
        return None

    def _ensure_session(self):
        if self._session is None:
            self._session = reflection.new_session(
                reflection.get_category(self._activity_id()))
            self._session['sid'] = reflection.new_session_id()
            self._data['sessions'].append(self._session)
        return self._session

    def _persist(self):
        if self._session is not None and not any(
                turn.get('role') == reflection.ROLE_CHILD
                for turn in self._session.get('turns', ())):
            # Jo alone is not worth a write: nothing of the child's
            # exists to lose yet, and an opener written from a cold
            # boot-time read once flattened a real talk.
            return
        uid = (self._metadata or {}).get('uid')
        fresh_raw = ''
        if uid:
            try:
                fresh_raw = model.get(uid).get('reflections', '') or ''
            except Exception:
                logging.exception(
                    'reflection: could not re-read %r before write', uid)
                fresh_raw = self._metadata.get('reflections', '') or ''
        merged = reflection.merge_sessions_for_write(
            fresh_raw, self._data['sessions'])
        raw = reflection.dumps(merged)
        if reflection.count_turns(merged) < \
                reflection.total_turns(fresh_raw):
            # A talk only ever grows. Shrinking means this copy went
            # stale under another writer - losing our newest turn is
            # recoverable, destroying the child's record is not.
            logging.warning('reflection: refusing stale shrink write')
            return
        self._known_raw = raw
        if uid:
            reflectguard.get_guard().note_sessions(
                uid, reflection.loads(raw).get('sessions', []))
        next_steps = reflection.get_next_steps(self._metadata or {})
        if self._session is not None:
            next_steps = reflection.resolve_next_steps(
                self._session, next_steps)
        self.emit('reflections-changed', raw, next_steps)

    def _speak(self, text, peer=False):
        self._ensure_session()
        reflection.add_turn(self._session, reflection.ROLE_JO, text,
                            peer=peer)
        self._set_now(text)
        self._persist()
        self._set_input_active(True)
        self._scroll_to_newest()

    def _saved_turns(self):
        turns = []
        for session in self._data['sessions']:
            if session is not self._session:
                turns.extend(session.get('turns', []))
        return turns

    def _show_history(self):
        """Every saved session, oldest first, dated between sessions.
        Only the newest stands open; older talk waits behind a fold.
        """
        description = self._metadata.get('description', '')
        sessions = [s for s in self._data['sessions']
                    if s.get('turns')]
        many = len(sessions) > 1
        star_cb = self.__star_toggled_cb if self._editable else None
        last_when = None
        self._turn_rows = []
        self._fold_open = False
        fold_box = None
        if many:
            # One revealer holds the whole older talk, above the pill.
            # The reveal is deliberately instant - a slide would
            # fight the anchored viewport and race the scrollbar.
            self._fold_revealer = Gtk.Revealer()
            self._fold_revealer.set_transition_type(
                Gtk.RevealerTransitionType.NONE)
            fold_box = Gtk.VBox()
            self._fold_revealer.add(fold_box)
            holder = Gtk.ListBoxRow()
            holder.set_activatable(False)
            holder.get_style_context().add_class('reflection-turn-row')
            holder.add(self._fold_revealer)
            holder.show_all()
            self._listbox.add(holder)
            fold_row = _FoldRow()
            fold_row.connect('fold-tapped', self.__fold_cb)
            self._listbox.add(fold_row)
        else:
            self._fold_revealer = None
        for position, session in enumerate(sessions):
            folded = many and position < len(sessions) - 1
            if many and not folded:
                # the open talk names its day even if a folded
                # same-day session already did
                last_when = None
            if many:
                when = _when_label(session.get('ts'))
                if when and when != last_when:
                    self.__history_row(_MarkRow(when), fold_box, folded)
                    last_when = when
            for turn in session.get('turns', []):
                text = turn.get('text', '')
                if turn.get('role') == reflection.ROLE_CHILD:
                    row = _TurnRow(
                        reflection.ROLE_CHILD, text,
                        star_cb=star_cb,
                        kept=reflection.has_kept_line(description, text),
                        animate=False)
                    self._turn_rows.append(row)
                    self.__history_row(row, fold_box, folded)
                else:
                    self.__history_row(_TurnRow(
                        reflection.ROLE_JO, text, animate=False),
                        fold_box, folded)

    def __history_row(self, row, fold_box, folded):
        if folded:
            fold_box.pack_start(row, False, False, 0)
        else:
            self._listbox.add(row)

    def __fold_cb(self, fold_row):
        # The viewport rides the growth in the same frame, so the
        # pill never moves under the finger. The anchor releases
        # itself from the adjustment's own first post-reveal growth,
        # not a guessed delay.
        self._fold_anchor = True
        self._fold_open = not self._fold_open
        self._fold_revealer.set_reveal_child(self._fold_open)
        fold_row.set_open(self._fold_open)

    def _set_now(self, text=None, thinking=False, over=False):
        """Jo's current place: a question, thinking, or dimmed
        goodbye. What stood there before steps back into scrollback.
        """
        if self._now_row is not None:
            demoted = self._now_row.text
            self._listbox.remove(self._now_row)
            if demoted:
                self._listbox.add(_TurnRow(reflection.ROLE_JO, demoted,
                                           animate=False))
            self._now_row = None
        if text is None and not thinking and not over:
            return
        self._now_row = _NowRow(text=text, thinking=thinking, over=over)
        self._listbox.add(self._now_row)

    def _scroll_to_newest(self):
        self._at_bottom = True
        adjustment = self._scrolled.get_vadjustment()
        adjustment.set_value(
            adjustment.get_upper() - adjustment.get_page_size())

    def __scroll_value_cb(self, adjustment):
        self._at_bottom = adjustment.get_value() >= \
            adjustment.get_upper() - adjustment.get_page_size() - \
            style.zoom(24)

    def __scroll_grew_cb(self, adjustment):
        # New rows re-measure late (wrapped labels); a talk resting
        # on its floor follows the floor down in the same frame, so
        # sending never hops. While a fold slides, the view rides
        # the growth instead, holding the pill still.
        upper = adjustment.get_upper()
        if self._fold_anchor:
            delta = upper - self._last_upper
            if delta:
                adjustment.set_value(adjustment.get_value() + delta)
                self._fold_anchor = False
        elif self._at_bottom:
            adjustment.set_value(upper - adjustment.get_page_size())
        self._last_upper = upper

    def _add_child_row(self, text):
        star_cb = self.__star_toggled_cb if self._editable else None
        row = _TurnRow(reflection.ROLE_CHILD, text, star_cb=star_cb)
        self._turn_rows.append(row)
        self._listbox.add(row)
        self._scroll_to_newest()

    def _set_input_active(self, active):
        self._entry.set_sensitive(active)
        self._send_button.set_sensitive(active)
        if active and self._wants_focus:
            GLib.idle_add(self.focus_entry)

    def _request_next_turn(self):
        self._request_active = True
        self._set_input_active(False)
        self._set_now(thinking=True)
        self._scroll_to_newest()

        turns = []
        if self._session is not None:
            turns = list(self._session.get('turns', []))
        description = self._metadata.get('description', '')
        if reflection.people_kept_in_description(
                self._metadata.get('reflections', ''), description):
            # An older talk's starred answer names someone in the
            # room, and the description carries it verbatim.
            description = ''
        args = (self._metadata.get('uid', ''), self._generation,
                self._activity_id(), self._metadata.get('title', ''),
                description, turns,
                reflection.get_next_steps(self._metadata), self._data,
                self._artifact_visible, self._opener_hint)
        thread = threading.Thread(target=self.__request_worker, args=args)
        thread.daemon = True
        thread.start()

    def __request_worker(self, object_id, generation, activity_id, title,
                         description, turns, next_steps, conversation,
                         artifact_visible, opener):
        try:
            result = reflection.request_turn(
                object_id, generation, activity_id, title, description,
                turns, next_steps=next_steps, conversation=conversation,
                artifact_visible=artifact_visible, opener=opener)
        except Exception:
            # The rail must never stay wedged in "thinking": a dying
            # worker still reports, as Jo quietly bowing out.
            logging.exception('reflection: turn request failed')
            result = {'object_id': object_id, 'generation': generation,
                      'status': reflection.STATUS_OK, 'turn': None,
                      'should_continue': True, 'crashed': True}
        GLib.idle_add(self.__request_done_cb, result)

    def __request_done_cb(self, result):
        if result['generation'] != self._generation:
            return False

        self._request_active = False

        if result.get('crashed'):
            # Not a dry bank - the next send simply tries again.
            self._set_now()
            self._set_input_active(True)
            return False
        # The engine floors every server death itself, so a result is
        # always STATUS_OK: a turn to speak, or silence.
        turn = result['turn']
        end = result.get('end')
        if turn is not None:
            self._ensure_session()
            typed = turn if turn.get('kind') else None
            reflection.add_turn(self._session, reflection.ROLE_JO,
                                turn['text'], q=turn.get('q'),
                                local=bool(turn.get('local')),
                                typed=typed)
            self._set_now(turn['text'])
            self._persist()
            self._scroll_to_newest()
            if result['should_continue']:
                self._set_input_active(True)
            else:
                self._enter_session_over()
        elif end is not None:
            # The engine closed the session with a typed end; the
            # child's forward answer (or its absence) persists from
            # it, and the talk rests here for next time.
            self._ensure_session()
            self._session['end'] = end
            self._persist()
            self._enter_session_over()
        elif self._session is not None:
            nudge = None
            if result['should_continue']:
                # A dry bank points at the room before goodbye.
                nudge = reflection.nearby_nudge(
                    reflection.used_floor_questions(
                        self._data, self._session.get('turns', ())))
            if nudge is not None:
                self._speak(nudge)
            else:
                self._enter_session_over()
        else:
            # STATUS_OK with no turn to show: the quiet line is honest.
            self._show_quiet()
        return False

    def _enter_session_over(self):
        # The line never closes - words left now rest here for next time.
        self._session_over = True
        self._set_now(over=True)
        self._chips_row.hide()
        self._set_input_active(True)
        self._quiet_label.set_text(SESSION_OVER_LINE)
        self._quiet_label.show()
        self._scroll_to_newest()

    def _show_quiet(self):
        # A dry bank points at the room before it goes quiet.
        turns = ()
        if self._session is not None:
            turns = self._session.get('turns', ())
        nudge = reflection.nearby_nudge(
            reflection.used_floor_questions(self._data, turns))
        if nudge is not None:
            self._speak(nudge)
            return
        # Nothing left to ask and no server to ask for more.
        self._session_over = True
        self._set_now(over=True)
        self._chips_row.hide()
        self._set_input_active(True)
        self._quiet_label.set_text(QUIET_LINE)
        self._quiet_label.show()
        self._scroll_to_newest()

    def _send_text(self, text):
        if not text or self._request_active:
            return
        if self._session_over:
            # Jo is not asking, but the page still listens.
            self._ensure_session()
            reflection.add_turn(self._session, reflection.ROLE_CHILD,
                                text)
            self._set_now()
            self._add_child_row(text)
            self._persist()
            self._quiet_label.set_text(QUIET_LINE)
            self._quiet_label.show()
            return
        self._ensure_session()
        if self._now_turn is not None and not self._session.get('turns'):
            carried = self._now_turn
            reflection.add_turn(
                self._session, reflection.ROLE_JO,
                carried.get('text', ''), peer=bool(carried.get('peer')),
                q=carried.get('q'), local=bool(carried.get('local')))
        self._now_turn = None
        reflection.add_turn(self._session, reflection.ROLE_CHILD, text)
        self._set_now()
        self._add_child_row(text)
        self._answers_this_session += 1
        if self._answers_this_session >= CHIPS_HIDE_AFTER:
            self._chips_row.hide()
        self._persist()
        self._request_next_turn()

    def __send_cb(self, widget):
        text = self._entry.get_text().strip()
        if not text:
            return
        self._entry.set_text('')
        self._send_text(text)

    def __chip_clicked_cb(self, button, text):
        self._entry.set_text(text)
        self._entry.grab_focus()
        self._entry.set_position(-1)

    def __star_toggled_cb(self, button, text):
        self.emit('keep-toggled', text, button.get_active())
