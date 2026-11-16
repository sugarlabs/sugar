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

# A card-grid companion to listview.py's TreeView, bound to the same
# ListModel/query.

# Not Gtk.FlowBox: it picks one children-per-line count for the whole box.

import base64
import itertools
import logging
import math
import time
from gettext import gettext as _
from gettext import ngettext

import cairo
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Pango

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3 import util

from jarabe.journal.basejournalview import BaseJournalView
from jarabe.journal import model
from jarabe.journal import misc
from jarabe.journal import journalwindow
from jarabe.journal import timeline


# The card is designed around the stock 4:3 preview; the toolkit's
# The grid pins its own cell size: a larger toolkit PREVIEW_SIZE
# must never inflate it.
_PREVIEW_WIDTH, _PREVIEW_HEIGHT = style.zoom(300), style.zoom(225)
_CARD_PADDING = style.zoom(14)
_CARD_WIDTH = _PREVIEW_WIDTH + 2 * _CARD_PADDING
_CARD_RADIUS = style.zoom(28)
_PREVIEW_RADIUS = style.zoom(15)
_CARD_GAP = style.zoom(28)
_SHADOW_MARGIN = style.zoom(6)

_CAPTION_HEIGHT = style.zoom(66)
_CAPTION_INNER_GAP = style.zoom(11)
# GTK3 multiplies a trackpad's fractional delta by this same value.
_ROW_SCROLL_STEP = (_PREVIEW_HEIGHT + 2 * _CARD_PADDING + _CAPTION_HEIGHT +
                    _CARD_GAP)
_TOUCH_TARGET = style.zoom(46)
_TOUCH_GLYPH = style.zoom(27)

_PAGE_BG = timeline.PAGE_BG
_CARD_BG = style.COLOR_WHITE.get_html()
_TITLE_INK = timeline.DAY_INK
_BAND_INK = timeline.BAND_INK
_SCROLLBAR_WIDTH = timeline.SCROLLBAR_WIDTH
_SCROLLBAR_REST = timeline.SCROLLBAR_REST
_SCROLLBAR_HOVER = timeline.SCROLLBAR_HOVER

_DAY_TITLE_SIZE = timeline.DAY_TITLE_SIZE
_BAND_NAME_SIZE = timeline.BAND_NAME_SIZE
_CARD_TITLE_SIZE = style.zoom(18)
_META_SIZE = style.zoom(15)

_TRAY_HEADER_GAP = style.zoom(16)
_TRAY_HEADER_RADIUS = style.zoom(12)
_TRAY_HEADER_SLOT_HEIGHT = style.zoom(50)
_TRAY_CARD_GAP = style.zoom(14)

_BAND_GLYPH_SIZE = timeline.GLYPH_SIZE
_BAND_HEADER_GAP = style.zoom(16)
_DAY_TO_BAND_GAP = style.zoom(24)
_BAND_GAP = style.zoom(32)
_SECTION_GAP = style.zoom(48)

# Shared with listview.py, which reserves the same width in its own
# gutter column.
_SPINE_COLUMN_WIDTH = timeline.SPINE_SLOT_WIDTH

_FOLD_MIN_CARDS = timeline.FOLD_MIN_CARDS

_DISCLOSURE_SIZE = style.zoom(26)

_STACK_DEPTH = 1
_STACK_PEEK_X = style.zoom(18)
_STACK_PEEK_Y = style.zoom(24)
_STACK_CHIP_INSET = style.zoom(14)
_STACK_CHIP_PAD_X = style.zoom(8)
_STACK_CHIP_HEIGHT = style.zoom(24)
_SHEET_HOVER_NUDGE = style.zoom(6)
_SHEET_NUDGE_DURATION_US = 120 * 1000

# Gtk.Revealer reads transition-duration only when set_reveal_child starts,
# not when the property changes.
_TRAY_OPEN_DURATION_MS = 220
_TRAY_CLOSE_DURATION_MS = 160
_TRAY_RELAYOUT_SETTLE_MS = 40
# HACK: SLIDE_LEFT not SLIDE_RIGHT -- SLIDE_RIGHT pins the child to the
# revealer's right edge and slides every card sideways; SLIDE_LEFT pins it
# left so cards never move.
_TRAY_REVEAL_TRANSITION = Gtk.RevealerTransitionType.SLIDE_LEFT


_FOCUS_RING_WIDTH = style.zoom(3)

_SHADOW_HEX = '#282216'
_SHADOW_RGB01 = timeline.hex_to_rgb01(_SHADOW_HEX)
_SHADOW_COLOR = 'rgba(%d, %d, %d, %%.3f)' % timeline.hex_to_rgb(_SHADOW_HEX)
_SHADOW_ALPHA = 0.070
_SHADOW_BLUR = style.zoom(4)

_CARD_ELEVATION = {
    'rest': 1.0, 'hover': 1.3, 'press': 0.6,
    'lift': 1.6, 'lift_hover': 1.9, 'lift_press': 0.96,
}

# Left literal since style has no pressed-white token.
_CARD_BG_PRESSED = '#f0f0f0'


def _card_shadow(state):
    return '0 0 %dpx %s' % (
        _SHADOW_BLUR, _SHADOW_COLOR % (_SHADOW_ALPHA * _CARD_ELEVATION[state]))


_GRID_CSS = '''
.grid-page {
    background-color: %(page_bg)s;
}
.grid-day-title {
    font-size: %(day_size)dpx;
    font-weight: 700;
    color: %(title_ink)s;
}
.grid-band-label {
    font-size: %(band_size)dpx;
    font-weight: 600;
    color: %(band_ink)s;
}
.grid-card-title {
    font-size: %(card_title_size)dpx;
    font-weight: 600;
    color: %(title_ink)s;
}
.grid-card-subtitle {
    font-size: %(meta_size)dpx;
    font-weight: 400;
    color: %(meta_ink)s;
}
.grid-star-button, .grid-resume-button, .grid-select-button {
    background-color: transparent;
    border: none;
    padding: 0;
    min-width: %(touch)dpx;
    min-height: %(touch)dpx;
    border-radius: 999px;
}
.grid-sheet-hit {
    background-color: transparent;
}
.grid-star-button:hover, .grid-resume-button:hover,
.grid-select-button:hover {
    background-color: %(control_hover)s;
}
.grid-star-button:active, .grid-resume-button:active,
.grid-select-button:active {
    background-color: %(control_press)s;
}
.grid-tray-header {
    background-color: transparent;
    border-radius: %(tray_header_radius)dpx;
}
.grid-tray-header:hover {
    background-color: %(control_hover)s;
}
.grid-tray-header:active {
    background-color: %(control_press)s;
}
scrollbar.grid-scrollbar {
    background-color: transparent;
    background-image: none;
    border: none;
}
scrollbar.grid-scrollbar trough {
    background-color: %(page_bg)s;
    background-image: none;
    border: none;
}
scrollbar.grid-scrollbar slider {
    background-color: %(scrollbar_rest)s;
    background-image: none;
    border: none;
    border-radius: %(scrollbar_width)dpx;
    min-width: %(scrollbar_width)dpx;
}
scrollbar.grid-scrollbar slider:hover {
    background-color: %(scrollbar_hover)s;
}
.grid-disclosure {
    color: %(accent)s;
}
/* outline-offset pulls the ring inside the widget's own box. Left at
   0 the theme draws it entirely outside, where these controls -- a
   star and a resume button packed hard against the caption's edges --
   have no room of their own to draw it in. */
.grid-focus-round, .grid-focus-rect {
    outline: %(focus_width)dpx solid %(accent)s;
    outline-offset: -%(focus_width)dpx;
}
.grid-focus-round {
    -gtk-outline-radius: 999px;
}
.grid-focus-rect {
    -gtk-outline-radius: %(tray_header_radius)dpx;
}
/* The card's paper and the shadow under it. The .lifted rules carry an
   extra class so they outrank the plain ones on specificity rather
   than on source order.
   grid-card, not journal-card: this provider is installed on the
   SCREEN, so a class name shared with another view is that view's
   problem too -- listview.py:1822 puts 'journal-card' on its own rows,
   and the box-shadow here reached every one of them (measured: 2696 px
   of shadow outside a list card that had none before). Every class this
   file installs is grid-prefixed for that reason; .lifted and .selected
   are safe unprefixed only because they are never used alone. */
.grid-card {
    background-color: %(card_bg)s;
    border-radius: %(card_radius)dpx;
    box-shadow: %(shadow_rest)s;
}
.grid-card:hover {
    box-shadow: %(shadow_hover)s;
}
.grid-card:active {
    background-color: %(card_bg_pressed)s;
    box-shadow: %(shadow_press)s;
}
.grid-card.lifted {
    box-shadow: %(shadow_lift)s;
}
.grid-card.lifted:hover {
    box-shadow: %(shadow_lift_hover)s;
}
.grid-card.lifted:active {
    background-color: %(card_bg_pressed)s;
    box-shadow: %(shadow_lift_press)s;
}
/* A ticked card keeps the ring the keyboard focus state draws, but on
   a class rather than a state, so a selection stays visible once the
   pointer or Tab moves elsewhere. */
.grid-card:focus, .grid-card.selected {
    outline: %(focus_width)dpx solid %(accent)s;
    outline-offset: -%(focus_width)dpx;
    -gtk-outline-radius: %(card_radius)dpx;
}
'''

_css_provider = None


def _get_css_provider():
    global _css_provider
    if _css_provider is None:
        _css_provider = Gtk.CssProvider()
        _css_provider.load_from_data((_GRID_CSS % {
            'page_bg': _PAGE_BG,
            'title_ink': _TITLE_INK,
            'band_ink': _BAND_INK,
            'meta_ink': timeline.META_INK,
            'tray_header_radius': _TRAY_HEADER_RADIUS,
            'touch': _TOUCH_TARGET,
            'control_hover': timeline.CONTROL_HOVER_TINT,
            'control_press': timeline.CONTROL_PRESS_TINT,
            'scrollbar_rest': _SCROLLBAR_REST,
            'scrollbar_hover': _SCROLLBAR_HOVER,
            'scrollbar_width': _SCROLLBAR_WIDTH,
            'day_size': _DAY_TITLE_SIZE,
            'band_size': _BAND_NAME_SIZE,
            'card_title_size': _CARD_TITLE_SIZE,
            'meta_size': _META_SIZE,
            'accent': timeline.owner_stroke_color(),
            'focus_width': _FOCUS_RING_WIDTH,
            'card_bg': _CARD_BG,
            'card_bg_pressed': _CARD_BG_PRESSED,
            'card_radius': _CARD_RADIUS,
            'shadow_rest': _card_shadow('rest'),
            'shadow_hover': _card_shadow('hover'),
            'shadow_press': _card_shadow('press'),
            'shadow_lift': _card_shadow('lift'),
            'shadow_lift_hover': _card_shadow('lift_hover'),
            'shadow_lift_press': _card_shadow('lift_press'),
        }).encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), _css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    return _css_provider


def _style_as(widget, css_class):
    # HACK: add the provider to the screen only -- the widget's own
    # style context chains a private GtkStyleCascade, expensive at scale.
    widget.get_style_context().add_class(css_class)
    _get_css_provider()


def _use_pointer_cursor(widget):
    # No GdkWindow to set a cursor on until realized, so defer to
    # the 'realize' signal instead of setting it here.
    widget.connect('realize', _on_realize_set_pointer_cursor)


def _on_realize_set_pointer_cursor(widget):
    cursor = Gdk.Cursor.new_from_name(widget.get_display(), 'pointer')
    widget.get_window().set_cursor(cursor)


def _use_focus_ring(widget, css_class='grid-focus-round'):
    # -gtk-outline-radius rounds the outline like border-radius rounds a
    # border.
    _style_as(widget, css_class)
    widget.connect('state-flags-changed', _on_focus_ring_state_changed)
    widget.connect_after('draw', _draw_focus_ring)


def _on_focus_ring_state_changed(widget, previous_flags):
    widget.queue_draw()


def _draw_focus_ring(widget, cr):
    if not bool(widget.get_state_flags() & Gtk.StateFlags.FOCUSED):
        return False
    allocation = widget.get_allocation()
    Gtk.render_focus(widget.get_style_context(), cr, 0, 0,
                     allocation.width, allocation.height)
    return False


def _use_hover_state(widget):
    # Gtk.EventBox never sets PRELIGHT/ACTIVE itself like Gtk.Button.
    widget.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                      Gdk.EventMask.LEAVE_NOTIFY_MASK)
    widget.connect('enter-notify-event', _on_hover_enter)
    widget.connect('leave-notify-event', _on_hover_leave)
    widget.connect('button-press-event', _on_hover_press)
    widget.connect('button-release-event', _on_hover_release)


def _on_hover_enter(widget, event):
    widget.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
    return False


def _on_hover_leave(widget, event):
    widget.unset_state_flags(Gtk.StateFlags.PRELIGHT |
                             Gtk.StateFlags.ACTIVE)
    return False


def _on_hover_press(widget, event):
    widget.set_state_flags(Gtk.StateFlags.ACTIVE, False)
    return False


def _on_hover_release(widget, event):
    widget.unset_state_flags(Gtk.StateFlags.ACTIVE)
    return False


def _use_focus_stop(widget):
    # Gtk.Container's default focus handling never makes the container
    # itself a Tab stop.
    widget.connect('focus', _focus_forward_claim_cb)
    widget.connect_after('focus', _focus_backward_claim_cb)


def _focus_forward_claim_cb(widget, direction):
    if direction != Gtk.DirectionType.TAB_FORWARD:
        return False
    if widget.is_focus() or widget.get_focus_child() is not None:
        return False
    widget.grab_focus()
    return True


def _focus_backward_claim_cb(widget, direction):
    if direction != Gtk.DirectionType.TAB_BACKWARD:
        return False
    if widget.is_focus():
        return False
    widget.grab_focus()
    return True


def _animations_enabled():
    # HACK: with animations off, Gtk.Revealer's set_reveal_child leaves
    # get_child_revealed() already true in the same iteration.
    settings = Gtk.Settings.get_default()
    return settings is None or settings.props.gtk_enable_animations


def _decode_preview(preview_data):
    if not preview_data or len(preview_data) <= 4:
        return None
    if preview_data[1:4] != b'PNG':
        try:
            preview_data = base64.b64decode(preview_data)
        except (ValueError, TypeError):
            return None
    loader = GdkPixbuf.PixbufLoader()
    try:
        loader.write(preview_data)
        loader.close()
    except GLib.Error:
        return None
    pixbuf = loader.get_pixbuf()
    if pixbuf is None or pixbuf.get_width() == 0 or pixbuf.get_height() == 0:
        return None
    return pixbuf


def _flatten_to_white(pixbuf):
    width, height = pixbuf.get_width(), pixbuf.get_height()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    cr.set_source_rgb(*style.COLOR_WHITE.get_rgba()[:3])
    cr.paint()
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
    cr.paint()
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)


def _cover_pixbuf(pixbuf, width, height):
    source_width, source_height = pixbuf.get_width(), pixbuf.get_height()
    scale = max(width * 1.0 / source_width, height * 1.0 / source_height)
    if scale != 1.0:
        source_width = max(width, int(math.ceil(source_width * scale)))
        source_height = max(height, int(math.ceil(source_height * scale)))
        pixbuf = pixbuf.scale_simple(source_width, source_height,
                                     GdkPixbuf.InterpType.BILINEAR)
    return pixbuf.new_subpixbuf((source_width - width) // 2,
                                (source_height - height) // 2,
                                width, height)


def _card_render_key(metadata, tray_position, caption_field):
    return (metadata.get('uid'),
            metadata.get('title'),
            metadata.get('timestamp'),
            metadata.get('creation_time'),
            metadata.get('filesize'),
            metadata.get('icon-color'),
            metadata.get('activity'),
            metadata.get('bundle_id'),
            metadata.get('mime_type'),
            metadata.get('preview'),
            tray_position,
            caption_field)


def _entry_date(metadata, field):
    # sugar-datastore backfills creation_time = timestamp on create and
    # update (carquinyol/datastore.py).
    timestamp = timeline.safe_timestamp(metadata.get('timestamp', 0))
    if field != 'creation_time':
        return timestamp
    return timeline.safe_timestamp(metadata.get('creation_time', timestamp),
                                   default=timestamp)


def _caption_field(order_by):
    # Mirrors ListView.update_with_query's sort column (listview.py).
    if not timeline.is_date_sort(order_by):
        return 'filesize'
    return timeline.sort_field(order_by)


def _entry_filesize(metadata):
    # util.format_size has no guard past its own `if not size` --
    # '%d' % a nan or inf raises.
    try:
        size = float(metadata.get('filesize'))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(size):
        return None
    return int(size)


def _format_card_meta(metadata, caption_field):
    if caption_field == 'filesize':
        return util.format_size(_entry_filesize(metadata))
    return _format_clock_time(_entry_date(metadata, caption_field))


def _group_into_bands(entries, field):
    def key(metadata):
        return timeline.band_kind(_entry_date(metadata, field))
    return [(kind, list(group))
            for kind, group in itertools.groupby(entries, key)]


def _datable(entries, field):
    return [metadata for metadata in entries
            if metadata.get('activity', '') and _entry_date(metadata, field)]


def _split_into_sittings(entries, field):
    def key(metadata):
        moment = _entry_date(metadata, field)
        return (time.localtime(moment)[:3], timeline.band_kind(moment),
                misc.get_sitting_key(metadata))
    return [list(group) for _run, group in itertools.groupby(entries, key)]


def _group_sittings(entries, field):
    trays_by_uid = {}
    trayed_uids = set()
    for sitting in _split_into_sittings(_datable(entries, field), field):
        if len(sitting) >= 2:
            trays_by_uid[sitting[0]['uid']] = sitting
            trayed_uids.update(metadata['uid'] for metadata in sitting)

    loose_uids = {metadata['uid'] for metadata in entries
                  if metadata['uid'] not in trayed_uids}
    return trays_by_uid, loose_uids


def _format_clock_time(timestamp):
    if not timestamp:
        return ''
    when = time.localtime(timestamp)
    # An empty %p means the locale has no 12-hour clock.
    if not time.strftime('%p', when):
        return time.strftime('%H:%M', when)
    # %-I is a glibc extension.
    return time.strftime('%I:%M %p', when).lstrip('0')


class _Tween:
    """Cubic ease-out tween shared by the fold, sheet-nudge, and chevron
    turn animations. `on_tick(done)` runs after each frame's .value
    update so the owner can queue its own redraw or relayout."""

    def __init__(self, on_tick):
        self._on_tick = on_tick
        self.value = 0.0
        self.target = 0.0
        self._start_value = 0.0
        self._start_time = 0
        self._duration_us = 0
        self._widget = None
        self._anim_id = None

    @property
    def running(self):
        return self._anim_id is not None

    def snap(self, value):
        self.cancel()
        self.value = value
        self.target = value

    def start(self, widget, target, duration_us):
        # Retargets an in-flight tween from its current position, matching
        # how Gtk.Revealer handles an interrupted transition.
        self.target = target
        self._start_value = self.value
        self._start_time = GLib.get_monotonic_time()
        self._duration_us = duration_us
        self._widget = widget
        if self._anim_id is None:
            self._anim_id = widget.add_tick_callback(self.__tick_cb)

    def cancel(self):
        if self._anim_id is None:
            return
        self._widget.remove_tick_callback(self._anim_id)
        self._anim_id = None

    def __tick_cb(self, widget, frame_clock):
        elapsed = GLib.get_monotonic_time() - self._start_time
        fraction = min(1.0, elapsed / float(self._duration_us))
        # Cubic ease-out, matching Gtk.Revealer's own slide.
        eased = 1 - (1 - fraction) ** 3
        self.value = (self._start_value +
                      (self.target - self._start_value) * eased)
        done = fraction >= 1.0
        if done:
            self.value = self.target
            self._anim_id = None
        self._on_tick(done)
        return GLib.SOURCE_REMOVE if done else GLib.SOURCE_CONTINUE


class _Glyph(Gtk.DrawingArea):

    def __init__(self, kind, size):
        Gtk.DrawingArea.__init__(self)
        self._kind = kind
        self._size = size
        self.set_size_request(size, size)
        self.connect('draw', self.__draw_cb)

    def __draw_cb(self, widget, cr):
        timeline.draw_swatch(cr, self._kind, self._size)
        return False


class _CardArt(Gtk.DrawingArea):
    """DrawingArea has its own GdkWindow."""

    def __init__(self, pixbuf, lifted=False, sheets=0, hidden_count=0):
        Gtk.DrawingArea.__init__(self)
        self._pixbuf = pixbuf
        self._lifted = lifted
        _style_as(self, 'grid-card')
        if lifted:
            self.get_style_context().add_class('lifted')
        self._sheets = sheets
        self._hidden_count = hidden_count
        self._fold_tween = _Tween(self.__fold_tick)
        self._fold_tween.value = 1.0 if sheets else 0.0
        self._drawn_sheets = sheets
        self._drawn_hidden_count = hidden_count
        self._hover = False
        self._pressed = False
        self._focused = False
        self._selected = False
        self._sheet_nudge_tween = _Tween(self.__sheet_nudge_tick)
        self._update_request()
        self.connect('draw', self.__draw_cb)

    def get_flow_width(self):
        # get_preferred_width() answers (0, 0) before show_all() and 340
        # not 328 after (gap = 2 * _SHADOW_MARGIN).
        width = _CARD_WIDTH
        if self._sheets:
            width += _STACK_PEEK_X * self._sheets + _SHEET_HOVER_NUDGE
        return width

    def _drawn_width(self):
        if not self._drawn_sheets:
            return _CARD_WIDTH
        reserve = _STACK_PEEK_X * self._drawn_sheets + _SHEET_HOVER_NUDGE
        return _CARD_WIDTH + int(round(reserve * self._fold_tween.value))

    def _update_request(self):
        height = _PREVIEW_HEIGHT + 2 * _CARD_PADDING + 2 * _SHADOW_MARGIN
        width = self._drawn_width() + 2 * _SHADOW_MARGIN
        self.set_size_request(width, height)

    def set_sheets(self, sheets, hidden_count=0, animate=False):
        target = 1.0 if sheets else 0.0
        settled = (self._fold_tween.value == target and
                   not self._fold_tween.running)
        if (sheets == self._sheets and hidden_count == self._hidden_count and
                settled):
            return
        self._sheets = sheets
        self._hidden_count = hidden_count
        if sheets:
            self._sheet_nudge_tween.snap(0.0)
        if animate and _animations_enabled():
            if sheets:
                self._drawn_sheets = sheets
                self._drawn_hidden_count = hidden_count
            duration_ms = (_TRAY_CLOSE_DURATION_MS if target
                           else _TRAY_OPEN_DURATION_MS)
            self._fold_tween.start(self, target, duration_ms * 1000)
        else:
            self._fold_tween.snap(target)
            self._drawn_sheets = sheets
            self._drawn_hidden_count = hidden_count
        self._update_request()
        self.queue_draw()

    def __fold_tick(self, done):
        if done:
            self._drawn_sheets = self._sheets
            self._drawn_hidden_count = self._hidden_count
        self._update_request()
        self.queue_draw()

    def set_sheet_hover(self, hovered):
        target = _SHEET_HOVER_NUDGE if hovered else 0.0
        if target == self._sheet_nudge_tween.target:
            return

        # gtk-enable-animations off means jump straight to target.
        if not _animations_enabled():
            self._sheet_nudge_tween.snap(target)
            self.queue_draw()
            return

        self._sheet_nudge_tween.start(self, target, _SHEET_NUDGE_DURATION_US)

    def __sheet_nudge_tick(self, done):
        self.queue_draw()

    def set_hover(self, hover):
        if hover == self._hover:
            return
        self._hover = hover
        if hover:
            self.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        else:
            self.unset_state_flags(Gtk.StateFlags.PRELIGHT)

    def set_pressed(self, pressed):
        if pressed == self._pressed:
            return
        self._pressed = pressed
        if pressed:
            self.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        else:
            self.unset_state_flags(Gtk.StateFlags.ACTIVE)

    def set_focused(self, focused):
        if focused == self._focused:
            return
        self._focused = focused
        if focused:
            self.set_state_flags(Gtk.StateFlags.FOCUSED, False)
        else:
            self.unset_state_flags(Gtk.StateFlags.FOCUSED)

    def set_selected(self, selected):
        if selected == self._selected:
            return
        self._selected = selected
        context = self.get_style_context()
        if selected:
            context.add_class('selected')
        else:
            context.remove_class('selected')
        self.queue_draw()

    def _shadow(self, cr, x, y, w, h, strength):
        # cairo has no native blur; approximate with seven expanding,
        # fading rects.
        for step in range(7):
            grow = (7 - step) * 1.5
            cr.set_source_rgba(*_SHADOW_RGB01, .006 * strength)
            timeline.rounded_rect_path(
                cr, x - grow / 2., y - grow / 2., w + grow, h + grow,
                _CARD_RADIUS + grow / 2.)
            cr.fill()

    def __draw_cb(self, widget, cr):
        cr.set_antialias(cairo.ANTIALIAS_BEST)
        height = _PREVIEW_HEIGHT + 2 * _CARD_PADDING

        cr.save()
        cr.translate(_SHADOW_MARGIN, _SHADOW_MARGIN)

        phase = self._fold_tween.value
        for depth in range(self._drawn_sheets, 0, -1):
            dx = (_STACK_PEEK_X * depth +
                  self._sheet_nudge_tween.value) * phase
            inset = _STACK_PEEK_Y * depth
            self._shadow(cr, dx, inset, _CARD_WIDTH, height - 2 * inset,
                         1.1 * phase)
            timeline.rounded_rect_path(
                cr, dx, inset, _CARD_WIDTH, height - 2 * inset,
                _CARD_RADIUS)
            red, green, blue = timeline.hex_to_rgb01(timeline.FOLD_TINT)
            cr.set_source_rgba(red, green, blue, phase)
            cr.fill_preserve()
            cr.set_source_rgba(*_SHADOW_RGB01, 0.55 * phase)
            cr.set_line_width(style.zoom(1))
            cr.stroke()

        # cairo has no blur but the CSS engine does.
        Gtk.render_background(widget.get_style_context(), cr, 0, 0,
                              _CARD_WIDTH, height)

        cr.save()
        cr.translate(_CARD_PADDING, _CARD_PADDING)
        timeline.rounded_rect_path(cr, 0, 0, _PREVIEW_WIDTH, _PREVIEW_HEIGHT,
                                   _PREVIEW_RADIUS)
        cr.clip()
        if self._pixbuf is not None:
            Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
            cr.paint()
        cr.restore()

        if self._drawn_hidden_count > 0:
            text = '+%d' % self._drawn_hidden_count
            cr.select_font_face('sans-serif', cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(style.zoom(13))
            extents = cr.text_extents(text)
            chip_width = extents.width + 2 * _STACK_CHIP_PAD_X
            right = _CARD_PADDING + _PREVIEW_WIDTH - _STACK_CHIP_INSET
            bottom = _CARD_PADDING + _PREVIEW_HEIGHT - _STACK_CHIP_INSET
            left = right - chip_width
            top = bottom - _STACK_CHIP_HEIGHT
            cr.set_source_rgba(*style.COLOR_BLACK.get_rgba()[:3], 0.55 * phase)
            timeline.rounded_rect_path(
                cr, left, top, chip_width, _STACK_CHIP_HEIGHT,
                _STACK_CHIP_HEIGHT / 2.)
            cr.fill()
            cr.set_source_rgba(*style.COLOR_WHITE.get_rgba()[:3], phase)
            cr.move_to(left + _STACK_CHIP_PAD_X - extents.x_bearing,
                       top + (_STACK_CHIP_HEIGHT - extents.height) / 2. -
                       extents.y_bearing)
            cr.show_text(text)

        Gtk.render_focus(widget.get_style_context(), cr, 0, 0,
                         _CARD_WIDTH, height)
        cr.restore()
        return False


class _SelectGlyph(Gtk.DrawingArea):

    _BOX_SIZE = style.zoom(22)

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self._revealed = False
        self.set_size_request(_TOUCH_TARGET, _TOUCH_TARGET)
        self.connect('draw', self.__draw_cb)

    def set_checked(self, checked):
        if checked == self.get_checked():
            return
        if checked:
            self.set_state_flags(Gtk.StateFlags.CHECKED, False)
        else:
            self.unset_state_flags(Gtk.StateFlags.CHECKED)
        self.queue_draw()

    def get_checked(self):
        return bool(self.get_state_flags() & Gtk.StateFlags.CHECKED)

    def set_reveal(self, reveal):
        if reveal == self._revealed:
            return
        self._revealed = reveal
        self.queue_draw()

    def __draw_cb(self, widget, cr):
        if not (self._revealed or self.get_checked()):
            return False
        context = widget.get_style_context()
        _get_css_provider()
        offset = (_TOUCH_TARGET - self._BOX_SIZE) / 2.
        Gtk.render_background(context, cr, offset, offset,
                              self._BOX_SIZE, self._BOX_SIZE)
        Gtk.render_check(context, cr, offset, offset,
                         self._BOX_SIZE, self._BOX_SIZE)
        return False


# Not settable from inside the class body: the type has to exist first.
if hasattr(_SelectGlyph, 'set_css_name'):
    _SelectGlyph.set_css_name('check')


class _Card(Gtk.EventBox):

    __gsignals__ = {
        'activated': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'favorite-toggled': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'resume-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'selection-toggled': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, metadata, tray_position=None, sheets=0,
                 hidden_count=0, selected=False, selection_active=False,
                 caption_field='timestamp'):
        Gtk.EventBox.__init__(self)
        self.uid = metadata['uid']
        self.metadata = metadata
        self.render_key = _card_render_key(metadata, tray_position,
                                           caption_field)
        self.set_visible_window(False)
        self.set_can_focus(True)
        self.connect('button-release-event', self.__button_release_event_cb)
        self.connect('key-press-event', self.__key_press_event_cb)
        self.connect('focus-in-event', self.__focus_in_event_cb)
        self.connect('focus-out-event', self.__focus_out_event_cb)
        _use_focus_stop(self)

        self._selected = selected
        self._selection_active = selection_active
        self._card_hovered = False
        self._select_focused = False

        self._xo_color = misc.get_icon_color(metadata)
        lifted = tray_position == 0

        wrapper = Gtk.VBox()
        self.add(wrapper)

        pixbuf = _decode_preview(metadata.get('preview', ''))
        if pixbuf is not None:
            pixbuf = _cover_pixbuf(_flatten_to_white(pixbuf),
                                   _PREVIEW_WIDTH, _PREVIEW_HEIGHT)

        # A windowless EventBox has no GdkWindow of its own to catch the click.
        hit_area = Gtk.EventBox()
        hit_area.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                            Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self._art = _CardArt(pixbuf, lifted=lifted, sheets=sheets,
                             hidden_count=hidden_count)
        hit_area.add(self._art)
        hit_area.connect('enter-notify-event',
                         self.__art_enter_notify_event_cb)
        hit_area.connect('leave-notify-event',
                         self.__art_leave_notify_event_cb)
        hit_area.connect('button-press-event', self.__art_press_cb)
        hit_area.connect('button-release-event', self.__art_release_cb)
        _use_pointer_cursor(hit_area)

        art_overlay = Gtk.Overlay()
        art_overlay.add(hit_area)

        self._sheet_toggle_handler_id = None
        self._sheet_hit = Gtk.EventBox()
        self._sheet_hit.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                                   Gdk.EventMask.LEAVE_NOTIFY_MASK |
                                   Gdk.EventMask.BUTTON_PRESS_MASK |
                                   Gdk.EventMask.BUTTON_RELEASE_MASK)
        self._sheet_hit.set_halign(Gtk.Align.END)
        self._sheet_hit.set_valign(Gtk.Align.FILL)
        self._sheet_hit.set_margin_end(_SHADOW_MARGIN)
        self._sheet_hit.set_margin_top(_SHADOW_MARGIN)
        self._sheet_hit.set_margin_bottom(_SHADOW_MARGIN)
        _style_as(self._sheet_hit, 'grid-sheet-hit')
        self._sheet_hit.connect('enter-notify-event',
                                self.__sheet_enter_notify_event_cb)
        self._sheet_hit.connect('leave-notify-event',
                                self.__sheet_leave_notify_event_cb)
        _use_pointer_cursor(self._sheet_hit)
        art_overlay.add_overlay(self._sheet_hit)
        self._update_sheet_hit(sheets)

        self._select_button = Gtk.Button()
        self._select_button.set_relief(Gtk.ReliefStyle.NONE)
        self._select_button.set_can_focus(True)
        _style_as(self._select_button, 'grid-select-button')
        self._select_glyph = _SelectGlyph()
        self._select_button.add(self._select_glyph)
        self._select_button.set_halign(Gtk.Align.START)
        self._select_button.set_valign(Gtk.Align.START)
        self._select_button.set_margin_start(_SHADOW_MARGIN + _CARD_PADDING)
        self._select_button.set_margin_top(_SHADOW_MARGIN + _CARD_PADDING)
        self._select_button.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                                       Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self._select_button.connect('clicked', self.__select_clicked_cb)
        self._select_button.connect('enter-notify-event',
                                    self.__select_enter_cb)
        self._select_button.connect('leave-notify-event',
                                    self.__select_leave_cb)
        self._select_button.connect('focus-in-event',
                                    self.__select_focus_in_cb)
        self._select_button.connect('focus-out-event',
                                    self.__select_focus_out_cb)
        _use_pointer_cursor(self._select_button)
        _use_focus_ring(self._select_button)
        art_overlay.add_overlay(self._select_button)
        self._select_glyph.set_checked(selected)

        wrapper.pack_start(art_overlay, False, False, 0)

        caption = Gtk.HBox(spacing=_CAPTION_INNER_GAP)
        caption.set_size_request(_CARD_WIDTH, _CAPTION_HEIGHT)
        caption.set_halign(Gtk.Align.START)
        caption.set_margin_top(_CARD_PADDING)
        caption.set_margin_start(_SHADOW_MARGIN)
        caption.set_margin_end(_SHADOW_MARGIN)
        wrapper.pack_start(caption, False, False, 0)

        self._resume_button = Gtk.Button()
        self._resume_button.set_relief(Gtk.ReliefStyle.NONE)
        self._resume_button.set_tooltip_text(_('Resume'))
        _style_as(self._resume_button, 'grid-resume-button')
        launch_icon = Icon(file=misc.get_icon_name(metadata),
                           xo_color=self._xo_color, pixel_size=_TOUCH_GLYPH)
        self._resume_button.add(launch_icon)
        self._resume_button.set_valign(Gtk.Align.CENTER)
        self._resume_button.connect('clicked', self.__resume_clicked_cb)
        _use_pointer_cursor(self._resume_button)
        _use_focus_ring(self._resume_button)
        caption.pack_start(self._resume_button, False, False, 0)

        text_box = Gtk.VBox()
        text_box.set_valign(Gtk.Align.CENTER)
        caption.pack_start(text_box, True, True, 0)

        title_text = metadata.get('title', '') or _('Untitled')
        meta_text = _format_card_meta(metadata, caption_field)

        title = Gtk.Label(label=title_text)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_alignment(0, 0.5)
        _style_as(title, 'grid-card-title')
        text_box.pack_start(title, False, False, 0)

        meta = Gtk.Label(label=meta_text)
        meta.set_ellipsize(Pango.EllipsizeMode.END)
        meta.set_alignment(0, 0.5)
        _style_as(meta, 'grid-card-subtitle')
        text_box.pack_start(meta, False, False, 0)

        self._favorite_button = Gtk.Button()
        self._favorite_button.set_relief(Gtk.ReliefStyle.NONE)
        _style_as(self._favorite_button, 'grid-star-button')
        self._favorite_icon = Icon(pixel_size=_TOUCH_GLYPH)
        self._favorite_button.add(self._favorite_icon)
        self._favorite_button.set_valign(Gtk.Align.CENTER)
        self._favorite_button.connect('clicked', self.__favorite_clicked_cb)
        _use_pointer_cursor(self._favorite_button)
        _use_focus_ring(self._favorite_button)
        caption.pack_start(self._favorite_button, False, False, 0)

        self.set_favorite(metadata.get('keep', 0) == '1')
        self.set_size_request(_CARD_WIDTH, -1)

        self._art.set_selected(selected)
        self._update_select_reveal()

    def get_flow_width(self):
        return self._art.get_flow_width()

    def set_sheets(self, sheets, hidden_count=0, animate=False):
        self._art.set_sheets(sheets, hidden_count, animate=animate)
        self._update_sheet_hit(sheets)

    def _update_sheet_hit(self, sheets):
        width = (_STACK_PEEK_X * sheets + _SHEET_HOVER_NUDGE
                 if sheets else 0)
        self._sheet_hit.set_size_request(width, -1)

    def set_favorite(self, active):
        self._favorite = active
        self._favorite_icon.props.icon_name = 'emblem-favorite'
        if active:
            fill = self._xo_color.get_fill_color()
            self._favorite_icon.props.fill_color = fill
            self._favorite_icon.props.stroke_color = fill
        else:
            self._favorite_icon.props.stroke_color = \
                style.COLOR_PANEL_GREY.get_svg()
            self._favorite_icon.props.fill_color = \
                style.COLOR_TRANSPARENT.get_svg()

    def __favorite_clicked_cb(self, button):
        self.emit('favorite-toggled')

    def __resume_clicked_cb(self, button):
        self.emit('resume-clicked')

    def set_selected(self, selected):
        if selected == self._selected:
            return
        self._selected = selected
        self._select_glyph.set_checked(selected)
        self._art.set_selected(selected)

    def set_selection_active(self, active):
        if active == self._selection_active:
            return
        self._selection_active = active
        self._update_select_reveal()

    def _update_select_reveal(self):
        self._select_glyph.set_reveal(
            self._card_hovered or self._selection_active or
            self._select_focused)

    def __select_clicked_cb(self, button):
        self.emit('selection-toggled')

    def __select_enter_cb(self, widget, event):
        self._card_hovered = True
        self._update_select_reveal()
        return False

    def __select_leave_cb(self, widget, event):
        self._card_hovered = False
        self._update_select_reveal()
        return False

    def __select_focus_in_cb(self, widget, event):
        self._select_focused = True
        self._update_select_reveal()
        return False

    def __select_focus_out_cb(self, widget, event):
        self._select_focused = False
        self._update_select_reveal()
        return False

    def __art_enter_notify_event_cb(self, widget, event):
        self._art.set_hover(True)
        self._card_hovered = True
        self._update_select_reveal()
        return False

    def __art_leave_notify_event_cb(self, widget, event):
        self._art.set_hover(False)
        self._art.set_pressed(False)
        self._card_hovered = False
        self._update_select_reveal()
        return False

    def __art_press_cb(self, widget, event):
        self._art.set_pressed(True)
        return False

    def __art_release_cb(self, widget, event):
        self._art.set_pressed(False)
        return False

    def __sheet_enter_notify_event_cb(self, widget, event):
        self._art.set_sheet_hover(True)
        return False

    def __sheet_leave_notify_event_cb(self, widget, event):
        self._art.set_sheet_hover(False)
        return False

    def connect_sheet_toggle(self, handler, *args):
        if self._sheet_toggle_handler_id is not None:
            self._sheet_hit.disconnect(self._sheet_toggle_handler_id)
        self._sheet_toggle_handler_id = self._sheet_hit.connect(
            'button-release-event', handler, *args)

    def __focus_in_event_cb(self, widget, event):
        self._art.set_focused(True)
        return False

    def __focus_out_event_cb(self, widget, event):
        self._art.set_focused(False)
        return False

    def __key_press_event_cb(self, widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            if self._selection_active:
                self.emit('selection-toggled')
            else:
                self.emit('activated')
            return True
        return False

    def __hits(self, hotspot, event):
        # windowless widgets have no GdkWindow of their own; event.x/y are
        # relative to the window of the ancestor that owns the event.
        toplevel = hotspot.get_toplevel()
        window = toplevel.get_window()
        if window is None:
            return False
        ok, origin_x, origin_y = window.get_origin()
        if not ok:
            return False
        # FIXME: this binding's translate_coordinates returns (x, y),
        # not the (ok, x, y) its introspected signature documents.
        offset = hotspot.translate_coordinates(toplevel, 0, 0)
        if offset is None:
            return False
        offset_x, offset_y = offset
        allocation = hotspot.get_allocation()
        x = event.x_root - origin_x - offset_x
        y = event.y_root - origin_y - offset_y
        return 0 <= x <= allocation.width and 0 <= y <= allocation.height

    def __button_release_event_cb(self, widget, event):
        # HACK: returning True here would swallow the resume button's own
        # 'clicked' signal in GTK's event handler chain.
        if self.__hits(self._favorite_button, event) or \
                self.__hits(self._resume_button, event) or \
                self.__hits(self._select_button, event):
            return False
        if self._selection_active:
            self.emit('selection-toggled')
        else:
            self.emit('activated')
        return True


class _DisclosureChevron(Gtk.DrawingArea):

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self._expanded = False
        self._turn_tween = _Tween(self.__turn_tick)
        self.set_size_request(_DISCLOSURE_SIZE, _DISCLOSURE_SIZE)
        self.connect('draw', self.__draw_cb)

    def set_expanded(self, expanded, animate=False):
        if expanded == self._expanded:
            return
        self._expanded = expanded
        target = 1.0 if expanded else 0.0
        if not animate or not _animations_enabled():
            self._turn_tween.snap(target)
            self.queue_draw()
            return
        duration_us = (_TRAY_OPEN_DURATION_MS if expanded
                       else _TRAY_CLOSE_DURATION_MS) * 1000
        self._turn_tween.start(self, target, duration_us)

    def __turn_tick(self, done):
        self.queue_draw()

    def __draw_cb(self, widget, cr):
        # Same pattern as toolbarbox.py and palettewindow.py.
        context = widget.get_style_context()
        context.add_class('grid-disclosure')
        _get_css_provider()
        # render_arrow measures from 0 = pointing up.
        angle = math.pi / 2 * (1 + self._turn_tween.value)
        Gtk.render_arrow(context, cr, angle, 0, 0, _DISCLOSURE_SIZE)
        return False


class GridView(BaseJournalView):
    __gtype_name__ = 'JournalGridView'

    def __init__(self, journalactivity):
        self._journalactivity = journalactivity
        self._scroll_position = 0.
        self._rows = []
        self._usable_width = _CARD_WIDTH
        self._expanded_trays = set()
        self._turning_trays = set()
        self._relayout_source_id = None
        self._refresh_idle_handler = None
        self._card_registry = {}
        self._reusable_cards = {}
        self._backup_selected = None

        BaseJournalView.__init__(self)

        self.connect('map', self.__map_cb)
        self.connect('unmap', self.__unmap_cb)
        self.connect('destroy', self.__destroy_cb)

        self._scrolled_window = Gtk.ScrolledWindow()
        # HACK: EXTERNAL not NEVER -- NEVER folds the child's full minimum
        # width into this widget's request, growing the toplevel on every fold.
        self._scrolled_window.set_policy(Gtk.PolicyType.EXTERNAL,
                                         Gtk.PolicyType.AUTOMATIC)
        # Overlay scrollbars auto-hide until hovered, unreachable on touch.
        self._scrolled_window.set_overlay_scrolling(False)
        self._scrolled_window.set_kinetic_scrolling(True)
        self.add(self._scrolled_window)
        self._scrolled_window.connect('size-allocate',
                                      self.__viewport_allocate_cb)
        # key-press-event bubbles up from any focused card (GTK3 walks the
        # parent chain) to here; TreeView/ListBox/IconView give paging
        # keys free.
        self._scrolled_window.connect('key-press-event',
                                      self.__paging_key_press_cb)
        self._scrolled_window.show()

        vscrollbar = self._scrolled_window.get_vscrollbar()
        if vscrollbar is not None:
            _style_as(vscrollbar, 'grid-scrollbar')

        # Background lives on an EventBox, not the VBox inside it: Gtk.Box has
        # no window of its own, so its CSS background wasn't painted
        # under the margin.
        self._page_bg = Gtk.EventBox()
        _style_as(self._page_bg, 'grid-page')

        self._page = Gtk.VBox()
        self._page.set_border_width(style.DEFAULT_SPACING * 2)
        self._page_bg.add(self._page)
        self._page.props.spacing = _BAND_GAP

        self._sections_box = Gtk.VBox()
        self._sections_box.props.spacing = _SECTION_GAP
        self._page.pack_start(self._sections_box, False, False, 0)

        self._scrolled_window.add_with_viewport(self._page_bg)
        self._scrolled_window.get_child().set_shadow_type(Gtk.ShadowType.NONE)
        self._page_bg.show_all()

        # step_increment/page_increment still govern keyboard/trough scrolling.
        vadjustment = self._scrolled_window.get_vadjustment()
        vadjustment.set_step_increment(_ROW_SCROLL_STEP)
        vadjustment.set_page_increment(_ROW_SCROLL_STEP * 3)

        self._suppress_rebuild_uid = None

        self._connect_model_signals()
        model.updated.connect(self.__model_updated_cb)

    def update_with_query(self, query_dict):
        logging.debug('GridView.update_with_query')
        if 'order_by' not in query_dict:
            query_dict['order_by'] = ['+timestamp']
        self._query = query_dict
        self.refresh(new_query=True)

    def refresh(self, new_query=False):
        if self._defer_refresh(new_query):
            return
        self._stop_progress_bar()
        self._model_ready = False
        self._refresh_idle_handler = GLib.idle_add(self._do_refresh, new_query)

    def _do_refresh(self, new_query=False):
        self._refresh_idle_handler = None
        if not new_query:
            self._scroll_position = \
                self._scrolled_window.get_vadjustment().get_value()

        self._reset_model(new_query)
        self._model.connect('ready', self.__model_ready_cb)
        self._model.setup()

    def __model_ready_cb(self, list_model):
        self._stop_progress_bar()
        self._model_ready = True

        if self._backup_selected is not None:
            list_model.restore_selection(self._backup_selected)
            self._backup_selected = None
            self.emit('selection-changed',
                      len(list_model.get_selected_items()))

        all_ids = list_model.get_all_ids()
        if not all_ids:
            if self._is_query_empty():
                self._show_message(_('Your Journal is empty'))
            else:
                self._show_message(_('No matching entries'),
                                   show_clear_query=True)
            return

        self._clear_message()
        rows = []
        for index in range(len(all_ids)):
            try:
                # Reads from the model's own result set, avoiding a
                # get_properties D-Bus round trip per entry.
                metadata = list_model.get_row_metadata(index)
            except Exception:
                logging.exception('grid view: could not read row %r', index)
                continue
            if metadata is None:
                continue
            rows.append(self._with_preview(metadata))

        self._rows = rows
        self._render_sections(rows)

        adjustment = self._scrolled_window.get_vadjustment()
        max_value = max(adjustment.get_lower(),
                        adjustment.get_upper() - adjustment.get_page_size())
        adjustment.set_value(min(self._scroll_position, max_value))

    def _with_preview(self, metadata):
        # HACK: scan can drop the preview key (model.py).
        if 'preview' in metadata or metadata.get('mountpoint', '/') == '/':
            return metadata
        try:
            return model.get(metadata['uid'])
        except Exception:
            logging.exception('grid view: could not re-read %r',
                              metadata['uid'])
            return metadata

    def _render_sections(self, rows):
        self._reusable_cards = self._card_registry
        self._card_registry = {}
        for card in self._reusable_cards.values():
            parent = card.get_parent()
            if parent is not None:
                parent.remove(card)
        for child in self._sections_box.get_children():
            self._sections_box.remove(child)

        if timeline.is_date_sort(self._query.get('order_by')):
            self._pack_timeline_page(rows)
        else:
            self._pack_flat_page(rows)

        for card in self._reusable_cards.values():
            card.destroy()
        self._reusable_cards = {}

        self._sections_box.show_all()

    def _pack_flat_page(self, rows):
        self._sections_box.pack_start(
            self._build_group_flow([self._build_card(metadata)
                                    for metadata in rows]),
            False, False, 0)

    def _pack_timeline_page(self, rows):
        now = time.time()
        field = timeline.sort_field(self._query.get('order_by'))

        days = {}
        for metadata in rows:
            moment = _entry_date(metadata, field)
            days.setdefault(
                time.localtime(moment)[:3] if moment else None,
                []).append(metadata)

        for day_ymd, day_entries in days.items():
            label = (_('Earlier') if day_ymd is None
                     else timeline.day_label(day_ymd, now))
            self._sections_box.pack_start(
                self._create_section(label, day_entries, field),
                False, False, 0)

    def _create_section(self, label_text, entries, field):
        section = Gtk.VBox()
        section.props.spacing = _DAY_TO_BAND_GAP

        title = Gtk.Label(label=label_text)
        title.set_alignment(0, 0.5)
        _style_as(title, 'grid-day-title')
        section.pack_start(title, False, False, 0)

        trays_by_uid, loose_uids = _group_sittings(entries, field)

        bands = Gtk.VBox()
        bands.props.spacing = _BAND_GAP
        glyphs = []
        for band_kind, band_entries in _group_into_bands(entries, field):
            band, glyph = self._build_band(
                band_kind, band_entries, loose_uids, trays_by_uid)
            if band is not None:
                bands.pack_start(band, False, False, 0)
                if glyph is not None:
                    glyphs.append(glyph)
        section.pack_start(bands, False, False, 0)

        if not glyphs:
            return section
        self._attach_spine(section, bands, glyphs)
        return section

    def _attach_spine(self, section, bands, glyphs):
        # connect_after('draw', ...) instead of Gtk.Overlay + DrawingArea: a
        # windowed DrawingArea eats clicks; pass_through needs a
        # windowless child.
        section.connect_after('draw', self.__draw_spine_cb, bands, glyphs)

    def __draw_spine_cb(self, widget, cr, bands, glyphs):
        # translate_coordinates returns (x, y) or None here, not the C
        # (ok, x, y) signature (PyGObject).
        centers = []
        for glyph in glyphs:
            translated = glyph.translate_coordinates(
                widget, 0, glyph.get_allocated_height() / 2.)
            if translated is None:
                return False
            centers.append(translated[1])
        if not centers:
            return False

        bottom_edge = bands.translate_coordinates(
            widget, 0, bands.get_allocated_height())
        if bottom_edge is None:
            return False
        bands_x, bottom = bottom_edge

        x = bands_x + timeline.spine_centre_in_slot(_BAND_GLYPH_SIZE)

        cr.set_antialias(cairo.ANTIALIAS_BEST)
        timeline.draw_spine(cr, x, centers[0], bottom, centers,
                            _BAND_GLYPH_SIZE)
        return False

    def _build_band(self, band_kind, band_entries, loose_uids,
                    trays_by_uid):
        spine_width = 0 if band_kind == 'earlier' else _SPINE_COLUMN_WIDTH
        band_usable_width = self._usable_width - spine_width
        items = []
        for metadata in band_entries:
            uid = metadata['uid']
            if uid in trays_by_uid:
                items.append(self._build_tray(trays_by_uid[uid],
                                              band_usable_width))
            elif uid in loose_uids:
                items.append(self._build_card(metadata))
        if not items:
            return None, None

        band = Gtk.VBox()
        band.props.spacing = _BAND_HEADER_GAP

        glyph = None
        content = self._build_group_flow(items, usable_width=band_usable_width)
        if band_kind != 'earlier':
            header = Gtk.HBox()
            glyph_slot = Gtk.Box()
            glyph_slot.set_size_request(_SPINE_COLUMN_WIDTH, -1)
            glyph = _Glyph(band_kind, _BAND_GLYPH_SIZE)
            glyph.set_halign(Gtk.Align.START)
            glyph.set_margin_start(
                timeline.glyph_left_in_slot(_BAND_GLYPH_SIZE))
            glyph.set_valign(Gtk.Align.CENTER)
            glyph_slot.pack_start(glyph, True, True, 0)
            header.pack_start(glyph_slot, False, False, 0)

            label = Gtk.Label(label=timeline.band_label(band_kind))
            label.set_alignment(0, 0.5)
            label.set_valign(Gtk.Align.CENTER)
            _style_as(label, 'grid-band-label')
            header.pack_start(label, False, False, 0)
            band.pack_start(header, False, False, 0)

            indent = Gtk.HBox()
            spine_gutter = Gtk.Box()
            spine_gutter.set_size_request(_SPINE_COLUMN_WIDTH, -1)
            indent.pack_start(spine_gutter, False, False, 0)
            indent.pack_start(content, False, False, 0)
            content = indent
        band.pack_start(content, False, False, 0)

        return band, glyph

    def _build_tray(self, group_entries, usable_width):
        ordered = list(group_entries)
        tray_key = ordered[0]['uid']
        count = len(ordered)
        hidden_count = count - 1

        tray = Gtk.VBox(spacing=_TRAY_HEADER_GAP)
        tray.is_tray_group = True

        label = Gtk.Label(label=ngettext(
            '%d entry', '%d entries', count) % count)
        label.set_alignment(0, 0.5)
        _style_as(label, 'grid-band-label')

        foldable = count >= _FOLD_MIN_CARDS
        if foldable:
            expanded = tray_key in self._expanded_trays

            chevron = _DisclosureChevron()
            chevron.set_valign(Gtk.Align.CENTER)
            chevron.set_expanded(expanded)
            label.set_valign(Gtk.Align.CENTER)
            header = Gtk.HBox(spacing=style.zoom(4))
            header.pack_start(chevron, False, False, 0)
            header.pack_start(label, False, False, 0)
            # Needs its own GdkWindow so hover/press background and
            # cursor land here.
            toggle = Gtk.EventBox()
            # EventBox defaults to halign FILL, stretching to the tray's
            # full width and overhanging the label; START hugs it back.
            toggle.set_halign(Gtk.Align.START)
            toggle.set_border_width(style.zoom(12))
            toggle.set_can_focus(True)
            _use_focus_stop(toggle)
            _use_focus_ring(toggle, 'grid-focus-rect')
            _style_as(toggle, 'grid-tray-header')
            _use_hover_state(toggle)
            _use_pointer_cursor(toggle)
            toggle.add(header)
            header_slot = Gtk.Box()
            header_slot.set_size_request(-1, _TRAY_HEADER_SLOT_HEIGHT)
            header_slot.set_halign(Gtk.Align.START)
            toggle.set_valign(Gtk.Align.CENTER)
            header_slot.pack_start(toggle, False, False, 0)
            tray.pack_start(header_slot, False, False, 0)

            newest = self._build_card(
                ordered[0], tray_position=0,
                sheets=0 if expanded else min(_STACK_DEPTH, hidden_count),
                hidden_count=0 if expanded else hidden_count)
            newest.set_halign(Gtk.Align.START)
            newest.set_valign(Gtk.Align.START)

            rest = [self._build_card(metadata, tray_position=i)
                    for i, metadata in enumerate(ordered[1:], start=1)]
            rest_usable_width = max(
                _CARD_WIDTH,
                usable_width - newest.get_flow_width() - _TRAY_CARD_GAP)
            slides = len(self._flow_rows(
                rest, _TRAY_CARD_GAP, rest_usable_width)) <= 1

            revealer = Gtk.Revealer()
            revealer.set_transition_duration(_TRAY_OPEN_DURATION_MS)
            if slides:
                # FIXME: Revealer's cross axis always reports full child
                # size, so a closed one still leaks newest's height.
                revealer.set_transition_type(_TRAY_REVEAL_TRANSITION)
                revealer.add(self._build_group_flow(
                    rest, gap=_TRAY_CARD_GAP,
                    usable_width=rest_usable_width))
                body = Gtk.HBox(spacing=_TRAY_CARD_GAP - 2 * _SHADOW_MARGIN)
                body.pack_start(newest, False, False, 0)
                body.pack_start(revealer, False, False, 0)
            else:
                revealer.set_transition_type(
                    Gtk.RevealerTransitionType.NONE)
                if expanded:
                    revealer.add(self._build_group_flow(
                        [newest] + rest, gap=_TRAY_CARD_GAP,
                        usable_width=usable_width))
                    body = revealer
                else:
                    body = Gtk.HBox(
                        spacing=_TRAY_CARD_GAP - 2 * _SHADOW_MARGIN)
                    body.pack_start(newest, False, False, 0)
                    body.pack_start(revealer, False, False, 0)
            revealer.set_reveal_child(expanded)
            if tray_key in self._turning_trays:
                self._turning_trays.discard(tray_key)
                chevron.set_expanded(not expanded)
                chevron.set_expanded(expanded, animate=True)

            toggle.connect('button-release-event', self.__tray_toggle_cb,
                           tray_key, revealer, newest, chevron, hidden_count,
                           slides)
            toggle.connect('key-press-event', self.__tray_toggle_key_cb,
                           tray_key, revealer, newest, chevron, hidden_count,
                           slides)
            newest.connect_sheet_toggle(self.__tray_toggle_cb,
                                        tray_key, revealer, newest, chevron,
                                        hidden_count, slides)

            def get_tray_flow_width(newest=newest, revealer=revealer,
                                    slides=slides):
                child = revealer.get_child()
                if not revealer.get_reveal_child() or child is None:
                    return newest.get_flow_width()
                if slides:
                    return (newest.get_flow_width() + _TRAY_CARD_GAP +
                            child.flow_width)
                return child.flow_width
            tray.get_flow_width = get_tray_flow_width
        else:
            header_slot = Gtk.Box()
            header_slot.set_size_request(-1, _TRAY_HEADER_SLOT_HEIGHT)
            header_slot.set_halign(Gtk.Align.START)
            label.set_valign(Gtk.Align.CENTER)
            header_slot.pack_start(label, False, False, 0)
            tray.pack_start(header_slot, False, False, 0)
            body = Gtk.HBox(spacing=_TRAY_CARD_GAP - 2 * _SHADOW_MARGIN)
            for i, metadata in enumerate(ordered):
                body.pack_start(
                    self._build_card(metadata, tray_position=i),
                    False, False, 0)
            width = count * _CARD_WIDTH + (count - 1) * _TRAY_CARD_GAP
            tray.get_flow_width = lambda width=width: width
        tray.pack_start(body, False, False, 0)

        return tray

    def __tray_toggle_cb(self, widget, event, tray_key, revealer, newest,
                         chevron, hidden_count, slides):
        expanded = not revealer.get_reveal_child()
        if expanded:
            self._expanded_trays.add(tray_key)
        else:
            self._expanded_trays.discard(tray_key)
        if not slides:
            # HACK: rebuild on a high-priority idle, ahead of GTK's resize
            # and redraw idles, so old and new layouts never both render.
            self._turning_trays.add(tray_key)
            self.__schedule_fold_relayout(None)
            return True
        # set_reveal_child reads transition-duration at call time, so it
        # must be set here per toggle rather than once at construction.
        duration = (_TRAY_OPEN_DURATION_MS if expanded
                    else _TRAY_CLOSE_DURATION_MS)
        revealer.set_transition_duration(duration)
        revealer.set_reveal_child(expanded)
        newest.set_sheets(0 if expanded else min(_STACK_DEPTH, hidden_count),
                          0 if expanded else hidden_count, animate=True)
        chevron.set_expanded(expanded, animate=True)
        self.__schedule_fold_relayout(
            duration + _TRAY_RELAYOUT_SETTLE_MS if _animations_enabled()
            else 0)
        return True

    def __schedule_fold_relayout(self, delay_ms):
        # delay_ms=None uses PRIORITY_HIGH_IDLE, ahead of GTK's resize idle.
        if self._relayout_source_id is not None:
            GLib.source_remove(self._relayout_source_id)
        if delay_ms is None:
            self._relayout_source_id = GLib.idle_add(
                self.__fold_relayout_cb, priority=GLib.PRIORITY_HIGH_IDLE)
        else:
            self._relayout_source_id = GLib.timeout_add(
                delay_ms, self.__fold_relayout_cb)

    def __fold_relayout_cb(self):
        self._relayout_source_id = None
        return self._relayout_preserving_scroll()

    def __tray_toggle_key_cb(self, widget, event, tray_key, revealer,
                             newest, chevron, hidden_count, slides):
        if event.keyval not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter,
                                Gdk.KEY_space):
            return False
        return self.__tray_toggle_cb(widget, event, tray_key, revealer,
                                     newest, chevron, hidden_count, slides)

    def _build_group_flow(self, widgets, gap=_CARD_GAP, usable_width=None):
        # Not Gtk.FlowBox: it fixes one children-per-line count for the
        # whole box, so a tray several cards wide can't get per-row packing.
        container = Gtk.VBox()
        container.set_halign(Gtk.Align.START)
        self._layout_group_flow(container, widgets, gap, usable_width)
        return container

    def _flow_rows(self, widgets, gap, usable_width=None):
        if usable_width is None:
            usable_width = self._usable_width
        rows = []
        row_items = None
        row_width = 0
        for widget in widgets:
            get_width = getattr(widget, 'get_flow_width', None)
            if get_width is None:
                logging.warning(
                    'grid view: flow item with no get_flow_width: %r',
                    widget)
                natural = _CARD_WIDTH
            else:
                natural = get_width()
            needed = natural if row_items is None else \
                row_width + gap + natural
            if row_items is None or \
                    needed + 2 * _SHADOW_MARGIN > usable_width:
                row_items = []
                rows.append([row_items, False, natural])
                row_width = natural
            else:
                row_width = needed
                rows[-1][2] = row_width
            row_items.append(widget)
            if getattr(widget, 'is_tray_group', False):
                rows[-1][1] = True
        return rows

    def _layout_group_flow(self, container, widgets, gap, usable_width=None):
        rows = self._flow_rows(widgets, gap, usable_width)

        previous_has_tray = False
        for index, (row_items, has_tray, _width) in enumerate(rows):
            if index > 0:
                spacer_height = (_SECTION_GAP if has_tray or previous_has_tray
                                 else gap)
                spacer = Gtk.Box()
                spacer.set_size_request(-1, spacer_height)
                container.pack_start(spacer, False, False, 0)
            row = Gtk.HBox(spacing=gap - 2 * _SHADOW_MARGIN)
            row.set_halign(Gtk.Align.START)
            for widget in row_items:
                if has_tray and not getattr(widget, 'is_tray_group', False):
                    widget = self._pad_for_tray_header(widget)
                widget.set_valign(Gtk.Align.START)
                row.pack_start(widget, False, False, 0)
            container.pack_start(row, False, False, 0)
            previous_has_tray = has_tray

        container.flow_width = max((w for _r, _t, w in rows), default=0)
        container.show_all()

    def _pad_for_tray_header(self, widget):
        padded = Gtk.VBox()
        spacer = Gtk.Box()
        spacer.set_size_request(-1, _TRAY_HEADER_SLOT_HEIGHT +
                                _TRAY_HEADER_GAP)
        padded.pack_start(spacer, False, False, 0)
        padded.pack_start(widget, False, False, 0)
        get_flow_width = getattr(widget, 'get_flow_width', None)
        if get_flow_width is not None:
            padded.get_flow_width = get_flow_width
        return padded

    def __paging_key_press_cb(self, widget, event):
        if event.keyval in (Gdk.KEY_Home, Gdk.KEY_KP_Home):
            self._focus_edge_card(first=True)
        elif event.keyval in (Gdk.KEY_End, Gdk.KEY_KP_End):
            self._focus_edge_card(first=False)
        elif event.keyval in (Gdk.KEY_Page_Up, Gdk.KEY_KP_Page_Up):
            self._focus_paged_card(forward=False)
        elif event.keyval in (Gdk.KEY_Page_Down, Gdk.KEY_KP_Page_Down):
            self._focus_paged_card(forward=True)
        else:
            return False
        return True

    def _visible_cards(self):
        # Gtk.Widget.get_mapped() distinguishes shown from hidden.
        return [card for card in self._card_registry.values()
                if card.get_mapped()]

    def _focus_edge_card(self, first):
        cards = self._visible_cards()
        if cards:
            (cards[0] if first else cards[-1]).grab_focus()

    def _card_top(self, card):
        translated = card.translate_coordinates(self._page_bg, 0, 0)
        return translated[1] if translated is not None else None

    def _focus_paged_card(self, forward):
        cards = self._visible_cards()
        if not cards:
            return
        vadjustment = self._scrolled_window.get_vadjustment()
        page = vadjustment.get_page_size()
        upper = vadjustment.get_upper()
        target = vadjustment.get_value() + (page if forward else -page)
        target = max(0, min(target, max(0, upper - page)))

        current = self.get_toplevel().get_focus()
        while current is not None and not isinstance(current, _Card):
            current = current.get_parent()
        if current not in cards:
            current = None

        scored = sorted(
            (card for card in cards if self._card_top(card) is not None),
            key=lambda card: abs(self._card_top(card) - target))
        if not scored:
            return
        choice = scored[0]
        if choice is current:
            index = cards.index(current) + (1 if forward else -1)
            choice = cards[max(0, min(index, len(cards) - 1))]
        choice.grab_focus()

    def __viewport_allocate_cb(self, widget, allocation):
        usable = allocation.width - 2 * style.DEFAULT_SPACING * 2
        if usable == self._usable_width:
            return
        self._usable_width = usable
        # GTK swallows a resize queued from within an in-progress
        # size-allocate pass, so defer to an idle callback instead.
        GLib.idle_add(self._relayout_preserving_scroll)

    def _relayout_preserving_scroll(self):
        adjustment = self._scrolled_window.get_vadjustment()
        position = adjustment.get_value()
        self._render_sections(self._rows)
        max_value = max(adjustment.get_lower(),
                        adjustment.get_upper() - adjustment.get_page_size())
        adjustment.set_value(min(position, max_value))
        return False

    def _build_card(self, metadata, tray_position=None, sheets=0,
                    hidden_count=0):
        uid = metadata['uid']
        selection_active = bool(self._model.get_selected_items())
        selected = self._model.is_selected(uid)
        caption_field = _caption_field(self._query.get('order_by'))
        card = self._reusable_cards.pop(uid, None)
        if card is not None and card.render_key == _card_render_key(
                metadata, tray_position, caption_field):
            card.metadata = metadata
            card.set_sheets(sheets, hidden_count)
            card.set_favorite(metadata.get('keep', 0) == '1')
            card.set_selected(selected)
            card.set_selection_active(selection_active)
        else:
            if card is not None:
                card.destroy()
            card = _Card(metadata, tray_position=tray_position, sheets=sheets,
                         hidden_count=hidden_count, selected=selected,
                         selection_active=selection_active,
                         caption_field=caption_field)
            card.connect('activated', self.__card_activated_cb)
            card.connect('favorite-toggled', self.__card_favorite_cb)
            card.connect('resume-clicked', self.__card_resume_cb)
            card.connect('selection-toggled',
                         self.__card_selection_toggled_cb)
        self._card_registry[uid] = card
        return card

    def __card_activated_cb(self, card):
        try:
            metadata = model.get(card.metadata['uid'])
        except Exception:
            logging.exception('grid view: could not re-read %r',
                              card.metadata['uid'])
            return
        if metadata.get('activity') == misc.PROJECT_BUNDLE_ID:
            self._journalactivity.project_view_activated_cb(self, metadata)
        else:
            self._journalactivity.show_object(card.metadata['uid'])

    def __card_resume_cb(self, card):
        misc.resume(card.metadata,
                    alert_window=journalwindow.get_journal_window())

    def __card_favorite_cb(self, card):
        try:
            metadata = model.get(card.metadata['uid'])
        except Exception:
            logging.exception('grid view: could not re-read %r',
                              card.metadata['uid'])
            return
        if not model.is_editable(metadata):
            return
        active = metadata.get('keep', 0) != '1'
        metadata['keep'] = '1' if active else '0'
        if not self._query.get('keep'):
            self._suppress_rebuild_uid = metadata['uid']
        model.write(metadata, update_mtime=False)
        card.set_favorite(active)

    def __card_selection_toggled_cb(self, card):
        self._toggle_selection(card.metadata['uid'])

    def _toggle_selection(self, uid):
        self._model.set_selected(uid, not self._model.is_selected(uid))
        self.refresh_selection_rendering()
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def refresh_selection_rendering(self):
        if self._model is None:
            return
        selection_active = bool(self._model.get_selected_items())
        for uid, card in self._card_registry.items():
            card.set_selected(self._model.is_selected(uid))
            card.set_selection_active(selection_active)

    def select_all(self):
        if self._model is None:
            return
        BaseJournalView.select_all(self)

    def select_none(self):
        if self._model is None:
            return
        BaseJournalView.select_none(self)

    def _repaint_selection(self):
        self.refresh_selection_rendering()

    def is_dragging(self):
        # duck-typed against listview.py so callers don't need to
        # distinguish the grid from the list view.
        return False

    def __model_updated_cb(self, sender, signal, object_id):
        if object_id == self._suppress_rebuild_uid:
            self._suppress_rebuild_uid = None
            return
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def __destroy_cb(self, widget):
        # GLib.source_remove: a timeout source outlives its widget
        # unless cancelled.
        if self._relayout_source_id is not None:
            GLib.source_remove(self._relayout_source_id)
            self._relayout_source_id = None
        if self._refresh_idle_handler is not None:
            GLib.source_remove(self._refresh_idle_handler)
            self._refresh_idle_handler = None
        if self._model is not None:
            self._model.stop()

    def __map_cb(self, widget):
        vadjustment = self._scrolled_window.get_vadjustment()
        vadjustment.set_value(self._scroll_position)
        vadjustment.value_changed()
        self.set_is_visible(True)

    def __unmap_cb(self, widget):
        self._scroll_position = \
            self._scrolled_window.get_vadjustment().get_value()
        self.set_is_visible(False)
