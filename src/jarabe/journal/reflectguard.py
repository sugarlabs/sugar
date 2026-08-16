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

"""Shell-memory guard for the reflections record.

The datastore's update() prunes any metadata key a writer does not
send, and a running activity saves with the metadata it loaded at
resume - erasing a moment, snapshot or session written here
mid-session. The last written state is held in shell memory and put
back the instant an update wipes it from the entry.

The guard retires if the datastore ever merges updates instead of
deleting omitted keys.
"""

import logging
import time

from gi.repository import GLib

from jarabe.journal import model
from jarabe.journal import reflection


SNAP_KEY = reflection.SNAP_KEY_PREFIX + '%d'

# Past a couple dozen, the oldest moment is dropped with its snapshot key.
MAX_MOMENTS = 24

# How long a write's expected model.updated echo stays credited.
# Past this, a stale echo could swallow the next real clobber.
ECHO_TTL = 30


class ReflectionsGuard(object):
    def __init__(self):
        self._entries = {}
        self._warned_sidless = False
        model.updated.connect(self.__updated_cb)

    def note_moments(self, uid, moments, snaps):
        """The canonical post-write state for an entry's moments and
        their snapshots. REPLACES what was held, not an append - a
        moment the cap evicted is never fought back in.
        """
        self.__replace(uid, moments=moments, snaps=snaps)

    def note_sessions(self, uid, sessions):
        """The canonical post-write state for an entry's sessions. A
        session with no 'sid' can't be recognised later, so it's never held.
        """
        self.__replace(uid, sessions=sessions)

    def __replace(self, uid, moments=None, snaps=None, sessions=None):
        held = self._entries.setdefault(uid, {
            'moments': [], 'snaps': {}, 'sessions': [],
            'echoes': 0, 'echo_born': 0.0, 'pending': False,
        })
        if moments is not None:
            held['moments'] = list(moments)
        if snaps is not None:
            held['snaps'] = dict(snaps)
        if sessions is not None:
            held['sessions'] = self.__hold_sessions(sessions)
        held['echoes'] += 1
        held['echo_born'] = time.monotonic()

    def __hold_sessions(self, sessions):
        held = []
        for session in sessions:
            if not session.get('sid'):
                if not self._warned_sidless:
                    logging.warning(
                        'reflectguard: session without sid cannot be '
                        'recognised later, dropped from the hold')
                    self._warned_sidless = True
                continue
            copy = dict(session)
            if 'turns' in copy:
                copy['turns'] = list(copy['turns'])
            held.append(copy)
        return held

    def __updated_cb(self, sender, object_id=None, **kwargs):
        held = self._entries.get(object_id)
        if held is None:
            return
        if held['echoes'] > 0:
            if time.monotonic() - held['echo_born'] <= ECHO_TTL:
                held['echoes'] -= 1
                return
            held['echoes'] = 0
        if held['pending']:
            return
        held['pending'] = True
        GLib.idle_add(self.__remerge, object_id)

    def __remerge(self, uid):
        held = self._entries.get(uid)
        if held is None:
            return False
        held['pending'] = False
        try:
            metadata = model.get(uid)
        except Exception:
            logging.exception('reflectguard: could not re-read %r', uid)
            return False
        data = reflection.loads(metadata.get('reflections', ''))
        current = data.get('moments', [])
        lost = [m for m in held['moments'] if m not in current]
        lost_snaps = [k for k in held['snaps'] if k not in metadata]
        lost_sessions = [
            s for s in held['sessions']
            if reflection.find_session(data, s.get('sid')) is None]
        if not lost and not lost_snaps and not lost_sessions:
            return False

        merged = sorted(current + lost, key=lambda m: m.get('ts', 0))
        evicted = []
        while len(merged) > MAX_MOMENTS:
            evicted.append(merged.pop(0).get('snap_seq'))
        data['moments'] = merged
        seqs = [m.get('snap_seq', 0) + 1 for m in merged]
        data['moment_seq'] = max([data.get('moment_seq', 0)] + seqs)

        for session in lost_sessions:
            data = reflection.merge_session(data, session)
        if lost_sessions:
            data['sessions'] = sorted(
                data.get('sessions', []), key=lambda s: s.get('ts', 0))

        metadata['reflections'] = reflection.dumps(data)
        for key in lost_snaps:
            metadata[key] = held['snaps'][key]
        for seq in evicted:
            if seq is not None:
                metadata.pop(SNAP_KEY % seq, None)
        try:
            model.write(metadata, update_mtime=False)
        except Exception:
            logging.exception(
                'reflectguard: could not restore state on %r', uid)
            return False

        # dumps() may itself have evicted a session past the byte
        # budget, so hold what actually landed, not what this function
        # merged (or dropped sessions get fought back in forever).
        # Re-holding the whole disk list would adopt every sid-bearing
        # session, resurrecting ones legitimately removed.
        written = reflection.loads(metadata['reflections'])
        kept_snaps = {
            k: v for k, v in held['snaps'].items() if k in metadata}
        held_sids = {s['sid'] for s in held['sessions']}
        kept_sessions = [s for s in written['sessions']
                         if s.get('sid') in held_sids]
        self.__replace(uid, moments=written['moments'], snaps=kept_snaps,
                       sessions=kept_sessions)
        return False


_guard = None


def get_guard():
    global _guard
    if _guard is None:
        _guard = ReflectionsGuard()
    return _guard
