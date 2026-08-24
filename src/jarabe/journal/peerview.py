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

"""A window onto a friend's shared Journal entry.

Everything shown here arrives over a one-to-one text channel with
the friend who shared it: the window asks them for the page and
draws whatever comes back. It never reads the datastore and never
writes to it, so it behaves the same whether the entry lives on the
laptop across the table or on this one.

The page is the Journal's own detail page, reused so a shared entry
looks the way it does on the owner's desk. The writing paths are
turned into dead ends and the parts that don't travel - the talk
with Jo, the moments, the star - are hidden. A visitor can leave one
question, which goes back to the owner and shows up in the entry's
comments.
"""

import base64
import json
import logging
import unicodedata
from functools import partial
from gettext import gettext as _

import dbus
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon
from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.xocolor import XoColor

from jarabe.journal import misc
from jarabe.journal import peershare
from jarabe.journal import reflectguard
from jarabe.journal import reflectstyle
from jarabe.journal.expandedentry import ExpandedEntry
from jarabe.model import neighborhood

_FETCH_SECONDS = 30
_DEFAULT_COLOR = '#FFFFFF,#000000'

_css_registered = False

_open_views = {}


def _ensure_css():
    global _css_registered
    if _css_registered:
        return
    _css_registered = True

    px = reflectstyle.px

    css = ("""
        .pv-page { background-color: %(paper)s; }
        .pv-title {
            font-family: %(font_hand)s;
            font-size: %(z28)dpx;
            color: %(paper)s;
        }
        .pv-owner {
            font-family: %(font_hand)s;
            font-size: %(z17)dpx;
            color: %(ink_soft)s;
        }
        .pv-status {
            font-family: %(font_hand)s;
            font-size: %(z18)dpx;
            color: %(ink_soft)s;
        }
        .pv-card {
            background-color: %(card)s;
            border-radius: %(z12)dpx;
            border: %(z1)dpx solid %(rim)s;
        }
        .pv-who {
            font-family: %(font_clear)s;
            font-size: %(z13)dpx;
            color: %(ink_soft)s;
        }
        .pv-said {
            font-family: %(font_clear)s;
            font-size: %(z17)dpx;
            color: %(ink)s;
        }
        .pv-lead {
            font-family: %(font_hand)s;
            font-size: %(z19)dpx;
            color: %(ink)s;
        }
        .pv-entry {
            font-family: %(font_clear)s;
            font-size: %(z17)dpx;
            color: %(ink)s;
            background-color: %(card)s;
            border: %(z1)dpx solid %(rim)s;
            border-radius: %(z999)dpx;
            padding: %(z8)dpx %(z16)dpx;
        }
        .pv-send {
            font-family: %(font_clear)s;
            font-size: %(z16)dpx;
            color: %(ink)s;
            background-color: %(card)s;
            border: %(z1)dpx solid %(rim)s;
            border-radius: %(z999)dpx;
            padding: %(z8)dpx %(z22)dpx;
        }
        .pv-send:active { background-color: %(ember)s; }
    """) % {
        'paper': reflectstyle.PAPER_PAGE,
        'card': reflectstyle.CARD,
        'rim': reflectstyle.RIM_PAGE,
        'ink': reflectstyle.INK_PAGE,
        'ink_soft': reflectstyle.INK_SOFT_PAGE,
        'ember': reflectstyle.EMBER,
        'font_hand': reflectstyle.FONT_HAND,
        'font_clear': reflectstyle.FONT_CLEAR,
        'z1': px(1), 'z8': px(8), 'z12': px(12),
        'z13': px(13), 'z16': px(16), 'z17': px(17), 'z18': px(18),
        'z19': px(19), 'z22': px(22), 'z28': px(28),
        'z999': px(999),
    }

    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode('utf-8'))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _class(widget, name):
    widget.get_style_context().add_class(name)
    return widget


def _preview_bytes(encoded):
    """Unwrap the base64 the preview arrived in.

    Only a PNG gets through. The toolkit's preview loader takes
    anything else for base64 text and decodes it outside its own
    try, so junk bytes from a peer would blow up halfway through
    drawing the page.
    """
    if not encoded:
        return None
    if not isinstance(encoded, str) or \
            len(encoded) > peershare.PAYLOAD_LIMIT:
        # A whole page fits under the limit already, so there is no
        # reason to spend the decode on something bigger.
        return None
    try:
        raw = base64.b64decode(encoded)
    except Exception:
        logging.exception('peerview: preview was not base64')
        return None
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        return None
    return raw


def _owner_nick(activity):
    owner = activity.get_owner()
    if owner is None:
        return ''
    return owner.get_nick() or ''


def _clean_text(text, multiline=False):
    """Take the control and direction-changing characters out of a
    peer's text before it reaches a label.

    The page draws whatever the wire hands it, and a title or comment
    carrying a direction override can rearrange the window around it.
    Newlines survive only in the fields meant to have them.
    """
    if not isinstance(text, str):
        return ''
    kept = []
    for ch in text:
        if multiline and ch == '\n':
            kept.append(ch)
        elif unicodedata.category(ch) not in ('Cc', 'Cf', 'Zl', 'Zp'):
            kept.append(ch)
    return ''.join(kept)


class _BorrowedPage(ExpandedEntry):
    """A read-only version of the owner's detail page.

    Everything the page can write goes through _write_entry and the
    editable checks, and both are stubbed out here. The layout is
    left alone: the parts that don't come over the wire - the talk
    with Jo, the moments, the star, the date - are just absent, and
    the visitor's question sits where the talk would have been.
    """

    def __init__(self, color):
        ExpandedEntry.__init__(self, None)
        self._reflection.hide()
        # The tape takes the owner's colour, same as on their page.
        self._mount.set_corner_color(color.get_stroke_color())

    def set_ask(self, widget):
        self._ask_widget = widget
        self._sidecol.pack_start(widget, False, False, 0)
        widget.show_all()

    def _refresh_sidecol(self, moments, editable):
        ExpandedEntry._refresh_sidecol(self, moments, editable)
        widget = getattr(self, '_ask_widget', None)
        if widget is not None:
            self._sidecol.pack_start(widget, False, False, 0)
            widget.show_all()

    def put_away(self):
        self._mount.set_corner_color(style.COLOR_INACTIVE_STROKE.get_html())

    def _none_kept(self):
        # Kept words aren't in the payload, so there is nothing to
        # say either way.
        return None

    def _entry_editable(self):
        return False

    def _write_entry(self):
        pass

    def set_rail_shown(self, shown):
        pass

    def _attach_reflection(self, metadata):
        pass

    def set_metadata(self, metadata):
        ExpandedEntry.set_metadata(self, metadata)
        # hide() on its own doesn't hold. The window runs show_all()
        # over itself once the page is packed, and that walks the
        # whole tree and shows every child again, including the two
        # we just hid, so they need no_show_all set as well.
        for widget in (self._keep_icon, self._date):
            widget.set_no_show_all(True)
            widget.hide()

    def _create_icon(self):
        icon = CanvasIcon(file_name=misc.get_icon_name(self._metadata))
        icon.props.xo_color = misc.get_icon_color(self._metadata)
        return icon

    def _create_technical(self):
        # Size and date come off the owner's disk.
        return Gtk.VBox()

    def _artwork_pixbuf(self):
        # Only the preview came over, so there is no file here to
        # load a pixbuf from.
        return None


class PeerEntryView(Gtk.Window):

    __gtype_name__ = 'SugarPeerEntryView'

    def __init__(self, activity):
        Gtk.Window.__init__(self)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)
        self.set_size_request(
            Gdk.Screen.width() - style.GRID_CELL_SIZE * 2,
            Gdk.Screen.height() - style.GRID_CELL_SIZE * 2)

        _ensure_css()

        self._activity = activity
        self._owner = _owner_nick(activity)
        owner = activity.get_owner()
        self._owner_key = owner.props.key if owner is not None else None
        self._uid = activity.entry_uid
        self._proxy = None
        self._match = None
        self._bus_name = None
        self._timeout_id = None
        self._answered = False
        self._asked = False
        self._closed = False
        self._ask_row = None

        self._page = None
        self._put_away_done = False
        model = neighborhood.get_model()
        self._gone_id = model.connect(
            'activity-removed', self.__activity_removed_cb)
        # activity-removed fires when the share itself ends. A friend
        # who drops off the network leaves the activity sitting in the
        # model, so watch the buddy as well.
        self._buddy_gone_id = model.connect(
            'buddy-removed', self.__buddy_removed_cb)

        self.set_title(_clean_text(activity.get_name() or ''))
        self.connect('key-press-event', self.__key_press_cb)
        self.connect('destroy', self.__destroy_cb)

        ground = _class(Gtk.EventBox(), 'pv-page')
        self.add(ground)
        page = Gtk.VBox()
        ground.add(page)
        page.pack_start(self.__build_header(), False, False, 0)
        page.pack_start(Gtk.HSeparator(), False, False, 0)

        strip = Gtk.VBox()
        strip.set_spacing(style.zoom(4))
        strip.set_margin_top(style.zoom(16))
        strip.set_margin_start(style.zoom(44))
        page.pack_start(strip, False, False, 0)

        owner_line = _class(Gtk.Label(), 'pv-owner')
        owner_line.set_xalign(0.0)
        if self._owner:
            # Isolate the nick so a right-to-left name can't reorder
            # the sentence around it.
            # TRANS: %s is the name of the friend the entry came from
            owner_line.set_label(_("From %s's Journal")
                                 % ('\u2068%s\u2069' % self._owner))
        else:
            owner_line.set_label(_('A shared Journal entry'))
        strip.pack_start(owner_line, False, False, 0)

        self._status = _class(
            Gtk.Label(label=_('Getting the page from your friend…')),
            'pv-status')
        self._status.set_xalign(0.0)
        strip.pack_start(self._status, False, False, 0)

        self._body = Gtk.VBox()
        page.pack_start(self._body, True, True, 0)

        self.show_all()
        self._open_line()

    def __build_header(self):
        bar = Gtk.Toolbar()
        bar.set_size_request(-1, style.GRID_CELL_SIZE)
        self._title = _class(
            Gtk.Label(label=_clean_text(self._activity.get_name() or '')),
            'pv-title')
        self._title.set_xalign(0.0)
        self._title.set_margin_start(style.zoom(24))
        self._title.set_ellipsize(Pango.EllipsizeMode.END)
        item = Gtk.ToolItem()
        item.set_expand(True)
        item.add(self._title)
        bar.insert(item, -1)
        close = ToolButton(icon_name='dialog-cancel')
        # TRANS: tooltip of the button that closes a friend's page
        close.set_tooltip(_('Close'))
        close.connect('clicked', lambda button: self.destroy())
        bar.insert(close, -1)
        return bar

    def _open_line(self):
        neighbors = neighborhood.get_model()
        conn = neighbors.get_link_local_connection()
        owner = self._activity.get_owner()
        if conn is None or owner is None or not self._uid:
            self._give_up()
            return
        self._bus_name = conn[peershare.CONNECTION].bus_name
        self._timeout_id = GLib.timeout_add_seconds(
            _FETCH_SECONDS, self.__fetch_timeout_cb)
        # The neighborhood already knows the friend by handle.
        handle = neighbors.get_link_local_handle(owner)
        if handle:
            self._request_channel(conn, handle)
            return
        contact_id = None if owner.is_owner() else owner.props.contact_id
        if not contact_id:
            self._give_up()
            return
        conn[peershare.CONNECTION].RequestHandles(
            peershare.HANDLE_TYPE_CONTACT, [contact_id],
            reply_handler=partial(self.__got_handle_cb, conn),
            error_handler=partial(self.__wire_error_cb, 'RequestHandles'))

    def __got_handle_cb(self, conn, handles):
        self._request_channel(conn, handles[0])

    def _request_channel(self, conn, handle):
        conn[peershare.CONNECTION].RequestChannel(
            peershare.CHANNEL_TYPE_TEXT, peershare.HANDLE_TYPE_CONTACT,
            handle, True,
            reply_handler=self.__got_channel_cb,
            error_handler=partial(self.__wire_error_cb, 'RequestChannel'))

    def __got_channel_cb(self, channel_path):
        # The reply can land after the child closed the window.
        if self._closed:
            return
        try:
            bus = dbus.SessionBus()
            self._proxy = bus.get_object(self._bus_name, channel_path)
        except Exception:
            logging.exception('peerview: could not open the line')
            self._give_up()
            return
        self._match = self._proxy.connect_to_signal(
            'Received', self.__received_cb,
            dbus_interface=peershare.CHANNEL_TYPE_TEXT)
        # An answer that beat the handler is in the pending queue.
        self._proxy.ListPendingMessages(
            False, dbus_interface=peershare.CHANNEL_TYPE_TEXT,
            reply_handler=self.__pending_cb,
            error_handler=partial(self.__log_error_cb,
                                  'ListPendingMessages'))
        self._send({'peershare': peershare.PROTOCOL,
                    'kind': peershare.KIND_FETCH, 'uid': self._uid},
                   partial(self.__wire_error_cb, 'Send'))

    def __pending_cb(self, messages):
        if self._closed:
            return
        for message in messages:
            self.__received_cb(*message)

    def _send(self, message, error_handler, reply_handler=None):
        if self._proxy is None:
            return
        self._proxy.Send(
            peershare.MESSAGE_TYPE_PROTOCOL, json.dumps(message),
            dbus_interface=peershare.CHANNEL_TYPE_TEXT,
            reply_handler=reply_handler or (lambda: None),
            error_handler=error_handler)

    def __received_cb(self, message_id, timestamp, sender, message_type,
                      flags, text):
        if self._closed:
            return
        message = peershare.parse_message(text)
        if message is None or message['kind'] != peershare.KIND_ENTRY:
            return
        if self._answered or message.get('uid') != self._uid:
            # Two pages open on the same friend share this line, so
            # each one takes only the entry it asked for.
            return
        self._answered = True
        self._acknowledge(message_id)
        self._cancel_timeout()
        self._show_entry(message)

    def _acknowledge(self, message_id):
        if self._proxy is None:
            return
        self._proxy.AcknowledgePendingMessages(
            [message_id], dbus_interface=peershare.CHANNEL_TYPE_TEXT,
            reply_handler=lambda: None,
            error_handler=partial(self.__log_error_cb,
                                  'AcknowledgePendingMessages'))

    def __fetch_timeout_cb(self):
        self._timeout_id = None
        self._give_up()
        return False

    def _cancel_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def _give_up(self):
        self._cancel_timeout()
        self._status.set_label(
            _('Your friend did not answer. You can look again later.'))
        self._status.show()

    def __wire_error_cb(self, call, error):
        logging.error('peerview: %s failed: %s', call, error)
        self._give_up()

    def __log_error_cb(self, call, error):
        logging.error('peerview: %s failed: %s', call, error)

    def _show_entry(self, payload):
        if self._put_away_done:
            # The owner pulled the entry while the page was still on
            # its way; don't wake it up now.
            return
        title = _clean_text(
            payload.get('title') or self._activity.get_name() or '')
        title = title or _('Untitled')
        self.set_title(title)
        self._title.set_label(title)
        self._color = self._payload_color(payload)
        self._status.hide()

        comments = payload.get('comments')
        if not isinstance(comments, list):
            comments = []
        # The cap is applied where the owner writes a comment, but a
        # hand-made reply can carry as many as it likes and each one
        # becomes a widget here.
        comments = [self._clean_comment(comment)
                    for comment in comments[:reflectguard.MAX_COMMENTS]
                    if isinstance(comment, dict)]

        bundle = self._activity.get_bundle()
        metadata = {
            'uid': peershare.safe_uid(self._uid),
            'title': title,
            'description': _clean_text(payload.get('description') or '',
                                       multiline=True),
            'tags': peershare.safe_tags(payload.get('tags')),
            'activity':
                bundle.get_bundle_id() if bundle is not None else '',
            'mime_type': peershare.safe_mime(self._activity.entry_mime),
            'icon-color': self._color.to_string(),
            'comments': json.dumps(comments),
        }
        preview = _preview_bytes(payload.get('preview'))
        if preview is not None:
            metadata['preview'] = preview

        borrowed = _BorrowedPage(self._color)
        borrowed.set_metadata(metadata)
        self._body.pack_start(borrowed, True, True, 0)
        self._body.show_all()
        borrowed.set_ask(self.__build_ask(comments))
        self._page = borrowed

    def __activity_removed_cb(self, model, activity):
        if activity.activity_id != self._activity.activity_id:
            return
        self._put_away()

    def __buddy_removed_cb(self, model, buddy):
        if self._owner_key is None or buddy.props.key != self._owner_key:
            return
        self._put_away()

    def _put_away(self):
        """Handle the share going away.

        The friend can unshare, close the activity or drop off the
        network, and all three land here. Whatever already arrived
        stays on screen, since the child may be in the middle of
        reading it, but the tape loses its colour, the ask box is
        taken out if it is still up, no further question can be sent
        and the status line says what happened. If the page never
        arrived there is nothing to grey out, so only the status line
        changes.
        """
        if self._put_away_done:
            return
        self._put_away_done = True
        self._cancel_timeout()
        if self._page is None:
            # TRANS: %s is the name of the friend who owns the entry
            self._status.set_label(_('%s put this away.') % self._owner
                                   if self._owner
                                   else _('This was put away.'))
            self._status.show()
            return
        self._page.put_away()
        if self._ask_row is not None:
            self._ask_column.remove(self._ask_row)
            self._ask_column.remove(self._ask_lead)
            self._ask_row = None
        self._asked = True
        self._ask_status.set_label(
            # TRANS: %s is the name of the friend who owns the entry
            _('%s put this away for now. You can look again when '
              'they share it.') % self._owner if self._owner
            else _('This was put away for now.'))
        self._ask_status.show()

    def _clean_comment(self, comment):
        clean = {'from': _clean_text(str(comment.get('from') or '')),
                 'message': _clean_text(str(comment.get('message') or ''))}
        color = comment.get('icon-color')
        if isinstance(color, str):
            try:
                XoColor(color)
            except Exception:
                pass
            else:
                clean['icon-color'] = color
        return clean

    def _payload_color(self, payload):
        try:
            return XoColor(str(payload.get('color') or _DEFAULT_COLOR))
        except Exception:
            return XoColor(_DEFAULT_COLOR)

    def _comment_card(self, comment):
        card = _class(Gtk.EventBox(), 'pv-card')
        card.set_halign(Gtk.Align.START)
        row = Gtk.HBox()
        row.set_spacing(style.DEFAULT_PADDING)
        row.set_border_width(style.zoom(9))

        icon = Icon(icon_name='computer-xo',
                    pixel_size=style.SMALL_ICON_SIZE)
        icon.props.xo_color = profile.get_color()
        icon.set_valign(Gtk.Align.START)
        row.pack_start(icon, False, False, 0)

        column = Gtk.VBox()
        who = _class(Gtk.Label(
            label=_clean_text(str(comment.get('from') or ''))), 'pv-who')
        who.set_xalign(0.0)
        who.set_ellipsize(Pango.EllipsizeMode.END)
        who.set_max_width_chars(40)
        column.pack_start(who, False, False, 0)
        said = _class(Gtk.Label(
            label=_clean_text(str(comment.get('message') or ''))),
            'pv-said')
        said.set_xalign(0.0)
        said.set_line_wrap(True)
        said.set_max_width_chars(40)
        column.pack_start(said, False, False, 0)
        row.pack_start(column, True, True, 0)

        card.add(row)
        return card

    def __build_ask(self, comments):
        self._ask_column = Gtk.VBox()
        self._ask_column.set_spacing(style.zoom(8))
        self._ask_column.set_margin_start(style.zoom(15))
        self._ask_column.set_margin_end(style.zoom(15))
        self._ask_column.set_margin_top(style.zoom(14))
        self._ask_column.set_margin_bottom(style.zoom(18))
        self._ask_status = _class(Gtk.Label(), 'pv-status')
        self._ask_status.set_xalign(0.0)
        self._ask_status.set_no_show_all(True)

        if peershare.has_asked(comments, profile.get_nick_name()):
            self._asked = True
            self._ask_status.set_label(_('You already asked here.'))
            self._ask_column.pack_start(self._ask_status, False, False, 0)
            self._ask_status.show()
            return self._ask_column

        self._ask_lead = _class(
            Gtk.Label(label=_('Ask your friend one question')), 'pv-lead')
        self._ask_lead.set_xalign(0.0)
        self._ask_column.pack_start(self._ask_lead, False, False, 0)

        self._ask_row = Gtk.HBox()
        self._ask_row.set_spacing(style.zoom(10))
        self._ask_entry = _class(Gtk.Entry(), 'pv-entry')
        self._ask_entry.set_max_length(peershare.ASK_LIMIT)
        self._ask_entry.set_has_frame(False)
        self._ask_entry.set_width_chars(40)
        self._ask_entry.connect('activate', self.__ask_cb)
        self._ask_row.pack_start(self._ask_entry, True, True, 0)
        # TRANS: button that sends the child's question to the friend
        self._ask_button = _class(Gtk.Button(label=_('Ask')), 'pv-send')
        self._ask_button.set_relief(Gtk.ReliefStyle.NONE)
        self._ask_button.connect('clicked', self.__ask_cb)
        self._ask_row.pack_start(self._ask_button, False, False, 0)
        self._ask_column.pack_start(self._ask_row, False, False, 0)
        self._ask_column.pack_start(self._ask_status, False, False, 0)
        return self._ask_column

    def __ask_cb(self, widget):
        if self._asked or self._proxy is None:
            return
        text = self._ask_entry.get_text().strip()
        if not text:
            return
        self._asked = True
        self._ask_entry.set_sensitive(False)
        self._ask_button.set_sensitive(False)
        self._send({'peershare': peershare.PROTOCOL,
                    'kind': peershare.KIND_ASK, 'uid': self._uid,
                    'message': text},
                   partial(self.__ask_error_cb, text),
                   partial(self.__asked_cb, text))

    def __asked_cb(self, text):
        self._ask_column.remove(self._ask_lead)
        self._ask_column.remove(self._ask_row)
        self._ask_row = None
        card = self._comment_card({'from': profile.get_nick_name(),
                                   'message': text})
        self._ask_column.pack_start(card, False, False, 0)
        self._ask_column.reorder_child(card, 0)
        self._ask_status.set_label(_('Your question is there now.'))
        self._ask_status.show()
        card.show_all()

    def __ask_error_cb(self, text, error):
        logging.error('peerview: could not send the question: %s', error)
        self._asked = False
        self._ask_entry.set_sensitive(True)
        self._ask_button.set_sensitive(True)
        self._ask_status.set_label(
            _('Your question did not get through. Try again?'))
        self._ask_status.show()

    def __key_press_cb(self, window, event):
        if Gdk.keyval_name(event.keyval) == 'Escape':
            self.destroy()
            return True
        return False

    def __destroy_cb(self, window):
        self._closed = True
        self._cancel_timeout()
        if self._gone_id is not None:
            neighborhood.get_model().disconnect(self._gone_id)
            self._gone_id = None
        if self._buddy_gone_id is not None:
            neighborhood.get_model().disconnect(self._buddy_gone_id)
            self._buddy_gone_id = None
        if self._match is not None:
            try:
                self._match.remove()
            except Exception:
                logging.exception('peerview: could not drop the listener')
            self._match = None
        # The channel belongs to the contact. Chat and any other page
        # opened on this friend are handed the same one, so drop the
        # reference and leave it open.
        self._proxy = None


def open_entry(activity):
    """Open the window for a friend's entry, or raise the open one."""
    view = _open_views.get(activity.activity_id)
    if view is not None:
        view.present()
        return view
    view = PeerEntryView(activity)
    _open_views[activity.activity_id] = view
    view.connect('destroy',
                 lambda window: _open_views.pop(activity.activity_id, None))
    return view
