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
import os
import sys

import time

import unittest
from unittest import mock

# gi is an apt-installed system package, not something `uvx pytest`'s
# own managed interpreter has -- skip rather than error when it isn't
# importable.
#
# Gtk/Gdk must be pinned to 3.0 before jarabe.journal.reflectguard pulls
# them in bare (via jarabe.journal.model), or PyGObject resolves Gdk to
# 4.0 first and the later Gtk 3.0 import conflicts with it.
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal import model  # noqa: E402
from jarabe.journal import momentcard  # noqa: E402
from jarabe.journal import reflectguard  # noqa: E402
from jarabe.journal import reflection  # noqa: E402


def _run_idle(test):
    # Stand in for the real GLib main loop: run the idle callback
    # __updated_cb schedules immediately, synchronously.
    patcher = mock.patch.object(
        reflectguard.GLib, 'idle_add', lambda func, *args: func(*args))
    patcher.start()
    test.addCleanup(patcher.stop)


def _forbid_model_access(test):
    def boom(*args, **kwargs):
        raise AssertionError('model touched when it should not be')
    for target, attr in (
            (model, 'get'),
            (model, 'write'),
            (reflectguard.GLib, 'idle_add')):
        patcher = mock.patch.object(target, attr, boom)
        patcher.start()
        test.addCleanup(patcher.stop)


# --- note_moments: replaces, never merges ---

class TestNoteMomentsReplacesHeldState(unittest.TestCase):

    def test_note_moments_replaces_held_state_rather_than_merging(self):
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(
            'uid-1', [{'caption': 'first', 'snap_seq': 0}],
            {'moment-snap-0': 'AAA'})
        guard.note_moments(
            'uid-1', [{'caption': 'second', 'snap_seq': 1}],
            {'moment-snap-1': 'BBB'})

        held = guard._entries['uid-1']
        self.assertEqual(
            held['moments'], [{'caption': 'second', 'snap_seq': 1}])
        self.assertEqual(held['snaps'], {'moment-snap-1': 'BBB'})
        self.assertEqual(held['echoes'], 2)


# --- the echo counter: our own write's Updated signal is swallowed ---

class TestEchoCounterSwallowsOwnUpdate(unittest.TestCase):

    def test_updated_signal_right_after_note_moments_is_swallowed_as_echo(
            self):
        _forbid_model_access(self)
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(
            'uid-echo', [{'caption': 'x', 'ts': 1, 'snap_seq': 0}], {})

        model.updated.send(None, object_id='uid-echo')

        self.assertEqual(guard._entries['uid-echo']['echoes'], 0)

    def test_stale_echo_expires_and_the_update_triggers_a_remerge(self):
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments('uid-stale', [{'snap_seq': 1}], {})
        scheduled = []
        patcher = mock.patch.object(
            reflectguard.GLib, 'idle_add',
            lambda cb, *a: scheduled.append((cb, a)))
        patcher.start()
        self.addCleanup(patcher.stop)
        real_monotonic = time.monotonic
        patcher = mock.patch.object(
            reflectguard.time, 'monotonic',
            lambda: real_monotonic() + reflectguard.ECHO_TTL + 1)
        patcher.start()
        self.addCleanup(patcher.stop)
        model.updated.send(None, object_id='uid-stale')
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(guard._entries['uid-stale']['echoes'], 0)

    def test_updated_signal_for_untracked_uid_is_ignored(self):
        _forbid_model_access(self)
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments('held-uid', [], {})

        model.updated.send(None, object_id='never-held')

        self.assertEqual(guard._entries['held-uid']['echoes'], 1)


# --- the re-merge: restore what a clobbering write erased ---

class TestRemergeRestoresClobberedWrite(unittest.TestCase):

    def test_remerge_restores_moments_and_snaps_lost_to_a_clobbering_write(
            self):
        _run_idle(self)
        uid = 'uid-remerge'
        moment = {'caption': 'a dragon wing', 'mark': 'proud', 'ts': 100,
                  'snap_seq': 0}
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(
            uid, [moment], {reflectguard.SNAP_KEY % 0: 'AAA=='})
        # our own write's echo arrives first and must not be treated as a
        # clobber
        model.updated.send(None, object_id=uid)

        written = []
        # the activity resumed and saved with metadata that never mentions
        # our moment or its snapshot -- a real clobbering write
        patcher = mock.patch.object(model, 'get', lambda object_id: {})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            model, 'write',
            lambda metadata, **kwargs: written.append(dict(metadata)))
        patcher.start()
        self.addCleanup(patcher.stop)

        model.updated.send(None, object_id=uid)

        self.assertEqual(len(written), 1)
        data = reflection.loads(written[0]['reflections'])
        self.assertEqual(data['moments'], [moment])
        self.assertEqual(written[0][reflectguard.SNAP_KEY % 0], 'AAA==')

    def test_remerge_noop_when_nothing_was_actually_lost(self):
        _run_idle(self)
        uid = 'uid-noop'
        moment = {'caption': 'x', 'ts': 1, 'snap_seq': 0}
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(uid, [moment], {reflectguard.SNAP_KEY % 0: 'AAA'})
        model.updated.send(None, object_id=uid)  # swallow our own echo

        def boom(*args, **kwargs):
            raise AssertionError('write touched when nothing was lost')
        intact = {
            'reflections': reflection.dumps({'moments': [moment]}),
            reflectguard.SNAP_KEY % 0: 'AAA',
        }
        patcher = mock.patch.object(model, 'get', lambda object_id: intact)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(model, 'write', boom)
        patcher.start()
        self.addCleanup(patcher.stop)

        # a genuine but unrelated Updated signal -- neither the moment nor
        # its snapshot is actually missing from the datastore's copy
        model.updated.send(None, object_id=uid)

        self.assertIs(guard._entries[uid]['pending'], False)

    def test_remerge_evicts_oldest_moments_past_the_cap(self):
        _run_idle(self)
        uid = 'uid-evict'
        cap = reflectguard.MAX_MOMENTS
        moments = [
            {'caption': 'm%d' % i, 'ts': i, 'snap_seq': i}
            for i in range(cap + 1)]
        snaps = {reflectguard.SNAP_KEY % i: 'data%d' % i
                 for i in range(cap + 1)}

        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(uid, moments, snaps)
        model.updated.send(None, object_id=uid)  # swallow our own echo

        written = []
        # the moments never reached the datastore at all; the snapshots did
        metadata = dict(snaps)
        patcher = mock.patch.object(model, 'get', lambda object_id: metadata)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            model, 'write',
            lambda md, **kwargs: written.append(dict(md)))
        patcher.start()
        self.addCleanup(patcher.stop)

        model.updated.send(None, object_id=uid)

        self.assertEqual(len(written), 1)
        data = reflection.loads(written[0]['reflections'])
        self.assertEqual(len(data['moments']), cap)
        # the oldest (ts=0 / snap_seq=0) is the one the cap dropped
        self.assertEqual(
            [m['snap_seq'] for m in data['moments']], list(range(1, cap + 1)))
        self.assertNotIn(reflectguard.SNAP_KEY % 0, written[0])
        self.assertIn(reflectguard.SNAP_KEY % 1, written[0])


# --- the echo counter also guards the re-merge's own follow-up write ---

class TestRemergeOwnWriteEchoSwallowed(unittest.TestCase):

    def test_remerges_own_write_echo_is_swallowed_next_time(self):
        _run_idle(self)
        uid = 'uid-loop-guard'
        moment = {'caption': 'x', 'mark': 'wonder', 'ts': 1, 'snap_seq': 0}
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(uid, [moment], {})
        model.updated.send(None, object_id=uid)  # swallow our own echo

        written = []
        patcher = mock.patch.object(model, 'get', lambda object_id: {})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            model, 'write',
            lambda md, **kwargs: written.append(dict(md)))
        patcher.start()
        self.addCleanup(patcher.stop)

        model.updated.send(None, object_id=uid)  # the real clobber -> remerge
        self.assertEqual(len(written), 1)

        # the Updated signal the remerge's own model.write() just emitted is
        # the next one in -- it must be swallowed, not chased as another
        # clobber, or every remerge would retrigger itself forever.
        model.updated.send(None, object_id=uid)
        self.assertEqual(len(written), 1)


# --- the pending flag: only one re-merge in flight per entry ---

class TestPendingFlagLimitsInFlightRemerge(unittest.TestCase):

    def test_second_updated_signal_while_pending_does_not_reschedule(self):
        scheduled = []
        patcher = mock.patch.object(
            reflectguard.GLib, 'idle_add',
            lambda func, *args: scheduled.append((func, args)))
        patcher.start()
        self.addCleanup(patcher.stop)
        uid = 'uid-pending'
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(uid, [{'caption': 'x', 'ts': 1, 'snap_seq': 0}], {})
        model.updated.send(None, object_id=uid)  # swallow our own echo

        model.updated.send(None, object_id=uid)  # real signal: schedules once
        # a second real signal, arriving before the idle callback above runs
        model.updated.send(None, object_id=uid)

        self.assertEqual(len(scheduled), 1)
        self.assertIs(guard._entries[uid]['pending'], True)


# --- get_guard(): one guard for the whole shell ---

class TestGetGuardSingleton(unittest.TestCase):

    def test_get_guard_returns_the_same_instance_every_time(self):
        self.assertIs(reflectguard.get_guard(), reflectguard.get_guard())


# --- note_sessions: sid required to be held at all ---

class TestNoteSessionsRequiresSid(unittest.TestCase):

    def test_note_sessions_drops_sessions_without_a_sid_and_warns_once(self):
        guard = reflectguard.ReflectionsGuard()
        kept = {'sid': 'sid-a', 'ts': 1, 'turns': [{'role': 'child',
                                                    'text': 'hi'}]}
        with self.assertLogs(level=logging.WARNING) as cm:
            guard.note_sessions('uid-a', [kept, {'ts': 2, 'turns': []}])
            guard.note_sessions('uid-b', [{'ts': 3, 'turns': []}])

        held_a = guard._entries['uid-a']['sessions']
        self.assertEqual(len(held_a), 1)
        self.assertEqual(held_a[0]['sid'], 'sid-a')
        self.assertEqual(guard._entries['uid-b']['sessions'], [])
        # one warning for the whole guard's lifetime, not one per offence
        sidless_warnings = [r for r in cm.records if 'sid' in r.getMessage()]
        self.assertEqual(len(sidless_warnings), 1)

        # a deep-ish copy: mutating the caller's turns afterwards must not
        # reach into what the guard is holding
        kept['turns'].append({'role': 'child', 'text': 'later'})
        self.assertEqual(len(held_a[0]['turns']), 1)


# --- the re-merge: restore a session lost to a clobbering write ---

class TestRemergeRestoresLostSession(unittest.TestCase):

    def test_remerge_restores_a_lost_session_and_keeps_the_fresh_blobs_content(
            self):
        _run_idle(self)
        uid = 'uid-session-remerge'
        lost = {
            'sid': 'sid-lost', 'ts': 100,
            'turns': [{'role': 'child', 'text': 'a dragon wing'}]}
        guard = reflectguard.ReflectionsGuard()
        guard.note_sessions(uid, [lost])
        model.updated.send(None, object_id=uid)  # swallow our own echo

        fresh_session = {
            'sid': 'sid-fresh', 'ts': 200,
            'turns': [{'role': 'child', 'text': 'something else'}]}
        fresh_reflections = reflection.dumps(
            {'version': 1, 'sessions': [fresh_session]})
        written = []
        patcher = mock.patch.object(
            model, 'get',
            lambda object_id: {'reflections': fresh_reflections,
                               'title': 'Untitled'})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            model, 'write',
            lambda metadata, **kwargs: written.append(dict(metadata)))
        patcher.start()
        self.addCleanup(patcher.stop)

        model.updated.send(None, object_id=uid)

        self.assertEqual(len(written), 1)
        data = reflection.loads(written[0]['reflections'])
        self.assertEqual(reflection.find_session(data, 'sid-lost'), lost)
        self.assertEqual(
            reflection.find_session(data, 'sid-fresh'), fresh_session)
        # sessions come back in chronological order after the merge
        self.assertEqual(
            [s['sid'] for s in data['sessions']], ['sid-lost', 'sid-fresh'])
        # the fresh blob's other metadata is untouched by the restore
        self.assertEqual(written[0]['title'], 'Untitled')


# --- the re-merge: what dumps() itself evicts must not loop forever ---

class TestRemergeRespectsDumpsEvictionBound(unittest.TestCase):

    def test_remerge_holds_what_dumps_actually_wrote_when_it_evicts_a_session(
            self):
        _run_idle(self)
        patcher = mock.patch.object(reflection, 'MAX_REFLECTIONS_BYTES', 400)
        patcher.start()
        self.addCleanup(patcher.stop)
        uid = 'uid-dumps-bound'
        lost = {
            'sid': 'sid-lost', 'ts': 1,
            'turns': [{'role': 'child', 'text': 'x' * 200}]}
        guard = reflectguard.ReflectionsGuard()
        guard.note_sessions(uid, [lost])
        model.updated.send(None, object_id=uid)  # swallow our own echo

        newer = {
            'sid': 'sid-newer', 'ts': 2,
            'turns': [{'role': 'child', 'text': 'y' * 200}]}
        fresh_reflections = reflection.dumps(
            {'version': 1, 'sessions': [newer]})
        written = []
        patcher = mock.patch.object(
            model, 'get', lambda object_id: {'reflections': fresh_reflections})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            model, 'write',
            lambda metadata, **kwargs: written.append(dict(metadata)))
        patcher.start()
        self.addCleanup(patcher.stop)

        model.updated.send(None, object_id=uid)

        self.assertEqual(len(written), 1)
        data = reflection.loads(written[0]['reflections'])
        # the tiny budget leaves room for only the newest session -- the
        # just-restored one is the one dumps() drops right back out
        self.assertEqual([s['sid'] for s in data['sessions']], ['sid-newer'])

        # dumps() dropped the restored session past the tiny budget, so
        # the guard stops holding it -- and it never adopts sid-newer,
        # which nobody asked it to guard in the first place
        self.assertEqual(guard._entries[uid]['sessions'], [])

        # the remerge's own write emitted its own Updated -- swallowed as
        # an echo -- and a genuine follow-up after that must not re-trigger
        # a write, since held state and disk now agree
        model.updated.send(None, object_id=uid)  # the write's own echo
        model.updated.send(None, object_id=uid)  # a real, unrelated signal
        self.assertEqual(len(written), 1)


# --- the shared echo counter across a mixed moments+sessions remerge ---

class TestMixedMomentsAndSessionsEchoSuppression(unittest.TestCase):

    def test_echo_suppression_holds_across_a_mixed_moments_and_sessions_write(
            self):
        _run_idle(self)
        uid = 'uid-mixed'
        moment = {'caption': 'x', 'mark': 'wonder', 'ts': 1, 'snap_seq': 0}
        session = {
            'sid': 'sid-x', 'ts': 1,
            'turns': [{'role': 'child', 'text': 'hi'}]}
        guard = reflectguard.ReflectionsGuard()
        guard.note_moments(uid, [moment], {})
        guard.note_sessions(uid, [session])
        # both prior writes' echoes must be swallowed before the clobber
        model.updated.send(None, object_id=uid)
        model.updated.send(None, object_id=uid)

        written = []
        patcher = mock.patch.object(model, 'get', lambda object_id: {})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            model, 'write',
            lambda md, **kwargs: written.append(dict(md)))
        patcher.start()
        self.addCleanup(patcher.stop)

        model.updated.send(None, object_id=uid)  # the real clobber -> remerge
        self.assertEqual(len(written), 1)
        data = reflection.loads(written[0]['reflections'])
        self.assertEqual(data['moments'], [moment])
        self.assertIsNotNone(reflection.find_session(data, 'sid-x'))

        # one physical write touching both moments and sessions must cost
        # exactly one echo, not two
        self.assertEqual(guard._entries[uid]['echoes'], 1)

        model.updated.send(None, object_id=uid)  # the write's own echo
        self.assertEqual(guard._entries[uid]['echoes'], 0)
        self.assertEqual(len(written), 1)


# --- guarding against a naming drift between the two modules under test ---

class TestModuleNamingDrift(unittest.TestCase):

    def test_momentcard_still_uses_reflectguards_snap_key_and_cap(self):
        self.assertEqual(momentcard.SNAP_KEY, reflectguard.SNAP_KEY)
        self.assertEqual(momentcard._MAX_MOMENTS, reflectguard.MAX_MOMENTS)


if __name__ == '__main__':
    unittest.main()
