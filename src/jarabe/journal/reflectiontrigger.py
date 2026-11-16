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

import logging
from gettext import gettext as _

import cairo
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from sugar3 import profile
from sugar3.datastore import datastore
from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon
from sugar3.graphics.objectchooser import get_preview_pixbuf

from jarabe.journal import misc
from jarabe.journal import reflectstyle
from jarabe.journal import timeline
from jarabe.model import shell
from jarabe.model.session import get_session_manager

NOTE_TIMEOUT = 15

# Below this, a close is a peek or mislaunch, not real work.
MIN_ACTIVE_SECONDS = 60

# Everything the note and its gate read. earned_invite answers False
# for any entry the datastore reply leaves these keys out of, so the
# gate's keys must stay requested here.
FIND_PROPERTIES = ['uid', 'activity', 'preview', 'icon-color',
                   'filesize', 'spent-times']


def earned_invite(metadata):
    """Whether this session's work has earned the note.

    Reads 'spent-times' ('%d' joined by ', '; last value is this
    session) and 'filesize'; any missing or malformed value keeps
    the note away.
    """
    try:
        if int(metadata.get('filesize')) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    last = str(metadata.get('spent-times') or '').split(',')[-1].strip()
    try:
        spent = int(last)
    except ValueError:
        return False
    return spent >= MIN_ACTIVE_SECONDS


_trigger = None

_NOTE_WIDTH = style.zoom(360)
_NOTE_MARGIN = style.zoom(24)
_CARD_RADIUS = style.zoom(12)
_THUMB_W = style.zoom(68)
_THUMB_H = style.zoom(52)

_invite_css_registered = False


def _register_invite_css():
    global _invite_css_registered
    if _invite_css_registered:
        return
    _invite_css_registered = True

    xo_color = profile.get_color()
    stroke = xo_color.get_stroke_color()
    r, g, b = (int(stroke.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    tint = '#%02X%02X%02X' % (r + (255 - r) * 9 // 10,
                              g + (255 - g) * 9 // 10,
                              b + (255 - b) * 9 // 10)

    px = reflectstyle.px

    css = ('''
.invite-title {
    font-family: %(font_round)s;
    font-weight: 700; font-size: %(z18)dpx; color: %(ink)s;
}
.invite-msg {
    font-family: %(font_round)s;
    font-weight: 500; font-size: %(z15)dpx; color: %(ink)s;
}
.invite-secondary {
    font-family: %(font_round)s;
    font-weight: 600; font-size: %(z16)dpx;
    color: %(ink)s; background-color: %(card)s;
    border: %(z2)dpx solid %(chip_line)s; border-radius: %(z22)dpx;
    padding: %(z10)dpx %(z16)dpx;
}
.invite-secondary:active { background-color: %(tint)s; }
.invite-primary {
    font-family: %(font_round)s;
    font-weight: 700; font-size: %(z16)dpx;
    color: %(ink)s; background-color: %(tint)s;
    border: %(z2)dpx solid %(stroke)s; border-radius: %(z22)dpx;
    padding: %(z10)dpx %(z16)dpx;
}
.invite-primary:active { background-color: %(card)s; }
''' % {
        'ink': reflectstyle.INK_PANEL,
        'chip_line': reflectstyle.CHIP_LINE,
        'card': reflectstyle.CARD,
        'stroke': stroke,
        'tint': tint,
        'font_round': reflectstyle.FONT_ROUND,
        'z2': px(2), 'z10': px(10), 'z15': px(15), 'z16': px(16),
        'z18': px(18), 'z22': px(22),
    }).encode('utf-8')

    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _set_source(cr, color):
    rgba = Gdk.RGBA()
    rgba.parse(color)
    Gdk.cairo_set_source_rgba(cr, rgba)


class _Thumb(Gtk.DrawingArea):
    """The entry's preview, clipped round, ringed in the child's stroke."""

    def __init__(self, pixbuf):
        Gtk.DrawingArea.__init__(self)
        self._pixbuf = pixbuf
        self._stroke = profile.get_color().get_stroke_color()
        self.set_size_request(_THUMB_W, _THUMB_H)
        self.connect('draw', self.__draw_cb)

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height
        radius = style.zoom(8)
        timeline.rounded_rect_path(cr, 0, 0, w, h, radius)
        cr.clip_preserve()
        scale = max(w / float(self._pixbuf.get_width()),
                    h / float(self._pixbuf.get_height()))
        cr.save()
        cr.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
        cr.get_source().set_filter(cairo.Filter.GOOD)
        cr.paint()
        cr.restore()
        _set_source(cr, self._stroke)
        cr.set_line_width(2.0)
        cr.stroke()
        return False


class _InviteNote(Gtk.Window):
    """Jo's invite note: a thumbnail, one question, two choices."""

    def __init__(self, metadata, response_cb):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self._response_cb = response_cb

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_app_paintable(True)
        self.set_keep_above(True)
        self.connect('realize', lambda w: self.set_type_hint(
            Gdk.WindowTypeHint.NOTIFICATION))
        self.connect('draw', self.__draw_cb)

        outer = Gtk.VBox()
        outer.set_border_width(style.zoom(18))
        self.add(outer)
        outer.set_spacing(style.zoom(12))

        head = Gtk.HBox()
        head.set_spacing(style.zoom(12))
        pixbuf = get_preview_pixbuf(metadata.get('preview', ''))
        if pixbuf is not None:
            head.pack_start(_Thumb(pixbuf), False, False, 0)
        else:
            icon = CanvasIcon(file_name=misc.get_icon_name(metadata),
                              pixel_size=style.zoom(52))
            icon.props.xo_color = misc.get_icon_color(metadata)
            head.pack_start(icon, False, False, 0)
        words = Gtk.VBox()
        words.set_valign(Gtk.Align.CENTER)
        words.set_spacing(style.zoom(2))
        title = Gtk.Label(label=_('Saved to your Journal'))
        title.get_style_context().add_class('invite-title')
        title.set_xalign(0)
        words.pack_start(title, False, False, 0)
        msg = Gtk.Label(label=_('Want to look back at it with Jo?'))
        msg.get_style_context().add_class('invite-msg')
        msg.set_xalign(0)
        msg.set_line_wrap(True)
        words.pack_start(msg, False, False, 0)
        head.pack_start(words, True, True, 0)
        outer.pack_start(head, False, False, 0)

        buttons = Gtk.HBox()
        buttons.set_spacing(style.zoom(10))
        later = Gtk.Button(label=_('Not now'))
        later.set_relief(Gtk.ReliefStyle.NONE)
        later.get_style_context().add_class('invite-secondary')
        later.connect('clicked', lambda b: self._response_cb(False))
        buttons.pack_start(later, True, True, 0)
        go = Gtk.Button(label=_('Open my Journal'))
        go.set_relief(Gtk.ReliefStyle.NONE)
        go.get_style_context().add_class('invite-primary')
        go.connect('clicked', lambda b: self._response_cb(True))
        buttons.pack_start(go, True, True, 0)
        outer.pack_start(buttons, False, False, 0)

        self.set_size_request(_NOTE_WIDTH, -1)
        outer.show_all()

    def place(self):
        screen = Gdk.Screen.get_default()
        width, height = self.get_size()
        self.move(screen.get_width() - width - _NOTE_MARGIN,
                  screen.get_height() - height - _NOTE_MARGIN)

    def __draw_cb(self, widget, cr):
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        # No compositor to round a toplevel for us: the window blends
        # into Home's white and the card is drawn inside it.
        _set_source(cr, reflectstyle.CARD)
        cr.paint()

        r = _CARD_RADIUS
        timeline.rounded_rect_path(cr, 1, 1, w - 2, h - 2, r)
        _set_source(cr, reflectstyle.MOUNT_LINE)
        cr.set_line_width(2.0)
        cr.stroke()

        stroke = profile.get_color().get_stroke_color()
        _set_source(cr, stroke)
        cr.move_to(1 + r, 2.5)
        cr.line_to(w - 1 - r, 2.5)
        cr.set_line_width(4.0)
        cr.stroke()
        return False


class ReflectionTrigger(object):
    """Invite the child to reflect when an activity closes.

    At most one note at a time, no countdown, and declining is a
    first-class button - only 'Open my Journal' opens the entry.
    """

    def __init__(self):
        self._note = None
        self._object_id = None
        self._timeout_id = None
        self._shutting_down = False

        model_ = shell.get_model()
        model_.connect('activity-removed', self.__activity_removed_cb)
        get_session_manager().shutdown_signal.connect(self.__shutdown_cb)

    def __shutdown_cb(self, event):
        self._shutting_down = True
        self.__dismiss()

    def __activity_removed_cb(self, model_, home_activity):
        if self._shutting_down or self._note is not None:
            return
        if home_activity.is_journal():
            return
        # Failed and timed-out launches are removed while still
        # LAUNCHING or LAUNCH_FAILED; only a real session gets asked.
        if home_activity.get_launch_status() != shell.Activity.LAUNCHED:
            return
        activity_id = home_activity.get_activity_id()
        if activity_id is None:
            return

        object_id, metadata = self._find_entry(activity_id)
        if object_id is None:
            return
        if not earned_invite(metadata):
            return
        self._show_note(object_id, metadata)

    def _find_entry(self, activity_id):
        """Return the Journal entry this activity session wrote, if any.
        """
        try:
            # the find() wrapper consumes 'uid' to build object_id, so
            # it must be requested even though it never reaches metadata
            results, count = datastore.find(
                {'activity_id': activity_id, 'limit': 1},
                sorting=['-mtime'],
                properties=FIND_PROPERTIES)
        except Exception:
            logging.exception('Reflection trigger datastore lookup failed')
            return None, None
        if not results:
            return None, None
        entry = results[0]
        object_id = entry.object_id
        metadata = entry.metadata
        # DSObject.destroy() leaves the entry's Updated signal match on
        # the bus, and the match pins the object through its callback;
        # clearing object_id runs the setter that removes the match.
        entry.object_id = None
        entry.destroy()
        return object_id, metadata

    def _show_note(self, object_id, metadata):
        _register_invite_css()
        note = _InviteNote(metadata, self.__note_response_cb)
        self._note = note
        self._object_id = object_id
        self._timeout_id = GLib.timeout_add_seconds(
            NOTE_TIMEOUT, self.__timeout_cb)
        note.show()
        note.place()

    def __dismiss(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        if self._note is not None:
            self._note.destroy()
            self._note = None

    def __timeout_cb(self):
        self._timeout_id = None
        self.__dismiss()
        return False

    def __note_response_cb(self, accepted):
        object_id = self._object_id
        self.__dismiss()
        if not accepted:
            return
        # bound at use, not at the top: journalactivity reaches
        # jarabe.config, which only exists in a built tree, and a
        # top-level import would leave this module unimportable by
        # the unit tests
        from jarabe.journal import journalactivity
        journal = journalactivity.get_journal()
        if journal.show_object(object_id, reveal_reflection=True):
            journal.reveal()


def start():
    global _trigger
    if _trigger is None:
        _trigger = ReflectionTrigger()
