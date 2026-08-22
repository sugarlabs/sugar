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

import configparser
import json
import logging
import os
import random
import re
import socket
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from gettext import gettext as _


SCHEMA_VERSION = 1

# Hard budget for the serialized metadata['reflections'] string. Any
# property over ~500 KB makes carquinyol's metadatareader.c raise
# ValueError and the whole entry becomes unreadable; 64 KB is margin.
MAX_REFLECTIONS_BYTES = 64 * 1024

ROLE_JO = 'jo'
ROLE_CHILD = 'child'

# The metadata keys holding the child's private talk: the serialized
# conversation, the numbered moment snaps (momentcard builds its key
# from this prefix), and next_steps, written only by the server
# layer's capture. Never copied where others browse.
SNAP_KEY_PREFIX = 'moment-snap-'
_PRIVATE_KEYS = ('reflections', 'next_steps')


def strip_private(metadata):
    for key in _PRIVATE_KEYS:
        metadata.pop(key, None)
    for key in [k for k in metadata if k.startswith(SNAP_KEY_PREFIX)]:
        del metadata[key]


def empty_conversation():
    return {'version': SCHEMA_VERSION, 'sessions': []}


def loads(raw):
    """Parse metadata['reflections']. Never raises; unknown keys survive."""
    if not raw:
        return empty_conversation()
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return empty_conversation()
    if not isinstance(data, dict):
        return empty_conversation()
    sessions = data.get('sessions', [])
    if not isinstance(sessions, list):
        return empty_conversation()
    data['sessions'] = [s for s in sessions if isinstance(s, dict)]
    moments = data.get('moments', [])
    if not isinstance(moments, list):
        moments = []
    data['moments'] = [m for m in moments if isinstance(m, dict)]
    seq = data.get('moment_seq', 0)
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
        data['moment_seq'] = max(
            [m.get('snap_seq', -1) for m in data['moments']
             if isinstance(m.get('snap_seq'), int)] + [-1]) + 1
    data.setdefault('version', SCHEMA_VERSION)
    return data


def dumps(data):
    """Serialize, evicting whole sessions oldest-first to fit
    MAX_REFLECTIONS_BYTES. Never the last one; never mutates input.
    """
    body = dict(data)
    sessions = list(body.get('sessions', []))
    body['sessions'] = sessions
    text = json.dumps(body)
    while len(text.encode('utf-8')) > MAX_REFLECTIONS_BYTES and \
            len(sessions) > 1:
        sessions.pop(0)
        body['sessions'] = sessions
        text = json.dumps(body)
    return text


def new_session(framework):
    return {'ts': int(time.time()), 'framework': framework, 'turns': []}


def new_session_id():
    """An id for a session that may need re-merging later. The
    datastore prunes any key an update omits, so an activity's stale
    close-time save drops the shell's session; the id puts it back.
    """
    return uuid.uuid4().hex


def find_session(data, sid):
    if not sid:
        return None
    for session in data.get('sessions', []):
        if session.get('sid') == sid:
            return session
    return None


def merge_session(data, session):
    sid = session.get('sid')
    body = dict(data)
    sessions = [s for s in body.get('sessions', [])
                if sid is None or s.get('sid') != sid]
    sessions.append(session)
    body['sessions'] = sessions
    return body


def merge_sessions_for_write(fresh_raw, sessions):
    """The store's current state with our sessions merged in. update()
    prunes any key the writer omits, so never write from a stale copy.
    Matched by sid then ts; whichever copy holds more turns wins.
    """
    data = loads(fresh_raw)
    for session in sessions:
        sid = session.get('sid')
        held = find_session(data, sid)
        if held is None:
            for candidate in data.get('sessions', []):
                if 'sid' not in candidate and 'sid' not in session and \
                        candidate.get('ts') == session.get('ts'):
                    held = candidate
                    break
        if held is not None:
            if len(held.get('turns', ())) > len(session.get('turns', ())):
                continue
            if held is not find_session(data, sid):
                body = dict(data)
                body['sessions'] = [s for s in body.get('sessions', [])
                                    if s is not held]
                data = body
        data = merge_session(data, session)
    data['sessions'] = sorted(data.get('sessions', []),
                              key=lambda s: s.get('ts', 0))
    return data


def has_kept_line(description, text):
    return text in (description or '').split('\n')


def kept_lines(raw, description, limit=2):
    """The kept child lines still in the description, newest first."""
    if not raw or not description:
        return []
    data = loads(raw)
    lines = []
    for session in reversed(data.get('sessions', [])):
        for turn in reversed(session.get('turns', [])):
            if turn.get('role') != ROLE_CHILD:
                continue
            text = turn.get('text', '')
            if text and text not in lines and \
                    has_kept_line(description, text):
                lines.append(text)
                if len(lines) >= limit:
                    return lines
    return lines


def add_turn(session, role, text, peer=False, q=None, local=False,
             typed=None):
    """Append a turn to a session and return it. peer marks a Jo turn
    voicing another child's comment, and rides the stored turn so
    later sessions still read it as a people question. q is the
    scripted question's stable id, stamped from the text or passed in
    when a composed line stands in for a script slot. local marks a Jo
    turn whose text must never reach the wire, and latches the child's
    answer off the wire with it. typed carries the engine's stamped
    fields for a server turn (kind, engagement, and the flags), so
    the next request rebuilds the engine's record exactly instead of
    re-deriving anything from text.
    """
    if role not in (ROLE_JO, ROLE_CHILD):
        raise ValueError('Unknown role: %r' % (role,))
    turn = {'role': role, 'text': text}
    if peer:
        turn['peer'] = True
    if role == ROLE_JO:
        if q is None:
            q = _QUESTION_ID.get(text)
        if q is not None:
            turn['q'] = q
        if local:
            turn['local'] = True
        if typed:
            turn['kind'] = typed.get('kind', 'question')
            turn['engagement'] = typed.get('engagement', 'engaged')
            for name in ('open', 'simplified', 'people_adjacent'):
                if typed.get(name):
                    turn[name] = True
    session.setdefault('turns', []).append(turn)
    return session


def _asks_about_people(text):
    return text in (TOGETHER_OPENER, NEARBY_NUDGE, NEARBY_MIDFLOW,
                    NEARBY_FOLLOWUP)


def _people_turn(turn):
    if turn.get('people_adjacent'):
        # The engine stamps its own turns; the sniffing below only
        # ever covers floor questions and turns stored before the
        # stamp existed.
        return True
    if turn.get('peer'):
        return True
    qid = turn.get('q')
    if isinstance(qid, str):
        return qid in _PEOPLE_IDS
    return _asks_about_people(turn.get('text', ''))


# Memory is the server's alone. The engine types the child's
# forward answer now: a session_end carries next_step (the child's
# words, verbatim, or null) and asked. The old marker regex that
# sniffed which question was forward-looking is gone with the wire
# that needed it.


def resolve_next_steps(session, previous):
    """What metadata['next_steps'] should hold after this session.

    A fresh answer replaces the note. A server session that closed
    with nothing retires it - carrying it further would be nagging.
    An offline session never closes server-side and leaves it alone:
    the floor never saw it.
    """
    end = session.get('end')
    if not isinstance(end, dict):
        return previous or ''
    step = end.get('next_step')
    if isinstance(step, str) and step.strip():
        # Clipped at the write so a paste cannot grow the metadata
        # property without bound.
        return clip_line(step, 120)
    return ''


def get_next_steps(metadata):
    return metadata.get('next_steps', '') or ''


def keep_in_description(description, text):
    """Append a starred answer to the description, verbatim."""
    if not description:
        return text
    return description.rstrip('\n') + '\n' + text


def unkeep_from_description(description, text):
    lines = description.split('\n')
    for i in range(len(lines) - 1, -1, -1):
        if lines[i] == text:
            del lines[i]
            return '\n'.join(lines)
    return description


def people_kept_in_description(raw, description):
    """Whether an answer to a people question - from any session the
    record holds, not only the open one - is kept in this description.
    A starred answer names someone in the room, so its description
    cannot ride a request.
    """
    if not description:
        return False
    for session in loads(raw).get('sessions', []):
        turns = session.get('turns')
        if not isinstance(turns, list):
            continue
        people = False
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            role = turn.get('role')
            if role == ROLE_JO:
                people = _people_turn(turn) or bool(turn.get('local'))
            if people and role == ROLE_CHILD and \
                    has_kept_line(description, turn.get('text', '')):
                return True
    return False


# Activities grouped into the five categories the offline floor asks
# from. The server keeps its own copy, held in step by hand; if the
# two drift, an unknown bundle just falls to creative on both sides.
CATEGORY_BUNDLES = {
    'creative': [
        'org.laptop.TurtleArtActivity',
        'org.laptop.Oficina',
        'org.laptop.AbiWordActivity',
        'org.laptop.Record',
        'org.sugarlabs.MusicBlocksActivity',
    ],
    'programming': [
        'org.laptop.PippyActivity',
        'org.laptop.Pippy',
        'org.laptop.Calculate',
        'org.laptop.Terminal',
        'org.laptop.Physics',
        'org.laptop.Measure',
    ],
    'exploration': [
        'org.laptop.WebActivity',
        'org.laptop.Log',
        'org.laptop.ImageViewerActivity',
    ],
    'game': [
        'org.laptop.Memorize',
        'org.sugarlabs.Maze',
        'org.sugarlabs.Clock',
        'org.sugarlabs.Abacus',
    ],
    'communication': [
        'org.laptop.Chat',
        'org.laptop.Speak',
    ],
}

DEFAULT_CATEGORY = 'creative'

BUNDLE_CATEGORY = {}
for _category, _bundles in CATEGORY_BUNDLES.items():
    for _bundle_id in _bundles:
        BUNDLE_CATEGORY[_bundle_id] = _category


def get_category(activity_id):
    return BUNDLE_CATEGORY.get(activity_id, DEFAULT_CATEGORY)


# Static banks for when Jo cannot see the work. Two questions is the
# whole visit - past the pair, a floor turn is one Jo cannot react to.
FLOOR_BANK = {
    'creative': [
        _("I can't see your work right now, but I'd love to hear "
          "about it. What did you make?"),
        _("If you could add one more thing to it, what would it be?"),
    ],
    'programming': [
        _("I can't see your project right now, but tell me about it. "
          "What were you trying to make it do?"),
        _("If you kept going, what would you make it do next?"),
    ],
    'exploration': [
        _("I can't see what you found right now, but tell me about "
          "it. What did you discover?"),
        _("Where would you look next?"),
    ],
    'game': [
        _("I can't see how your game went right now, but tell me "
          "about it. What happened when you played?"),
        _("What will you try differently next time?"),
    ],
    'communication': [
        _("I can't see your conversation right now, but tell me "
          "about it. Who did you talk to?"),
        _("What would you ask them next time?"),
    ],
}

DEFAULT_FLOOR_BANK = [
    _("I can't see your work right now, but tell me about it. What "
      "did you just do?"),
    _("What would you do differently next time?"),
]

# Openers for work on screen, keyed by the one each stands in for.
# Jo still never claims to see it; these only drop the disclaimer.
VISIBLE_WORK_OPENERS = {
    FLOOR_BANK['creative'][0]:
        _("I'd love to hear about what you made. What is it?"),
    FLOOR_BANK['programming'][0]:
        _("Tell me about your project. What were you trying to make "
          "it do?"),
    FLOOR_BANK['exploration'][0]:
        _("Tell me about what you found. What did you discover?"),
    FLOOR_BANK['game'][0]:
        _("How did your game go? What happened when you played?"),
    FLOOR_BANK['communication'][0]:
        _("Tell me about your conversation. Who did you talk to?"),
    DEFAULT_FLOOR_BANK[0]:
        _("Tell me about what you just did. What was it?"),
}

# Never composed from the description, which is prose the child owns.
# TRANS: %(title)s is the child's own title or caption, quoted as is.
TITLED_OPENER = _('You called this “%(title)s”. '
                  'What do you like most about it?')

# Asked once beside work with a recorded shared session. That record
# is wrong both ways, so the question stays open and names no one.
TOGETHER_OPENER = _("What did you work out together on this one, "
                    "or was it all you?")

# When the bank runs dry, point the child at a nearby person, once
# per artifact, carrying a question to ask - never a line to repeat.
NEARBY_NUDGE = _("I'm out of questions about this one. What does "
                 "someone near you notice when you show it to them?")
NEARBY_FOLLOWUP = _("If you talked this one over with someone, "
                    "what did you two figure out?")

# The room can also come up mid-talk. Either form spends the one
# nearby slot; both numbers below are guesses until children set them.
# TRANS: the same question as the nudge above without its preamble -
# please keep the two parallel.
NEARBY_MIDFLOW = _("What does someone near you notice when you show "
                   "it to them?")
NEARBY_MIDFLOW_CHANCE = 0.25
NEARBY_MIDFLOW_WARMUP = 1

# A peer's question from the stock comments box, voiced as a Jo turn,
# once each. Comments arrive from other people, so only one shaped
# like an honest question gets a voice, and it and its answers stay
# off the wire: another child's words and name.
# TRANS: %(who)s is the commenter's name, %(question)s their words.
PEER_QUESTION_OPENER = _('%(who)s saw this and asks: “%(question)s”')
# TRANS: the same line for a comment that carries no name.
PEER_QUESTION_ANON = _('Someone saw this and asks: “%(question)s”')

# A name longer than any real name is not a name; the line it would
# build could evict the child's whole saved talk.
PEER_NAME_LIMIT = 40

_ALL_FLOOR_QUESTIONS = set(DEFAULT_FLOOR_BANK)
for _questions in FLOOR_BANK.values():
    _ALL_FLOOR_QUESTIONS.update(_questions)
_ALL_FLOOR_QUESTIONS.update(VISIBLE_WORK_OPENERS.values())
_ALL_FLOOR_QUESTIONS.add(TOGETHER_OPENER)
_ALL_FLOOR_QUESTIONS.add(NEARBY_NUDGE)
_ALL_FLOOR_QUESTIONS.add(NEARBY_MIDFLOW)
_ALL_FLOOR_QUESTIONS.add(NEARBY_FOLLOWUP)

# Every scripted question carries a stable id, stamped on the Jo turn
# as 'q', so used-tracking survives a locale switch. An opener and
# its beside-the-work variant share one id: one slot, either voice.
_QUESTION_ID = {}
_ID_QUESTION = {}


def _register_question(qid, text):
    _QUESTION_ID[text] = qid
    _ID_QUESTION.setdefault(qid, text)


for _cat, _questions in FLOOR_BANK.items():
    for _i, _question in enumerate(_questions):
        _register_question('floor:%s:%d' % (_cat, _i), _question)
for _i, _question in enumerate(DEFAULT_FLOOR_BANK):
    _register_question('floor:default:%d' % _i, _question)
for _plain, _beside in VISIBLE_WORK_OPENERS.items():
    _register_question(_QUESTION_ID[_plain], _beside)
_register_question('together', TOGETHER_OPENER)
_register_question('nearby:nudge', NEARBY_NUDGE)
_register_question('nearby:midflow', NEARBY_MIDFLOW)
_register_question('nearby:followup', NEARBY_FOLLOWUP)

_PEOPLE_IDS = {'together', 'nearby:nudge', 'nearby:midflow',
               'nearby:followup'}


def floor_bank(activity_id):
    category = BUNDLE_CATEGORY.get(activity_id)
    if category is None:
        return DEFAULT_FLOOR_BANK
    return FLOOR_BANK[category]


def floor_question(activity_id, used=(), artifact_visible=False):
    for question in floor_bank(activity_id):
        variant = VISIBLE_WORK_OPENERS.get(question)
        if question in used or (variant is not None and variant in used):
            continue
        if artifact_visible and variant is not None:
            return variant
        return question
    return None


def opener_slot_id(activity_id):
    return _QUESTION_ID[floor_bank(activity_id)[0]]


def quoted_child_text(text, limit):
    """Drop format characters and wrap in first-strong isolates, so a
    stray RLO or a Latin title in an RTL UI cannot reorder Jo's words.
    """
    text = ''.join(ch for ch in text if unicodedata.category(ch)
                   not in ('Cc', 'Cf', 'Zl', 'Zp'))
    return '\u2068%s\u2069' % clip_line(text, limit)


def titled_opener(label):
    """Speak with q=opener_slot_id(...) so it spends the opener slot."""
    return TITLED_OPENER % {'title': quoted_child_text(label, 60)}


def has_buddies(metadata):
    raw = metadata.get('buddies', '')
    if not raw:
        return False
    try:
        buddies = json.loads(raw)
    except (TypeError, ValueError):
        return False
    return isinstance(buddies, dict) and bool(buddies)


def together_question(metadata, used=()):
    if TOGETHER_OPENER in used or not has_buddies(metadata):
        return None
    return TOGETHER_OPENER


def nearby_nudge(used=()):
    if NEARBY_NUDGE in used or NEARBY_MIDFLOW in used:
        return None
    return NEARBY_NUDGE


def nearby_midflow(used=(), turns=(), roll=1.0):
    """The same move mid-talk. It spends the one nearby slot."""
    if NEARBY_NUDGE in used or NEARBY_MIDFLOW in used:
        return None
    replies = _child_replies(turns)
    if len(replies) < NEARBY_MIDFLOW_WARMUP:
        return None
    if roll >= NEARBY_MIDFLOW_CHANCE:
        return None
    return NEARBY_MIDFLOW


def nearby_followup(used=(), data=None, now=None):
    """The what-came-of-it opener, once and only after time away."""
    if NEARBY_FOLLOWUP in used:
        return None
    if NEARBY_NUDGE not in used and NEARBY_MIDFLOW not in used:
        return None
    if data is not None and not feed_forward_due(data, now):
        return None
    return NEARBY_FOLLOWUP


def parse_comments(raw):
    if not raw:
        return []
    try:
        comments = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(comments, list):
        return []
    return [c for c in comments if isinstance(c, dict)]


def _plain_text(text):
    return all(unicodedata.category(ch) not in ('Cc', 'Cf', 'Zl', 'Zp')
               for ch in text)


def compose_peer_question(comment):
    message = comment.get('message')
    if not isinstance(message, str):
        return None
    message = message.strip()
    if not turn_acceptable(message) or not _plain_text(message):
        return None
    who = comment.get('from')
    who = who.strip() if isinstance(who, str) else ''
    if len(who) > PEER_NAME_LIMIT or not _plain_text(who):
        who = ''
    if who:
        return PEER_QUESTION_OPENER % {'who': who, 'question': message}
    return PEER_QUESTION_ANON % {'question': message}


def peer_question(comments_raw, spoken=()):
    for comment in parse_comments(comments_raw):
        text = compose_peer_question(comment)
        if text is not None and text not in spoken:
            return text
    return None


def jo_texts(conversation, turns=()):
    """Every line Jo has said here. Peer questions are composed, not
    from a bank, so voiced-once needs the whole record.
    """
    texts = set()
    sessions = conversation.get('sessions', []) if conversation else []
    for session in sessions:
        for turn in session.get('turns', []):
            if turn.get('role') == ROLE_JO:
                texts.add(turn.get('text', ''))
    for turn in turns:
        if turn.get('role') == ROLE_JO:
            texts.add(turn.get('text', ''))
    return texts


def used_floor_questions(conversation, turns=()):
    used = set()
    sessions = conversation.get('sessions', []) if conversation else []
    for session in sessions:
        for turn in session.get('turns', []):
            _collect_used(turn, used)
    for turn in turns:
        _collect_used(turn, used)
    return used


def _collect_used(turn, used):
    """Mark a Jo turn's question used: by stable id first, which
    survives a locale switch, then by text as a defense for a
    record whose stamp went missing.
    """
    if turn.get('role') != ROLE_JO:
        return
    qid = turn.get('q')
    if isinstance(qid, str) and qid in _ID_QUESTION:
        used.add(_ID_QUESTION[qid])
    elif turn.get('text') in _ALL_FLOOR_QUESTIONS:
        used.add(turn['text'])


# A server is something a school opts into: until somebody ticks the
# switch, Jo asks from the floor and nothing leaves the laptop.
DEFAULT_ENABLED = False

DEFAULT_CONFIG_PATH = os.path.expanduser('~/.sugar/default/reflection.conf')

_CONFIG_SECTION = 'reflection'
_ENV_URL = 'SUGAR_AI_URL'
_ENV_API_KEY = 'SUGAR_AI_KEY'
_ENV_ENABLED = 'SUGAR_AI_REFLECTION_ENABLED'


def read_config(path=DEFAULT_CONFIG_PATH):
    """Read the reflection endpoint's url, api_key and enabled flag."""
    config = {'url': '', 'api_key': '', 'enabled': DEFAULT_ENABLED}

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read([path])
    except (configparser.Error, OSError, ValueError):
        logging.exception('Error reading reflection config %r', path)
    else:
        if parser.has_option(_CONFIG_SECTION, 'url'):
            config['url'] = parser.get(_CONFIG_SECTION, 'url')
        if parser.has_option(_CONFIG_SECTION, 'api_key'):
            config['api_key'] = parser.get(_CONFIG_SECTION, 'api_key')
        if parser.has_option(_CONFIG_SECTION, 'enabled'):
            try:
                config['enabled'] = parser.getboolean(_CONFIG_SECTION,
                                                      'enabled')
            except ValueError:
                logging.warning('Invalid enabled value in %r', path)

    if os.environ.get(_ENV_URL):
        config['url'] = os.environ[_ENV_URL]
    if os.environ.get(_ENV_API_KEY):
        config['api_key'] = os.environ[_ENV_API_KEY]
    if os.environ.get(_ENV_ENABLED):
        config['enabled'] = os.environ[_ENV_ENABLED].strip().lower() in \
            ('1', 'true', 'yes', 'on')

    return config


# Jo introduces itself once, on whichever surface the child meets
# first. That fact lives here, not in any entry's metadata.
STATE_PATH = os.path.expanduser('~/.sugar/default/reflection-state.json')

INTRO_LINE = _("I'm Jo. I like hearing about things people make. "
               "Can I ask you about this one?")
_register_question('intro', INTRO_LINE)


def _read_state(path=STATE_PATH):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def state_flag(key, path=STATE_PATH):
    return bool(_read_state(path).get(key))


def mark_state(key, path=STATE_PATH):
    """Record a once-ever moment. Best-effort; it may repeat."""
    data = _read_state(path)
    data[key] = True
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except OSError:
        logging.exception('Error writing reflection state %r', path)


READ_TIMEOUT = 30

# A reply is one question: past this the body is no shape we can use,
# and reading it on would spend the laptop's memory to throw it away.
_MAX_RESPONSE_BYTES = 64 * 1024

_PROBE_TIMEOUT = 5

_CHAT_PATH = '/reflect/chat'


class ReflectionOffline(Exception):
    """No network, or the reflect endpoint was unreachable."""


class ReflectionTimeout(Exception):
    """The reflect endpoint did not answer within READ_TIMEOUT."""


class ReflectionHTTPError(Exception):
    """The reflect endpoint answered with a non-2xx status."""

    def __init__(self, status, reason):
        Exception.__init__(self, '%s %s' % (status, reason))
        self.status = status
        self.reason = reason


class ReflectionBadResponse(Exception):
    """The response body was not the expected shape."""


def _probe_address(url):
    """Host and port to knock on for a configured url, or None when
    the url is not one we could post to at all.
    """
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port or (443 if parts.scheme == 'https' else 80)
    except ValueError:
        return None
    if not parts.hostname:
        return None
    return parts.hostname, port


def is_online(url):
    """Cheap knock on the configured server's own host. It answers
    reachable, never fast: a slow endpoint still passes here, which is
    what keeps an outage off READ_TIMEOUT.
    """
    address = _probe_address(url)
    if address is None:
        return False
    try:
        probe = socket.create_connection(address, timeout=_PROBE_TIMEOUT)
        probe.close()
        return True
    except OSError:
        return False


def _post_json(url, api_key, payload):
    """POST payload as JSON; raises only Reflection* errors. Connect
    and read share one socket timeout - plain urllib cannot split
    them - so is_online() keeps an outage off READ_TIMEOUT.
    """
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': api_key,
            },
            method='POST')
        with urllib.request.urlopen(request, timeout=READ_TIMEOUT) as resp:
            raw = resp.read(_MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise ReflectionHTTPError(e.code, e.reason)
    except socket.timeout:
        raise ReflectionTimeout()
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.timeout):
            raise ReflectionTimeout()
        raise ReflectionOffline()
    except ValueError:
        # An address with no scheme never gets a socket; unreachable
        # is the honest reading of it.
        raise ReflectionOffline()

    if len(raw) > _MAX_RESPONSE_BYTES:
        raise ReflectionBadResponse('response was over %d bytes'
                                    % _MAX_RESPONSE_BYTES)

    try:
        return json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        raise ReflectionBadResponse('response was not valid JSON')


STATUS_OK = 'ok'


# The wire carries the engine's own trace records (engine spec,
# section 1); the storage roles stay jo/child so metadata never
# depends on another project's naming. Server turns are stored with
# their typed fields and rebuild exactly; a floor question or a turn
# stored before the typed fields existed becomes a plain engine
# question - that is what the child saw, and the engine's budgets
# should count it.


def _engine_turn_record(turn):
    return {
        'type': 'engine_turn', 'by': 'engine',
        'kind': turn.get('kind', 'question'),
        'text': turn.get('text', ''),
        'flags': {
            'open': bool(turn.get('open')),
            'simplified': bool(turn.get('simplified')),
            'people_adjacent': _people_turn(turn),
        },
        'engagement': turn.get('engagement', 'engaged'),
    }


def _build_payload(title, description, activity_id, turns,
                   next_steps=None):
    """The whitelisted body for /reflect/chat - never the reflections
    blob, a preview, or the full metadata dict. A people question and
    its answers stay off the wire: they name someone in the room. The
    child can star such an answer into the description, so a starred
    one among these turns empties it here, and
    people_kept_in_description() covers the sessions already stored.
    """
    records = []
    people = False
    starred_people = False
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        role = turn.get('role')
        if role == ROLE_JO:
            people = _people_turn(turn) or bool(turn.get('local'))
        if people:
            if role == ROLE_CHILD and \
                    has_kept_line(description, turn.get('text', '')):
                starred_people = True
            continue
        if role == ROLE_JO:
            records.append(_engine_turn_record(turn))
        elif role == ROLE_CHILD:
            records.append({'type': 'child_turn', 'by': 'host',
                            'text': turn.get('text', '')})
    payload = {
        'title': title,
        'description': '' if starred_people else description,
        'activity_id': activity_id,
        'records': records,
    }
    if next_steps:
        payload['previous_next_steps'] = next_steps
    return payload


def _result(object_id, generation, status, turn=None,
            should_continue=True, end=None):
    result = {'object_id': object_id, 'generation': generation,
              'status': status, 'turn': turn,
              'should_continue': should_continue}
    if end is not None:
        result['end'] = end
    return result


# The nearby follow-up is only honest after real time away - no
# talk in the room can have happened a minute after Jo pointed at it.
FEED_FORWARD_GAP = 45 * 60


def latest_session_ts(data):
    ts = 0
    for session in data.get('sessions', []):
        try:
            ts = max(ts, int(session.get('ts', 0)))
        except (TypeError, ValueError):
            continue
    return ts


def feed_forward_due(data, now=None):
    if now is None:
        now = time.time()
    return (now - latest_session_ts(data)) > FEED_FORWARD_GAP


def count_turns(data):
    """Turns held by a parsed conversation, before any eviction."""
    return sum(len(s.get('turns', ())) for s in data.get('sessions', []))


def total_turns(raw):
    """How many turns a record holds. The write guard's yardstick: a
    talk only grows, so a shrinking count means a stale copy.
    """
    data = loads(raw)
    return sum(len(s.get('turns', []))
               for s in data.get('sessions', []))


def clip_line(text, limit):
    text = ' '.join(text.split())
    if len(text) <= limit:
        return text
    trimmed = text[:limit]
    if ' ' in trimmed:
        trimmed = trimmed.rsplit(' ', 1)[0]
    return trimmed + '…'


def hanging_question(data):
    sessions = data.get('sessions', [])
    if not sessions:
        return None
    turns = sessions[-1].get('turns', [])
    if not turns:
        return None
    last = turns[-1]
    if last.get('role') != ROLE_JO:
        return None
    text = (last.get('text') or '').strip()
    # A voiced peer question ends on its closing quote.
    if not text.rstrip('”').endswith(_QUESTION_ENDS):
        return None
    return text


def _child_replies(turns):
    return [turn.get('text', '') for turn in turns
            if turn.get('role') == ROLE_CHILD]


# Question terminators beyond ASCII: Arabic, fullwidth CJK, and the
# unambiguous Greek U+037E, Armenian and Ethiopic marks. The ASCII
# semicolon Greek actually types stays out - accepting it would read
# every clause break as a question.
_QUESTION_ENDS = ('?', '？', '؟', '\u037e', '\u055e', '\u1367')
_SENTENCE_MARKS = '.!?。！？؟\u0964\u06d4\u0589\u1362'


def turn_acceptable(text):
    """Whether a server turn is shaped like Jo: short, one question."""
    text = text.strip()
    if not text or len(text) > 140 or '\n' in text:
        return False
    if not text.endswith(_QUESTION_ENDS):
        return False
    if ':' in text or ' - ' in text or '•' in text:
        return False
    return sum(text.count(mark) for mark in _SENTENCE_MARKS) <= 2


def _floor_result(object_id, generation, activity_id, conversation, turns,
                  artifact_visible=False, opener=None):
    used = used_floor_questions(conversation, turns)
    # Mid-talk the "I can't see" preamble reads absurd, so a fallback
    # landing after the child has spoken takes the beside-work voice.
    in_talk = bool(_child_replies(turns))
    question = floor_question(activity_id, used, artifact_visible or in_talk)
    if question is not None and opener is not None and \
            not in_talk and \
            _QUESTION_ID.get(question) == opener.get('q'):
        # When the floor would open, the child's own words lead.
        turn = {'role': ROLE_JO, 'text': opener['text'],
                'q': opener['q']}
        if opener.get('local'):
            turn['local'] = True
        return _result(object_id, generation, STATUS_OK, turn=turn)
    if question is not None:
        midflow = nearby_midflow(used, turns, random.random())
        if midflow is not None:
            question = midflow
    if question is None:
        return _result(object_id, generation, STATUS_OK)
    return _result(object_id, generation, STATUS_OK,
                   turn={'role': ROLE_JO, 'text': question})


def request_turn(object_id, generation, activity_id, title, description,
                 turns, next_steps=None, config=None, conversation=None,
                 artifact_visible=False, opener=None):
    """Ask the reflect endpoint for Jo's next turn. The result carries
    (object_id, generation), so a caller with several requests in
    flight can place a late reply. Every road away lands on the floor.
    """
    if config is None:
        config = read_config()

    if not config['enabled'] or not config['api_key'] or not config['url']:
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)

    if not is_online(config['url']):
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)

    payload = _build_payload(title, description, activity_id, turns,
                             next_steps)
    url = config['url'].rstrip('/') + _CHAT_PATH

    try:
        body = _post_json(url, config['api_key'], payload)
    except ReflectionOffline:
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)
    except ReflectionTimeout:
        logging.warning('Reflection server timed out; floor answers')
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)
    except ReflectionHTTPError as e:
        logging.warning('Reflection server error %s %s; floor answers',
                        e.status, e.reason)
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)
    except ReflectionBadResponse as e:
        logging.warning('Reflection server reply unusable (%s); '
                        'floor answers', e)
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)

    record = body.get('record') if isinstance(body, dict) else None
    rtype = record.get('type') if isinstance(record, dict) else None

    if rtype == 'session_end':
        return _result(object_id, generation, STATUS_OK,
                       should_continue=False,
                       end={'reason': record.get('reason'),
                            'next_step': record.get('next_step'),
                            'asked': bool(record.get('asked'))})

    if rtype != 'engine_turn':
        logging.warning('Reflection server reply carried no turn; '
                        'floor answers')
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)

    if record.get('kind') == 'floor_request':
        # The engine could not produce a usable turn and says so in
        # the open; the local floor bank answers, same as an outage.
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)

    text = record.get('text')
    # The engine guards its own turns (single question, its own
    # length cap); this is a transport-sanity bound, not a second
    # shape judge - the old one is retired with the free-text wire.
    if not isinstance(text, str) or not text.strip() or \
            len(text) > 200 or '\n' in text:
        logging.warning('Reflection server turn unusable; '
                        'floor answers')
        return _floor_result(object_id, generation, activity_id,
                             conversation, turns, artifact_visible,
                             opener=opener)

    return _result(object_id, generation, STATUS_OK,
                   turn=_turn_from_record(record),
                   should_continue=True)


def _turn_from_record(record):
    """A stored jo turn from one engine_turn record. The typed fields
    ride the stored turn so the next request rebuilds this record
    exactly - never re-derived from the text.
    """
    turn = {'role': ROLE_JO, 'text': record['text'].strip(),
            'kind': record.get('kind', 'question'),
            'engagement': record.get('engagement', 'engaged')}
    flags = record.get('flags') or {}
    for name in ('open', 'simplified', 'people_adjacent'):
        if flags.get(name):
            turn[name] = True
    return turn
