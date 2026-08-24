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

"""Advertise shared Journal entries to the neighborhood.

An entry whose 'shared' metadata is '1' gets a salut room named by an
activity id minted from its uid, and rides the same BuddyInfo and
ActivityProperties wire that shared activities use. An older shell
that doesn't know the entry type sees an unknown bundle and drops the
advert.

The room only carries the advert. The page itself, the request for
it, and the visitor's question all travel over a plain one-to-one
text channel, so every message has to name the entry it's about.
Those channels are shared with whatever else the two friends say to
each other, so anything that isn't ours gets left in the queue unread
and unacknowledged for whoever else is reading.
"""

import base64
import hashlib
import json
import logging
import re
import unicodedata
from functools import partial

import dbus
import gi
gi.require_version('TelepathyGLib', '0.12')
from gi.repository import GLib
from gi.repository import TelepathyGLib

from sugar3 import profile
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.contentbundle import ContentBundle

from jarabe.journal import model
from jarabe.journal import reflectguard
from jarabe.journal import reflection
from jarabe.journal.journalentrybundle import JournalEntryBundle
from jarabe.model import neighborhood
from jarabe.model.neighborhood import CONNECTION_INTERFACE_BUDDY_INFO
from jarabe.model.neighborhood import CONNECTION_INTERFACE_REQUESTS
from jarabe.model.neighborhood import \
    CONNECTION_INTERFACE_ACTIVITY_PROPERTIES

CONNECTION = TelepathyGLib.IFACE_CONNECTION
CHANNEL = TelepathyGLib.IFACE_CHANNEL
CHANNEL_TYPE_TEXT = TelepathyGLib.IFACE_CHANNEL_TYPE_TEXT
HANDLE_TYPE_ROOM = TelepathyGLib.HandleType.ROOM
HANDLE_TYPE_CONTACT = int(TelepathyGLib.HandleType.CONTACT)
# A stock Chat window only renders NORMAL messages. Its
# TextChannelWrapper._received_cb drops anything else before it
# reaches the screen ("if type_ != 0: return" in sugarlabs/chat's
# activity.py), but it stays in the channel for
# whoever else is reading. That's why the whole protocol rides
# NOTICE.
MESSAGE_TYPE_PROTOCOL = int(TelepathyGLib.ChannelTextMessageType.NOTICE)

PROTOCOL = 1
KIND_FETCH = 'fetch'
KIND_ENTRY = 'entry'
KIND_ASK = 'ask'
KINDS = (KIND_FETCH, KIND_ENTRY, KIND_ASK)

# Longest question we'll take, in characters.
ASK_LIMIT = 500
# Ceiling on the encoded line, in bytes. A message goes whole or it
# doesn't go, so an entry whose preview would push it over the top
# gets sent without the preview.
PAYLOAD_LIMIT = 90000

# The entry keys a peer may see; build_entry_payload adds the uid,
# color, comments and preview on top of these. The child's talk with
# Jo, their moments and their next steps are deliberately not here,
# so they stay on this laptop.
_PAYLOAD_KEYS = ('title', 'description', 'tags', 'activity')

_RETRY_SECONDS = 10

_instance = None


def entry_activity_id(uid):
    return hashlib.sha1(uid.encode('utf-8')).hexdigest()


def without_activity(activities, activity_id):
    """The buddy's activity list with one entry filtered out.

    SetActivities replaces the whole list, so a retraction has to
    start from what GetActivities gave us. Sending only our own
    entries would drop everything else the child is sharing.
    """
    return [(aid, room_handle) for aid, room_handle in activities
            if aid != activity_id]


def entry_properties(metadata, color=None):
    if color is None:
        color = profile.get_color().to_string()
    # The connection manager rejects any key outside the stock
    # property set, so the uid, source bundle id and mime type all
    # ride space-separated in 'tags'. Only the mime type has a '/' in
    # it, which is how the reader tells the tokens apart when some of
    # them are missing.
    uid = metadata.get('uid', '')
    bundle_id = metadata.get('activity', '')
    mime_type = metadata.get('mime_type', '')
    tokens = [uid]
    if bundle_id:
        tokens.append(bundle_id)
    if mime_type and '/' in mime_type:
        tokens.append(mime_type)
    tags = ' '.join(tokens)
    return {
        'type': neighborhood.JOURNAL_ENTRY_TYPE,
        'name': metadata.get('title', '') or '',
        'color': color,
        'private': False,
        'tags': tags,
    }


def _preview_bytes(preview):
    if isinstance(preview, str):
        return preview.encode('utf-8')
    try:
        return bytes(preview)
    except TypeError:
        return b''


def build_entry_payload(metadata, color=None):
    """The page a friend gets to look at.

    Built up key by key. If it were built by stripping the metadata
    instead, a private key added to entries later would start
    travelling on its own.
    """
    payload = {'peershare': PROTOCOL, 'kind': KIND_ENTRY,
               'uid': str(metadata.get('uid', '') or '')}
    for key in _PAYLOAD_KEYS:
        payload[key] = str(metadata.get(key, '') or '')
    entry_color = metadata.get('icon-color')
    if not entry_color:
        entry_color = color if color is not None \
            else profile.get_color().to_string()
    payload['color'] = str(entry_color)
    payload['comments'] = reflection.parse_comments(
        metadata.get('comments', ''))
    preview = _preview_bytes(metadata.get('preview', ''))
    if preview:
        payload['preview'] = base64.b64encode(preview).decode('ascii')
    return payload


def encode_payload(payload):
    line = json.dumps(payload)
    if len(line.encode('utf-8')) <= PAYLOAD_LIMIT:
        return line
    payload = dict(payload)
    payload.pop('preview', None)
    return json.dumps(payload)


TAG_LIMIT = 8
TAG_CHARS = 32

_UID_SHAPE = re.compile(r'[A-Za-z0-9_-]{1,128}')

_BUNDLE_KINDS = (ActivityBundle.MIME_TYPE, ContentBundle.MIME_TYPE,
                 JournalEntryBundle.MIME_TYPE)


def safe_uid(uid):
    """The uid if it's a plain id, otherwise ''.

    The machinery this page gets handed to reads a uid that looks
    like a real path as a file to open, so nothing arriving off the
    wire is allowed to name a path on this laptop.
    """
    if not isinstance(uid, str) or _UID_SHAPE.fullmatch(uid) is None:
        return ''
    return uid


def safe_mime(mime_type):
    """Refuse the activity, content and Journal-entry bundle types,
    which would send the Journal looking for a file on disk.
    """
    if not isinstance(mime_type, str) or mime_type in _BUNDLE_KINDS:
        return ''
    return mime_type


def safe_tags(tags):
    """Trim the tag string down to what the page can draw."""
    if not isinstance(tags, str):
        return ''
    words = []
    for word in tags.split():
        word = ''.join(ch for ch in word
                       if unicodedata.category(ch)
                       not in ('Cc', 'Cf', 'Zl', 'Zp'))
        if word:
            words.append(word[:TAG_CHARS])
        if len(words) == TAG_LIMIT:
            break
    return ' '.join(words)


def parse_message(line):
    """Parse a line as this protocol's envelope, or return None.

    These are plain text channels, so most of what arrives on one is
    somebody else's traffic and gets ignored. The channel only tells
    us which friend we're talking to, so a fetch or an ask has to
    carry the uid itself or there's nothing to answer.
    """
    try:
        message = json.loads(line)
    except (TypeError, ValueError):
        return None
    if not isinstance(message, dict):
        return None
    version = message.get('peershare')
    if isinstance(version, bool) or version != PROTOCOL:
        return None
    kind = message.get('kind')
    if kind not in KINDS:
        return None
    if kind in (KIND_FETCH, KIND_ASK):
        uid = message.get('uid')
        if not isinstance(uid, str) or not uid:
            return None
    return message


_stray_chat_cb = None


def set_stray_chat_cb(callback):
    """Register the listener for real chat on a protocol line.

    The invites model quietens the knock for channels that only carry
    protocol, so it needs telling when a friend starts actually
    talking on one.
    """
    global _stray_chat_cb
    _stray_chat_cb = callback


def sender_nick(nick):
    """A peer's nick for a comment's 'from', or '' for anonymous.

    Anything longer than a real name, or carrying control or
    direction-changing characters, comes back as ''.
    """
    nick = nick.strip() if isinstance(nick, str) else ''
    if len(nick) > reflection.PEER_NAME_LIMIT:
        return ''
    if any(unicodedata.category(ch) in ('Cc', 'Cf', 'Zl', 'Zp')
           for ch in nick):
        return ''
    return nick


def has_asked(comments, nick):
    """Whether this visitor's question already stands on the entry.

    The answer comes out of the entry's own comments, so closing the
    page and opening it again doesn't hand out a second turn.
    Visitors with no usable name all share the anonymous slot.
    """
    if not isinstance(comments, list):
        return False
    who = sender_nick(nick)
    return any(isinstance(comment, dict) and comment.get('from') == who
               for comment in comments)


def append_comment(comments_raw, nick, text, color=''):
    """The entry's comments with one friend's question appended, or
    None if the ask can't be taken.

    This is where one-question-per-friend is actually enforced. The
    visitor's window checks too, but that check runs on their machine
    and can't be relied on here. A record already at MAX_COMMENTS
    takes no more, which keeps a peer from growing it without bound.
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text or len(text) > ASK_LIMIT:
        return None
    # Zero-width joiners are allowed through because that's how
    # multi-part emoji hold together. Every other format character is
    # a lever on how the record displays. A question made of nothing
    # but joiners has nothing to show, so it goes too.
    bare = text.replace('\u200d', '')
    if not bare or any(unicodedata.category(ch) in ('Cc', 'Cf', 'Zl', 'Zp')
                       for ch in bare):
        return None
    who = sender_nick(nick)
    comments = reflection.parse_comments(comments_raw)
    if len(comments) >= reflectguard.MAX_COMMENTS:
        return None
    for comment in comments:
        if comment.get('from') == who:
            return None
    entry = {'from': who, 'message': text}
    if color:
        entry['icon-color'] = color
    comments.append(entry)
    return json.dumps(comments)


class PeerShare(object):

    def __init__(self):
        self._shares = {}
        self._pending = set()
        self._retractions = set()
        self._retract_inflight = False
        self._peers = {}
        self._watches = []
        self._bus_name = None
        self._wait_source = None
        self._buddy_info_absent = False
        model.updated.connect(self.__entry_updated_cb)
        model.deleted.connect(self.__entry_deleted_cb)
        neighborhood.get_model().connect(
            'link-local-connection-changed', self.__connection_changed_cb)
        GLib.idle_add(self.__rescan_cb)

    def _connection(self):
        return neighborhood.get_model().get_link_local_connection()

    def __rescan_cb(self):
        # The datastore's filter on 'shared' isn't reliable, so
        # re-read every hit before letting it advertise.
        try:
            bus = dbus.SessionBus()
            data_store = dbus.Interface(
                bus.get_object('org.laptop.sugar.DataStore',
                               '/org/laptop/sugar/DataStore'),
                'org.laptop.sugar.DataStore')
            entries, _count = data_store.find(
                {'shared': '1'}, ['uid'], byte_arrays=True)
        except Exception:
            logging.exception('peershare: could not scan for shared entries')
            return False
        for entry in entries:
            uid = str(entry['uid'])
            try:
                metadata = model.get(uid)
            except Exception:
                continue
            if metadata.get('shared', '0') == '1':
                reflectguard.get_guard().note_shared(uid, '1')
                self._queue(uid)
        return False

    def _queue(self, uid):
        self._retractions.discard(uid)
        if uid in self._shares or uid in self._pending:
            return
        self._pending.add(uid)
        self._flush()

    def _flush(self):
        conn = self._connection()
        if conn is None:
            self._arm_wait()
            return
        self._ensure_watch(conn)
        if not self._buddy_info_ready(conn):
            return
        for uid in list(self._pending):
            self._pending.discard(uid)
            self._advertise(uid, conn)

    def _buddy_info_ready(self, conn):
        if CONNECTION_INTERFACE_BUDDY_INFO in conn:
            return True
        # If it's missing it stays missing for the life of this
        # connection, so retrying every few seconds just opens and
        # closes rooms for nothing. The next connection gets a fresh
        # try.
        if not self._buddy_info_absent:
            self._buddy_info_absent = True
            logging.warning('peershare: connection has no BuddyInfo '
                            'interface; entries stay unadvertised')
        return False

    def _arm_wait(self):
        """Make sure the retry timer is running.

        Two things end up waiting on this: entries queued while there
        was no connection at all, and entries parked after a call came
        back an error. Both want the same thing a few seconds later,
        so one timer covers the whole queue. __wait_cb lets it die
        once the queues are empty, which keeps an idle shell from
        waking up every ten seconds forever. Calling this while the
        timer is already armed does nothing.
        """
        if self._wait_source is not None:
            return
        self._wait_source = GLib.timeout_add_seconds(
            _RETRY_SECONDS, self.__wait_cb)

    def __wait_cb(self):
        if not self._pending and not self._retractions:
            self._wait_source = None
            return False
        if self._connection() is None:
            return True
        self._wait_source = None
        self._flush()
        self._flush_retractions()
        return False

    def __connection_changed_cb(self, neighbors):
        conn = self._connection()
        if conn is None:
            self._drop_shares()
            self._drop_peers()
            return
        # What the dead connection was missing tells us nothing about
        # this one, so look for BuddyInfo again.
        self._buddy_info_absent = False
        # A read still out against the dead bus will never come back.
        # Leaving the flag set would jam retractions for the rest of
        # the session.
        self._retract_inflight = False
        self._flush()
        self._flush_retractions()

    def _drop_shares(self):
        """The channels and handles went with the dead connection, so
        there is nothing left to close and the rooms are just
        forgotten. Each entry goes back on the pending queue for
        whatever connection turns up next.
        """
        for uid in list(self._shares):
            self._pending.add(uid)
        self._shares.clear()
        self._retract_inflight = False
        if self._pending:
            self._arm_wait()

    def _advertise(self, uid, conn):
        activity_id = entry_activity_id(uid)
        self._shares[uid] = {'activity_id': activity_id,
                             'room_handle': None, 'channel': None,
                             'advertised': False,
                             'bus_name': conn[CONNECTION].bus_name}
        logging.debug('peershare: advertising %r as %r', uid, activity_id)
        try:
            conn[CONNECTION].RequestHandles(
                HANDLE_TYPE_ROOM, [activity_id],
                reply_handler=partial(self.__got_room_cb, uid),
                error_handler=partial(self.__share_error_cb, uid,
                                      'RequestHandles'))
        except Exception as error:
            # A dead proxy raises straight away and never calls back.
            self.__share_error_cb(uid, 'RequestHandles', error)

    def _park(self, uid):
        share = self._shares.pop(uid, None)
        if share is None and uid not in self._pending:
            # A late error for a share that has already been
            # retracted. Parking it would put an unshared entry back
            # on the neighborhood.
            return
        if share is not None:
            self._close_channel(share)
        self._pending.add(uid)
        self._arm_wait()

    def _close_channel(self, share):
        channel_path = share.get('channel')
        if channel_path is None:
            return
        try:
            bus = dbus.SessionBus()
            channel = bus.get_object(share['bus_name'], channel_path)
            channel.Close(dbus_interface=CHANNEL,
                          reply_handler=lambda: None,
                          error_handler=partial(self.__close_error_cb,
                                                channel_path))
        except Exception:
            logging.exception('peershare: could not close the room')

    def __close_error_cb(self, channel_path, error):
        logging.error('peershare: Close failed for %r: %s',
                      channel_path, error)

    def __got_room_cb(self, uid, handles):
        share = self._shares.get(uid)
        if share is None:
            return
        conn = self._connection()
        if conn is None:
            self._park(uid)
            return
        share['room_handle'] = handles[0]
        try:
            conn[CONNECTION].RequestChannel(
                CHANNEL_TYPE_TEXT, HANDLE_TYPE_ROOM, handles[0], True,
                reply_handler=partial(self.__got_channel_cb, uid),
                error_handler=partial(self.__share_error_cb, uid,
                                      'RequestChannel'))
        except Exception as error:
            self.__share_error_cb(uid, 'RequestChannel', error)

    def __got_channel_cb(self, uid, channel_path):
        share = self._shares.get(uid)
        if share is None:
            return
        conn = self._connection()
        if conn is None:
            self._park(uid)
            return
        share['channel'] = channel_path
        if not self._buddy_info_ready(conn):
            self._park(uid)
            return
        try:
            conn[CONNECTION_INTERFACE_BUDDY_INFO].AddActivity(
                share['activity_id'], share['room_handle'],
                reply_handler=partial(self.__advertised_cb, uid),
                error_handler=partial(self.__share_error_cb, uid,
                                      'AddActivity'))
        except Exception as error:
            self.__share_error_cb(uid, 'AddActivity', error)

    def __advertised_cb(self, uid):
        logging.debug('peershare: %r is on the neighborhood', uid)
        share = self._shares.get(uid)
        if share is not None:
            share['advertised'] = True
        self._publish_properties(uid)

    def _publish_properties(self, uid):
        share = self._shares.get(uid)
        conn = self._connection()
        if share is None or conn is None or share['room_handle'] is None:
            return
        try:
            metadata = model.get(uid)
        except Exception:
            logging.exception('peershare: could not read %r', uid)
            return
        try:
            conn[CONNECTION_INTERFACE_ACTIVITY_PROPERTIES].SetProperties(
                share['room_handle'], entry_properties(metadata),
                reply_handler=lambda: None,
                error_handler=partial(self.__share_error_cb, uid,
                                      'SetProperties'))
        except Exception as error:
            self.__share_error_cb(uid, 'SetProperties', error)

    def _ensure_watch(self, conn):
        """Watch the connection for the channels peers talk on.

        A fetch turns up on a one-to-one text channel no matter who
        opened it, so this has to catch channels our own window asked
        for as well as ones a friend opened: if we're looking at their
        entry while they look at ours, both sides are talking down the
        same channel. Which signal announces it depends on the
        connection manager, so the old Connection.NewChannel and the
        Requests.NewChannels are both hooked up and _attach ignores a
        path it has seen before. That still leaves channels that were
        open before any of this ran, because salut keeps going on the
        user bus across a shell restart, so the Get(Channels) call at
        the end sweeps those up.
        """
        if self._bus_name is not None:
            return
        self._bus_name = conn[CONNECTION].bus_name
        watches = ((CONNECTION, 'NewChannel', self.__new_channel_cb),
                   (CONNECTION_INTERFACE_REQUESTS, 'NewChannels',
                    self.__new_channels_cb))
        for interface, signal, callback in watches:
            try:
                self._watches.append(
                    conn[interface].connect_to_signal(signal, callback))
            except Exception:
                logging.exception('peershare: could not watch %s', signal)
        # Sweep up the channels that were already open.
        try:
            bus = dbus.SessionBus()
            proxy = bus.get_object(self._bus_name,
                                   conn[CONNECTION].object_path)
            proxy.Get(CONNECTION_INTERFACE_REQUESTS, 'Channels',
                      dbus_interface=dbus.PROPERTIES_IFACE,
                      reply_handler=self.__new_channels_cb,
                      error_handler=partial(self.__log_error_cb,
                                            'watch', 'Get(Channels)'))
        except Exception:
            logging.exception('peershare: could not sweep open channels')

    def __new_channel_cb(self, channel_path, channel_type, handle_type,
                         handle, suppress_handler):
        if channel_type == CHANNEL_TYPE_TEXT and \
                handle_type == HANDLE_TYPE_CONTACT:
            self._attach(channel_path)

    def __new_channels_cb(self, channels):
        for channel_path, properties in channels:
            if properties.get(CHANNEL + '.ChannelType') == \
                    CHANNEL_TYPE_TEXT and \
                    properties.get(CHANNEL + '.TargetHandleType') == \
                    HANDLE_TYPE_CONTACT:
                self._attach(channel_path)

    def _attach(self, channel_path):
        if channel_path in self._peers or self._bus_name is None:
            return
        try:
            bus = dbus.SessionBus()
            proxy = bus.get_object(self._bus_name, channel_path)
        except Exception:
            logging.exception('peershare: could not open a visitor channel')
            return
        peer = {'proxy': proxy, 'match': None}
        self._peers[channel_path] = peer
        peer['match'] = proxy.connect_to_signal(
            'Received', partial(self.__peer_received_cb, channel_path),
            dbus_interface=CHANNEL_TYPE_TEXT)
        # A fetch that landed before the signal handler was connected
        # is still in the pending queue. Reading with clear=False
        # leaves it there for anyone else on the channel.
        proxy.ListPendingMessages(
            False, dbus_interface=CHANNEL_TYPE_TEXT,
            reply_handler=partial(self.__peer_pending_cb, channel_path),
            error_handler=partial(self.__log_error_cb, channel_path,
                                  'ListPendingMessages'))

    def __peer_pending_cb(self, channel_path, messages):
        for message in messages:
            self.__peer_received_cb(channel_path, *message)

    def __peer_received_cb(self, channel_path, message_id, timestamp,
                           sender, message_type, flags, text):
        message = parse_message(text)
        if message is None:
            # A friend's chat rides these channels too. Leave it in
            # the queue unread and unacknowledged so its own reader
            # finds it, but tell whoever quietened this line that
            # someone is actually talking on it.
            if _stray_chat_cb is not None:
                try:
                    _stray_chat_cb(channel_path, sender)
                except Exception:
                    logging.exception('peershare: stray chat listener')
            return
        kind = message['kind']
        if kind not in (KIND_FETCH, KIND_ASK):
            # An entry payload is an answer; the window that asked
            # deals with it.
            return
        self._acknowledge(channel_path, message_id)
        uid = message['uid']
        if uid not in self._shares:
            return
        if kind == KIND_FETCH:
            self._send_entry(channel_path, uid)
        else:
            self._take_ask(uid, sender, message.get('message'))

    def _drop_peers(self):
        for peer in list(self._peers.values()):
            self._remove_match(peer['match'])
        self._peers.clear()
        for match in self._watches:
            self._remove_match(match)
        self._watches = []
        self._bus_name = None

    def _remove_match(self, match):
        if match is None:
            return
        try:
            match.remove()
        except Exception:
            logging.exception('peershare: could not drop a listener')

    def _acknowledge(self, channel_path, message_id):
        peer = self._peers.get(channel_path)
        if peer is None:
            return
        peer['proxy'].AcknowledgePendingMessages(
            [message_id], dbus_interface=CHANNEL_TYPE_TEXT,
            reply_handler=lambda: None,
            error_handler=partial(self.__log_error_cb, channel_path,
                                  'AcknowledgePendingMessages'))

    def _send_entry(self, channel_path, uid):
        peer = self._peers.get(channel_path)
        if peer is None:
            return
        try:
            metadata = model.get(uid)
        except Exception:
            logging.exception('peershare: could not read %r', uid)
            return
        peer['proxy'].Send(
            MESSAGE_TYPE_PROTOCOL,
            encode_payload(build_entry_payload(metadata)),
            dbus_interface=CHANNEL_TYPE_TEXT,
            reply_handler=lambda: None,
            error_handler=partial(self.__log_error_cb, uid, 'Send'))

    def _take_ask(self, uid, sender, text):
        # Read fresh. The datastore replaces the whole record on
        # write, so writing back an older copy would roll back
        # anything the child changed in the meantime.
        try:
            metadata = model.get(uid)
        except Exception:
            logging.exception('peershare: could not read %r', uid)
            return False
        who, color = self._sender(sender)
        comments = append_comment(metadata.get('comments', ''),
                                  who, text, color=color)
        if comments is None:
            return False
        metadata['comments'] = comments
        model.write(metadata, update_mtime=False)
        # An activity that resumes with the metadata it loaded
        # earlier would wipe the question we just wrote. The guard
        # puts it back.
        delivered = reflection.parse_comments(comments)
        if delivered:
            reflectguard.get_guard().note_delivered_comment(
                uid, delivered[-1])
        return True

    def _sender(self, handle):
        """Look up the sender's nick and color.

        Both come from the channel's sender handle and our own
        presence record. A nick or color carried inside the message
        would just be whatever the sender typed there.
        """
        try:
            neighbors = neighborhood.get_model()
            if handle == neighbors.get_link_local_self_handle():
                return (profile.get_nick_name(),
                        profile.get_color().to_string())
            buddy = neighbors.get_buddy_by_handle(handle)
        except Exception:
            logging.exception('peershare: could not name the sender')
            return '', ''
        if buddy is None:
            return '', ''
        color = buddy.get_color()
        return (buddy.get_nick() or '',
                color.to_string() if color is not None else '')

    def __share_error_cb(self, uid, call, error):
        logging.error('peershare: %s failed for %r: %s', call, uid, error)
        self._park(uid)

    def _retract(self, uid):
        self._pending.discard(uid)
        share = self._shares.pop(uid, None)
        if share is None:
            return
        logging.debug('peershare: retracting %r', uid)
        self._close_channel(share)
        self._retractions.add(uid)
        self._flush_retractions()

    def _flush_retractions(self):
        """Push the queued retractions out over BuddyInfo.

        This needs a live connection, so without one the retraction
        stays queued and the timer brings us back to it. The whole
        queue goes out in a single read-modify-write round, because
        two overlapping rounds would each write back what the other
        had just removed.
        """
        if not self._retractions or self._retract_inflight:
            return
        conn = self._connection()
        if conn is None or not self._buddy_info_ready(conn):
            self._arm_wait()
            return
        self_handle = neighborhood.get_model().get_link_local_self_handle()
        if self_handle is None:
            self._arm_wait()
            return
        self._retract_inflight = True
        try:
            conn[CONNECTION_INTERFACE_BUDDY_INFO].GetActivities(
                self_handle,
                reply_handler=self.__got_own_activities_cb,
                error_handler=self.__retract_read_error_cb)
        except Exception:
            # A call that never went out won't reach either handler,
            # and a flag left set here would stop retractions for the
            # rest of the session.
            self._retract_inflight = False
            logging.exception('peershare: could not read own activities')
            self._arm_wait()

    def __got_own_activities_cb(self, activities):
        self._retract_inflight = False
        conn = self._connection()
        if conn is None:
            return
        batch = []
        remaining = list(activities)
        for uid in list(self._retractions):
            self._retractions.discard(uid)
            if uid in self._shares or uid in self._pending:
                # The child shared it again while we were asking, so
                # leave the new advert alone.
                continue
            batch.append(uid)
            remaining = without_activity(remaining, entry_activity_id(uid))
        if not batch:
            return
        # An advert that landed after the read would be lost if we
        # wrote back the list from before it, so put those back in.
        # Only shares whose AddActivity already went through count.
        # Naming the room any earlier shows peers an advert with no
        # properties on it yet.
        present = set(activity_id for activity_id, _ in remaining)
        for share in self._shares.values():
            if share.get('advertised') and \
                    share['activity_id'] not in present:
                remaining.append((share['activity_id'],
                                  share['room_handle']))
        try:
            conn[CONNECTION_INTERFACE_BUDDY_INFO].SetActivities(
                remaining,
                reply_handler=lambda: None,
                error_handler=partial(self.__retract_error_cb, batch))
        except Exception as error:
            self.__retract_error_cb(batch, error)

    def __retract_read_error_cb(self, error):
        self._retract_inflight = False
        logging.error('peershare: GetActivities failed: %s', error)
        self._arm_wait()

    def __retract_error_cb(self, batch, error):
        logging.error('peershare: SetActivities failed for %r: %s',
                      batch, error)
        for uid in batch:
            if uid not in self._shares:
                self._retractions.add(uid)
        self._arm_wait()

    def __log_error_cb(self, uid, call, error):
        logging.error('peershare: %s failed for %r: %s', call, uid, error)

    def __entry_updated_cb(self, sender, object_id=None, **kwargs):
        if not object_id:
            return
        try:
            metadata = model.get(object_id)
        except Exception:
            return
        shared = metadata.get('shared', '0') == '1'
        if shared and object_id not in self._shares:
            self._queue(object_id)
        elif not shared:
            self._retract(object_id)
        else:
            # The title may have changed under the advert.
            self._publish_properties(object_id)

    def __entry_deleted_cb(self, sender, object_id=None, **kwargs):
        if object_id:
            self._retract(object_id)


def is_ours(uid):
    return _instance is not None and uid in _instance._shares


def start():
    global _instance
    if _instance is None:
        _instance = PeerShare()
