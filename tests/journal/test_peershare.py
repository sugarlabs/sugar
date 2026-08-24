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

import base64
import json
import logging
import unittest
from functools import partial
from unittest.mock import Mock, patch

from jarabe.journal import model
from jarabe.journal import peershare
from jarabe.journal import reflectguard
from jarabe.model import neighborhood

CONNECTION = peershare.CONNECTION
REQUESTS = neighborhood.CONNECTION_INTERFACE_REQUESTS
BUDDY_INFO = neighborhood.CONNECTION_INTERFACE_BUDDY_INFO
ACTIVITY_PROPERTIES = \
    neighborhood.CONNECTION_INTERFACE_ACTIVITY_PROPERTIES


class TestParseEntryTags(unittest.TestCase):

    def test_all_three_tokens(self):
        self.assertEqual(
            neighborhood.parse_entry_tags(
                'abc org.laptop.RocketActivity image/png'),
            ('abc', 'org.laptop.RocketActivity', 'image/png'))

    def test_a_mime_without_a_bundle_is_told_apart(self):
        self.assertEqual(neighborhood.parse_entry_tags('abc image/png'),
                         ('abc', '', 'image/png'))

    def test_empty(self):
        self.assertEqual(neighborhood.parse_entry_tags(''), ('', '', ''))
        self.assertEqual(neighborhood.parse_entry_tags(None), ('', '', ''))


class TestEntryAdvert(unittest.TestCase):

    def test_activity_id_is_stable_and_room_shaped(self):
        uid = '1b4c282a-f20a-41ec-9805-2ea9b7124948'
        first = peershare.entry_activity_id(uid)
        self.assertEqual(first, peershare.entry_activity_id(uid))
        self.assertEqual(len(first), 40)
        int(first, 16)
        self.assertNotEqual(first, peershare.entry_activity_id('other'))

    def test_properties_carry_the_entry_not_the_talk(self):
        metadata = {'uid': 'abc', 'title': 'my rockit',
                    'reflections': '{"sessions": []}',
                    'description': 'private words'}
        properties = peershare.entry_properties(metadata,
                                                color='#FF2B34,#005FE4')
        self.assertEqual(properties['type'],
                         neighborhood.JOURNAL_ENTRY_TYPE)
        self.assertEqual(properties['name'], 'my rockit')
        self.assertEqual(properties['tags'], 'abc')
        self.assertFalse(properties['private'])
        # The connection manager rejects keys outside the stock set.
        self.assertEqual(sorted(properties),
                         ['color', 'name', 'private', 'tags', 'type'])
        for value in properties.values():
            self.assertNotIn('sessions', str(value))
            self.assertNotIn('private words', str(value))

    def test_properties_carry_uid_and_bundle_when_activity_present(self):
        metadata = {'uid': 'abc', 'title': 'my rockit',
                    'activity': 'org.laptop.RocketActivity'}
        properties = peershare.entry_properties(metadata,
                                                color='#FF2B34,#005FE4')
        self.assertEqual(properties['tags'], 'abc org.laptop.RocketActivity')

    def test_properties_carry_the_mime_type_too(self):
        metadata = {'uid': 'abc', 'title': 'my rockit',
                    'activity': 'org.laptop.RocketActivity',
                    'mime_type': 'image/png'}
        properties = peershare.entry_properties(metadata,
                                                color='#FF2B34,#005FE4')
        self.assertEqual(properties['tags'],
                         'abc org.laptop.RocketActivity image/png')

    def test_a_slashless_mime_type_stays_home(self):
        # Without its '/' the reader could not tell it from a bundle.
        metadata = {'uid': 'abc', 'mime_type': 'weird'}
        properties = peershare.entry_properties(metadata,
                                                color='#FF2B34,#005FE4')
        self.assertEqual(properties['tags'], 'abc')

    def test_properties_survive_a_bare_record(self):
        properties = peershare.entry_properties({}, color='#000,#FFF')
        self.assertEqual(properties['name'], '')
        self.assertEqual(properties['tags'], '')


class TestWithoutActivity(unittest.TestCase):

    def test_filters_only_the_named_activity(self):
        activities = [('write-1', 5), ('entry-1', 9), ('paint-1', 11)]
        remaining = peershare.without_activity(activities, 'entry-1')
        self.assertEqual(remaining, [('write-1', 5), ('paint-1', 11)])

    def test_absent_activity_id_leaves_list_untouched(self):
        activities = [('write-1', 5)]
        self.assertEqual(peershare.without_activity(activities, 'nope'),
                         activities)


class _FakeNeighborhood(object):

    def __init__(self, activity):
        self._activities = {'a1': activity}
        self.emitted = []

    def emit(self, signal, *args):
        self.emitted.append((signal, args))


class TestActivitiesBeforeContact(unittest.TestCase):
    """ActivitiesChanged racing ahead of the contact round trip."""

    def _bare_account(self):
        account = neighborhood._Account.__new__(neighborhood._Account)
        account._self_handle = 1
        account._buddy_handles = {}
        account._activity_handles = {}
        account._activities_per_buddy = {}
        account._buddies_per_activity = {}
        account._connection = _fake_conn()
        account._connection[ACTIVITY_PROPERTIES].replies['GetProperties'] = \
            ({},)
        account._connection[BUDDY_INFO].replies['GetCurrentActivity'] = \
            ('', 0)
        emitted = []
        account.emit = lambda *args: emitted.append(args)
        return account, emitted

    def test_a_signal_ahead_of_the_contact_is_dropped_whole(self):
        # partial processing would record the pairing, then crash on
        # the missing name, leaving nothing for the retry to do
        account, emitted = self._bare_account()
        account._update_buddy_activities(2, [('act-1', 7)])
        self.assertEqual(emitted, [])
        self.assertNotIn(2, account._activities_per_buddy)

    def test_the_requery_after_the_contact_lands_attaches(self):
        account, emitted = self._bare_account()
        account._update_buddy_activities(2, [('act-1', 7)])
        account._buddy_handles[2] = 'contact-2'
        account._update_buddy_activities(2, [('act-1', 7)])
        self.assertIn(('buddy-joined-activity', 'contact-2', 'act-1'),
                      emitted)


class TestUpdateSharedEntry(unittest.TestCase):

    def test_missing_color_does_not_crash(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        neighborhood.Neighborhood._update_shared_entry(
            fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                         'name': 'no color here'})
        self.assertEqual(activity.get_name(), 'no color here')
        self.assertIsNone(activity.get_color())

    def test_missing_name_defaults_to_empty(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        neighborhood.Neighborhood._update_shared_entry(
            fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                         'color': '#FF2B34,#005FE4'})
        self.assertEqual(activity.get_name(), '')

    def test_a_full_record_still_updates_both(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        neighborhood.Neighborhood._update_shared_entry(
            fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                         'name': 'my rockit',
                         'color': '#FF2B34,#005FE4',
                         'uid': 'abc'})
        self.assertEqual(activity.get_name(), 'my rockit')
        self.assertEqual(activity.get_color().to_string(),
                         '#FF2B34,#005FE4')
        self.assertEqual(activity.entry_uid, 'abc')
        self.assertEqual(fake.emitted, [('activity-added', (activity,))])

    def test_the_mime_type_lands_on_the_model(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        neighborhood.Neighborhood._update_shared_entry(
            fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                         'name': 'my rockit',
                         'tags': 'abc image/png'})
        self.assertEqual(activity.entry_mime, 'image/png')

    def test_a_signal_without_tags_keeps_the_mime_type(self):
        activity = neighborhood.ActivityModel('a1', 7)
        activity.entry_mime = 'image/png'
        fake = _FakeNeighborhood(activity)
        neighborhood.Neighborhood._update_shared_entry(
            fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                         'name': 'renamed'})
        self.assertEqual(activity.entry_mime, 'image/png')

    def test_no_bundle_token_leaves_bundle_unset(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        neighborhood.Neighborhood._update_shared_entry(
            fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                         'name': 'my rockit', 'tags': 'abc'})
        self.assertIsNone(activity.get_bundle())

    def test_bundle_token_resolves_through_the_registry(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        bundle = object()
        registry = Mock()
        registry.get_bundle.return_value = bundle
        with patch('jarabe.model.neighborhood.bundleregistry.get_registry',
                   return_value=registry):
            neighborhood.Neighborhood._update_shared_entry(
                fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                             'name': 'my rockit',
                             'tags': 'abc org.laptop.RocketActivity'})
        registry.get_bundle.assert_called_once_with(
            'org.laptop.RocketActivity')
        self.assertIs(activity.get_bundle(), bundle)

    def test_a_partial_signal_does_not_take_the_bundle_away(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        bundle = object()
        registry = Mock()
        registry.get_bundle.return_value = bundle
        with patch('jarabe.model.neighborhood.bundleregistry.get_registry',
                   return_value=registry):
            neighborhood.Neighborhood._update_shared_entry(
                fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                             'name': 'my rockit',
                             'tags': 'abc org.laptop.RocketActivity'})
        neighborhood.Neighborhood._update_shared_entry(
            fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                         'name': 'my rockit renamed'})
        self.assertIs(activity.get_bundle(), bundle)

    def test_unknown_bundle_id_falls_back_to_none(self):
        activity = neighborhood.ActivityModel('a1', 7)
        fake = _FakeNeighborhood(activity)
        registry = Mock()
        registry.get_bundle.return_value = None
        with patch('jarabe.model.neighborhood.bundleregistry.get_registry',
                   return_value=registry):
            neighborhood.Neighborhood._update_shared_entry(
                fake, 'a1', {'type': neighborhood.JOURNAL_ENTRY_TYPE,
                             'name': 'my rockit',
                             'tags': 'abc org.laptop.MissingActivity'})
        self.assertIsNone(activity.get_bundle())


class TestEntryOwner(unittest.TestCase):

    def test_the_first_buddy_attached_stays_the_owner(self):
        activity = neighborhood.ActivityModel('a1', 7)
        self.assertIsNone(activity.get_owner())
        author = Mock()
        visitor = Mock()
        activity.add_buddy(author)
        activity.add_buddy(visitor)
        self.assertIs(activity.get_owner(), author)

    def test_a_visitor_leaving_does_not_change_the_owner(self):
        activity = neighborhood.ActivityModel('a1', 7)
        author = Mock()
        visitor = Mock()
        activity.add_buddy(author)
        activity.add_buddy(visitor)
        activity.remove_buddy(visitor)
        self.assertIs(activity.get_owner(), author)

    def test_the_owner_leaving_leaves_the_entry_unattributed(self):
        activity = neighborhood.ActivityModel('a1', 7)
        author = Mock()
        visitor = Mock()
        latecomer = Mock()
        activity.add_buddy(author)
        activity.add_buddy(visitor)
        activity.remove_buddy(author)
        self.assertIsNone(activity.get_owner())
        # a later buddy joining does not fill the empty owner slot
        activity.add_buddy(latecomer)
        self.assertIsNone(activity.get_owner())


class _FakeAccount(object):

    def __init__(self, object_path='/salut', conn_ready=True):
        self.object_path = object_path
        self.conn_ready = conn_ready


class _FakeLinkLocal(object):

    def __init__(self, account):
        self._link_local_account = account


class TestLinkLocalHandle(unittest.TestCase):
    """Only salut's own buddies have a handle salut answers to."""

    def _handle(self, buddy, account=None):
        if account is None:
            account = _FakeAccount()
        return neighborhood.Neighborhood.get_link_local_handle(
            _FakeLinkLocal(account), buddy)

    def _buddy(self, account='/salut', handle=9):
        return neighborhood.BuddyModel(nick='Ana', account=account,
                                       contact_id='ana@laptop',
                                       handle=handle)

    def test_a_friend_on_this_connection_is_known_by_handle(self):
        self.assertEqual(self._handle(self._buddy()), 9)

    def test_a_friend_from_the_jabber_account_is_not(self):
        # this handle was assigned by a different connection and
        # refers to someone else on this one
        self.assertIsNone(self._handle(self._buddy(account='/jabber')))

    def test_a_friend_without_a_handle_yet_is_not(self):
        self.assertIsNone(self._handle(self._buddy(handle=None)))

    def test_we_are_not_our_own_friend(self):
        owner = Mock()
        owner.is_owner.return_value = True
        self.assertIsNone(self._handle(owner))

    def test_a_connection_that_is_not_ready_names_nobody(self):
        self.assertIsNone(
            self._handle(self._buddy(),
                         account=_FakeAccount(conn_ready=False)))

    def test_no_account_and_no_friend_are_survivable(self):
        no_account = neighborhood.Neighborhood.get_link_local_handle(
            _FakeLinkLocal(None), self._buddy())
        self.assertIsNone(no_account)
        self.assertIsNone(self._handle(None))


class TestBuildEntryPayload(unittest.TestCase):

    def _payload(self, metadata):
        return peershare.build_entry_payload(metadata,
                                             color='#FF2B34,#005FE4')

    def test_the_talk_never_travels(self):
        payload = self._payload({
            'uid': 'abc', 'title': 'my rockit',
            'description': 'i made a rocket',
            'reflections': '{"sessions": [{"turns": ["secret"]}]}',
            'next_steps': 'paint the fins',
            'moment-snap-1': 'AAAA',
            'shared': '1'})
        for key in ('reflections', 'next_steps', 'moment-snap-1', 'shared'):
            self.assertNotIn(key, payload)
        line = peershare.encode_payload(payload)
        for word in ('secret', 'paint the fins', 'AAAA'):
            self.assertNotIn(word, line)

    def test_the_page_travels(self):
        payload = self._payload({
            'uid': 'abc', 'title': 'my rockit',
            'description': 'i made a rocket', 'tags': 'space',
            'activity': 'org.laptop.RocketActivity'})
        self.assertEqual(payload['peershare'], peershare.PROTOCOL)
        self.assertEqual(payload['kind'], peershare.KIND_ENTRY)
        self.assertEqual(payload['uid'], 'abc')
        self.assertEqual(payload['title'], 'my rockit')
        self.assertEqual(payload['description'], 'i made a rocket')
        self.assertEqual(payload['tags'], 'space')
        self.assertEqual(payload['activity'], 'org.laptop.RocketActivity')

    def test_comments_travel_as_a_list(self):
        comments = [{'from': 'Ana', 'message': 'how did you do the fins?'}]
        payload = self._payload({'uid': 'abc',
                                 'comments': json.dumps(comments)})
        self.assertEqual(payload['comments'], comments)

    def test_broken_comments_travel_as_nothing(self):
        payload = self._payload({'uid': 'abc', 'comments': 'not json'})
        self.assertEqual(payload['comments'], [])

    def test_the_entry_color_beats_the_owner_color(self):
        payload = self._payload({'uid': 'abc',
                                 'icon-color': '#00FF00,#0000FF'})
        self.assertEqual(payload['color'], '#00FF00,#0000FF')

    def test_a_colorless_entry_falls_back(self):
        payload = self._payload({'uid': 'abc'})
        self.assertEqual(payload['color'], '#FF2B34,#005FE4')

    def test_preview_rides_base64(self):
        payload = self._payload({'uid': 'abc', 'preview': b'\x89PNG\r\n'})
        self.assertEqual(base64.b64decode(payload['preview']),
                         b'\x89PNG\r\n')

    def test_a_missing_preview_leaves_the_key_out(self):
        self.assertNotIn('preview', self._payload({'uid': 'abc'}))
        self.assertNotIn('preview',
                         self._payload({'uid': 'abc', 'preview': ''}))

    def test_a_bare_record_still_builds(self):
        payload = self._payload({})
        self.assertEqual(payload['uid'], '')
        self.assertEqual(payload['title'], '')
        self.assertEqual(payload['comments'], [])


class TestEncodePayload(unittest.TestCase):

    def test_a_small_page_keeps_its_preview(self):
        payload = peershare.build_entry_payload(
            {'uid': 'abc', 'preview': b'tiny'}, color='#000,#FFF')
        line = peershare.encode_payload(payload)
        self.assertIn('preview', json.loads(line))
        self.assertNotIn('\n', line)

    def test_an_oversized_preview_is_left_behind(self):
        payload = peershare.build_entry_payload(
            {'uid': 'abc', 'title': 'my rockit',
             'preview': b'x' * peershare.PAYLOAD_LIMIT},
            color='#000,#FFF')
        message = json.loads(peershare.encode_payload(payload))
        self.assertNotIn('preview', message)
        self.assertEqual(message['title'], 'my rockit')

    def test_an_oversized_page_without_a_preview_still_goes(self):
        payload = peershare.build_entry_payload(
            {'uid': 'abc', 'description': 'x' * peershare.PAYLOAD_LIMIT},
            color='#000,#FFF')
        message = json.loads(peershare.encode_payload(payload))
        self.assertEqual(len(message['description']),
                         peershare.PAYLOAD_LIMIT)


class TestParseMessage(unittest.TestCase):

    def test_a_fetch_parses(self):
        message = peershare.parse_message(
            '{"peershare": 1, "kind": "fetch", "uid": "abc"}')
        self.assertEqual(message['kind'], 'fetch')
        self.assertEqual(message['uid'], 'abc')

    def test_an_ask_keeps_its_text(self):
        message = peershare.parse_message(
            json.dumps({'peershare': 1, 'kind': 'ask', 'uid': 'abc',
                        'message': 'why?'}))
        self.assertEqual(message['message'], 'why?')

    def test_a_fetch_that_names_no_entry_is_nothing_to_answer(self):
        for line in ('{"peershare": 1, "kind": "fetch"}',
                     '{"peershare": 1, "kind": "fetch", "uid": ""}',
                     '{"peershare": 1, "kind": "fetch", "uid": 5}',
                     '{"peershare": 1, "kind": "fetch", "uid": null}',
                     '{"peershare": 1, "kind": "fetch", "uid": ["abc"]}',
                     '{"peershare": 1, "kind": "ask", "message": "why?"}',
                     '{"peershare": 1, "kind": "ask", "uid": 5}'):
            self.assertIsNone(peershare.parse_message(line), line)

    def test_an_entry_reply_needs_no_uid_to_parse(self):
        message = peershare.parse_message(
            '{"peershare": 1, "kind": "entry"}')
        self.assertEqual(message['kind'], 'entry')

    def test_somebody_elses_chat_is_ignored(self):
        for line in ('hello everyone', '', '[1, 2, 3]', '"peershare"',
                     'null', '{"kind": "fetch", "uid": "abc"}',
                     '{"peershare": 2, "kind": "fetch", "uid": "abc"}',
                     '{"peershare": true, "kind": "fetch", "uid": "abc"}',
                     '{"peershare": 1, "kind": "erase", "uid": "abc"}',
                     '{"peershare": 1}'):
            self.assertIsNone(peershare.parse_message(line), line)

    def test_a_non_string_is_ignored(self):
        self.assertIsNone(peershare.parse_message(None))

    def test_a_round_trip_survives(self):
        payload = peershare.build_entry_payload(
            {'uid': 'abc', 'title': 'my rockit'}, color='#000,#FFF')
        message = peershare.parse_message(peershare.encode_payload(payload))
        self.assertEqual(message['kind'], peershare.KIND_ENTRY)
        self.assertEqual(message['title'], 'my rockit')


class TestSenderNick(unittest.TestCase):

    def test_a_name_is_a_name(self):
        self.assertEqual(peershare.sender_nick('  Ana '), 'Ana')

    def test_a_name_nobody_has_is_anonymous(self):
        self.assertEqual(peershare.sender_nick('a' * 500), '')

    def test_control_and_direction_characters_are_anonymous(self):
        for nick in ('An\ra', 'An\u202ea', 'An\u2028a'):
            self.assertEqual(peershare.sender_nick(nick), '')

    def test_a_missing_nick_is_anonymous(self):
        self.assertEqual(peershare.sender_nick(None), '')
        self.assertEqual(peershare.sender_nick(''), '')


class TestHasAsked(unittest.TestCase):

    def test_a_visitor_who_already_asked_is_recognised(self):
        comments = [{'from': 'Bo', 'message': 'nice'},
                    {'from': 'Ana', 'message': 'how?'}]
        self.assertTrue(peershare.has_asked(comments, 'Ana'))

    def test_a_visitor_who_has_not_asked_still_may(self):
        comments = [{'from': 'Bo', 'message': 'nice'}]
        self.assertFalse(peershare.has_asked(comments, 'Ana'))

    def test_an_empty_page_lets_anyone_ask(self):
        self.assertFalse(peershare.has_asked([], 'Ana'))

    def test_the_question_survives_reopening_the_page(self):
        # a window closed and reopened re-derives the answer from the
        # comments already on the page, since that's the only record
        raw = peershare.append_comment('', 'Ana', 'how?')
        self.assertTrue(peershare.has_asked(json.loads(raw), 'Ana'))

    def test_an_unusable_name_shares_the_anonymous_slot(self):
        comments = [{'from': '', 'message': 'how?'}]
        self.assertTrue(peershare.has_asked(comments, 'a' * 500))
        self.assertFalse(peershare.has_asked(comments, 'Ana'))

    def test_a_page_without_comments_lets_anyone_ask(self):
        for comments in (None, '', {'from': 'Ana'}, 5):
            self.assertFalse(peershare.has_asked(comments, 'Ana'))

    def test_junk_in_the_list_is_not_a_question(self):
        self.assertFalse(peershare.has_asked(['Ana', None], 'Ana'))


class TestAppendComment(unittest.TestCase):

    def test_a_question_lands_on_the_end(self):
        comments = json.loads(peershare.append_comment(
            '[{"from": "Bo", "message": "nice"}]', 'Ana', 'how?'))
        self.assertEqual(comments[-1], {'from': 'Ana', 'message': 'how?'})
        self.assertEqual(len(comments), 2)

    def test_the_first_question_starts_the_list(self):
        comments = json.loads(
            peershare.append_comment('', 'Ana', 'how?'))
        self.assertEqual(comments, [{'from': 'Ana', 'message': 'how?'}])

    def test_a_redelivered_question_lands_once(self):
        first = peershare.append_comment('', 'Ana', 'how?')
        self.assertIsNone(peershare.append_comment(first, 'Ana', 'how?'))

    def test_a_second_question_from_the_same_friend_is_dropped(self):
        # the has-asked check in the window only runs on the visitor's
        # own machine, so the record has to enforce the rule too
        first = peershare.append_comment('', 'Ana', 'how?')
        self.assertIsNone(
            peershare.append_comment(first, 'Ana', 'and the fins?'))

    def test_a_different_friend_still_gets_their_turn(self):
        first = peershare.append_comment('', 'Ana', 'how?')
        second = peershare.append_comment(first, 'Ben', 'and the fins?')
        self.assertEqual(
            [comment['from'] for comment in json.loads(second)],
            ['Ana', 'Ben'])

    def test_a_full_record_takes_no_more(self):
        comments = json.dumps(
            [{'from': 'kid-%d' % index, 'message': 'hi'}
             for index in range(reflectguard.MAX_COMMENTS)])
        self.assertIsNone(peershare.append_comment(comments, 'Ana', 'how?'))

    def test_an_empty_question_is_no_question(self):
        for text in ('', '   ', '\t\n ', None, 5, ['how?']):
            self.assertIsNone(peershare.append_comment('', 'Ana', text))

    def test_an_essay_is_not_a_question(self):
        self.assertIsNone(peershare.append_comment(
            '', 'Ana', 'x' * (peershare.ASK_LIMIT + 1)))
        self.assertIsNotNone(peershare.append_comment(
            '', 'Ana', 'x' * peershare.ASK_LIMIT))

    def test_control_characters_never_reach_the_record(self):
        self.assertIsNone(
            peershare.append_comment('', 'Ana', 'how\u202edid you'))

    def test_an_unusable_name_leaves_the_question_anonymous(self):
        comments = json.loads(
            peershare.append_comment('', 'a' * 500, 'how?'))
        self.assertEqual(comments, [{'from': '', 'message': 'how?'}])

    def test_a_broken_record_is_not_a_reason_to_drop_the_question(self):
        comments = json.loads(
            peershare.append_comment('not json', 'Ana', 'how?'))
        self.assertEqual(comments, [{'from': 'Ana', 'message': 'how?'}])

    def test_an_emoji_held_together_still_asks(self):
        self.assertIsNotNone(peershare.append_comment(
            '', 'Ana', 'I love \U0001F469\u200d\U0001F680 rockets!'))

    def test_a_question_of_nothing_but_joiners_is_no_question(self):
        self.assertIsNone(
            peershare.append_comment('', 'Ana', '\u200d\u200d'))

    def test_the_senders_color_rides_along_when_known(self):
        comments = json.loads(peershare.append_comment(
            '', 'Ana', 'how?', color='#FF2B34,#005FE4'))
        self.assertEqual(comments[0]['icon-color'], '#FF2B34,#005FE4')

    def test_an_unknown_color_leaves_the_record_plain(self):
        comments = json.loads(
            peershare.append_comment('', 'Ana', 'how?'))
        self.assertNotIn('icon-color', comments[0])


class _Call(object):
    """One D-Bus method call the fake connection took."""

    def __init__(self, name, args, reply_handler, error_handler):
        self.name = name
        self.args = args
        self.reply_handler = reply_handler
        self.error_handler = error_handler

    def reply(self, *values):
        self.reply_handler(*values)

    def fail(self, error='boom'):
        self.error_handler(error)


class _FakeInterface(object):
    """One interface proxy off the fake connection.

    Every method call lands in `calls`; by default the reply handler
    fires straight away with whatever `replies` holds for that method.
    A name in `holds` is recorded and left hanging, so a test can drive
    the ordering by firing the reply itself.
    """

    def __init__(self, bus_name='org.fake.Salut'):
        self.bus_name = bus_name
        self.object_path = '/org/fake/conn'
        self.calls = []
        self.replies = {}
        self.errors = {}
        self.holds = set()
        self.raises = set()
        self.signals = {}

    def __getattr__(self, name):
        return partial(self._invoke, name)

    def connect_to_signal(self, name, handler, **kwargs):
        self.signals[name] = handler
        return Mock()

    def _invoke(self, name, *args, **kwargs):
        if name in self.raises:
            raise RuntimeError('synchronous boom')
        call = _Call(name, args, kwargs.get('reply_handler'),
                     kwargs.get('error_handler'))
        self.calls.append(call)
        if name in self.holds:
            return
        if name in self.errors:
            call.fail(self.errors[name])
            return
        if call.reply_handler is not None:
            call.reply(*self.replies.get(name, ()))

    def names(self):
        return [call.name for call in self.calls]

    def find(self, name):
        return [call for call in self.calls if call.name == name]


def _fake_conn(buddy_info=True):
    conn = {CONNECTION: _FakeInterface(),
            REQUESTS: _FakeInterface(),
            ACTIVITY_PROPERTIES: _FakeInterface()}
    conn[CONNECTION].replies['RequestHandles'] = ([7],)
    conn[CONNECTION].replies['RequestChannel'] = ('/org/fake/room',)
    if buddy_info:
        conn[BUDDY_INFO] = _FakeInterface()
        conn[BUDDY_INFO].replies['GetActivities'] = ([],)
    return conn


class _FakeNeighborhoodModel(object):

    def __init__(self, conn):
        self.conn = conn
        self.self_handle = 1
        self._callbacks = []

    def connect(self, signal, callback):
        self._callbacks.append((signal, callback))
        return len(self._callbacks)

    def get_link_local_connection(self):
        return self.conn

    def get_link_local_self_handle(self):
        if self.conn is None:
            return None
        return self.self_handle

    def get_buddy_by_handle(self, handle):
        return None

    def connection_changed(self):
        for signal, callback in self._callbacks:
            if signal == 'link-local-connection-changed':
                callback(self)


class _FakeChannel(object):

    def __init__(self):
        self.sent = []
        self.sent_types = []
        self.closes = 0
        self.acknowledged = []
        self.pending = []
        self.handlers = []
        self.matches = []

    def connect_to_signal(self, name, handler, **kwargs):
        match = Mock()
        if name == 'Received':
            self.handlers.append(handler)
            match.remove.side_effect = \
                lambda: self.handlers.remove(handler)
        self.matches.append(match)
        return match

    def ListPendingMessages(self, clear, **kwargs):
        kwargs['reply_handler'](list(self.pending))

    def AcknowledgePendingMessages(self, message_ids, **kwargs):
        self.acknowledged.extend(message_ids)

    def Send(self, message_type, text, **kwargs):
        self.sent.append(text)
        self.sent_types.append(message_type)

    def Close(self, **kwargs):
        self.closes += 1

    def receive(self, text, message_id=1, sender=42):
        for handler in list(self.handlers):
            handler(message_id, 0, sender, 0, 0, text)


class _FakeConnProxy(object):
    """Stands in for the connection object the sweep calls
    Properties.Get on to list channels that existed before the
    watch started."""

    def __init__(self):
        self.existing = []
        self.gets = []

    def Get(self, interface, name, **kwargs):
        self.gets.append((interface, name))
        kwargs['reply_handler'](list(self.existing))


class _FakeBus(object):

    def __init__(self, channel, conn_proxy=None):
        self._channel = channel
        self._conn_proxy = conn_proxy or _FakeConnProxy()

    def get_object(self, bus_name, path):
        if path == '/org/fake/conn':
            return self._conn_proxy
        return self._channel


class _TransportCase(unittest.TestCase):
    """Drives the advert's D-Bus chain without a bus or a main loop."""

    def setUp(self):
        self.timers = []
        self.channel = _FakeChannel()
        self.conn_proxy = _FakeConnProxy()
        self.model = _FakeNeighborhoodModel(_fake_conn())
        self.written = []
        self._patch(peershare.GLib, 'idle_add', lambda cb, *a: 0)
        self._patch(peershare.GLib, 'timeout_add_seconds', self._add_timer)
        self._patch(peershare.neighborhood, 'get_model', lambda: self.model)
        self._patch(peershare.dbus, 'SessionBus',
                    lambda: _FakeBus(self.channel, self.conn_proxy))
        self._patch(model, 'get',
                    lambda uid: {'uid': uid, 'title': 'my rockit',
                                 'shared': '1'})
        self._patch(model, 'write',
                    lambda metadata, **kwargs:
                    self.written.append(dict(metadata)))

    def _patch(self, target, attribute, value):
        patcher = patch.object(target, attribute, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _add_timer(self, delay, callback, *args):
        self.timers.append((delay, callback, args))
        return len(self.timers)

    def _peershare(self):
        share = peershare.PeerShare()
        self.addCleanup(model.updated.disconnect,
                        share._PeerShare__entry_updated_cb)
        self.addCleanup(model.deleted.disconnect,
                        share._PeerShare__entry_deleted_cb)
        return share


class TestAdvertiseChain(_TransportCase):

    def test_properties_only_go_out_once_the_advert_landed(self):
        conn = self.model.conn
        conn[BUDDY_INFO].holds.add('AddActivity')
        share = self._peershare()
        share._queue('uid-1')

        names = conn[CONNECTION].names()
        self.assertLess(names.index('RequestHandles'),
                        names.index('RequestChannel'))
        self.assertEqual(conn[BUDDY_INFO].names(), ['AddActivity'])
        self.assertEqual(conn[ACTIVITY_PROPERTIES].names(), [])

        conn[BUDDY_INFO].find('AddActivity')[0].reply()
        self.assertEqual(conn[ACTIVITY_PROPERTIES].names(),
                         ['SetProperties'])
        self.assertIn('uid-1', share._shares)

    def test_the_room_is_named_after_the_entry(self):
        share = self._peershare()
        share._queue('uid-1')
        call = self.model.conn[CONNECTION].find('RequestHandles')[0]
        self.assertEqual(call.args[1],
                         [peershare.entry_activity_id('uid-1')])


class TestFailedAdvert(_TransportCase):

    def test_a_failed_advert_comes_round_again_on_the_wait(self):
        conn = self.model.conn
        conn[CONNECTION].errors['RequestHandles'] = 'no bus'
        share = self._peershare()
        with self.assertLogs(level=logging.ERROR):
            share._queue('uid-1')

        self.assertIn('uid-1', share._pending)
        self.assertEqual(self.timers[-1][0], peershare._RETRY_SECONDS)

        del conn[CONNECTION].errors['RequestHandles']
        _delay, callback, args = self.timers[-1]
        callback(*args)
        self.assertIn('uid-1', share._shares)
        self.assertEqual(conn[BUDDY_INFO].names(), ['AddActivity'])


class TestConnectionComesAndGoes(_TransportCase):

    def test_a_dropped_connection_re_advertises_when_it_returns(self):
        share = self._peershare()
        share._queue('uid-1')
        self.assertIn('uid-1', share._shares)

        self.model.conn = None
        self.model.connection_changed()
        self.assertEqual(share._shares, {})
        self.assertIn('uid-1', share._pending)
        # nothing is closed over a connection that is already gone
        self.assertEqual(self.channel.closes, 0)

        self.model.conn = _fake_conn()
        self.model.connection_changed()
        self.assertIn('uid-1', share._shares)
        self.assertEqual(self.model.conn[BUDDY_INFO].names(),
                         ['AddActivity'])


class TestRetraction(_TransportCase):

    def test_a_retraction_waits_for_a_connection_it_can_use(self):
        share = self._peershare()
        share._queue('uid-1')
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.replies['GetActivities'] = (
            [('other-activity', 3),
             (peershare.entry_activity_id('uid-1'), 7)],)

        self.model.self_handle = None
        share._retract('uid-1')
        self.assertEqual(share._retractions, {'uid-1'})
        self.assertEqual(buddy_info.names(), ['AddActivity'])

        self.model.self_handle = 5
        self.model.connection_changed()
        self.assertEqual(buddy_info.names(),
                         ['AddActivity', 'GetActivities', 'SetActivities'])
        self.assertEqual(buddy_info.find('SetActivities')[0].args[0],
                         [('other-activity', 3)])
        self.assertEqual(share._retractions, set())

    def test_two_retractions_ride_one_round_and_both_land(self):
        # if each retraction did its own read, the second write would
        # undo the first one's removal
        share = self._peershare()
        share._queue('uid-1')
        share._queue('uid-2')
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.holds.add('GetActivities')

        share._retract('uid-1')
        share._retract('uid-2')
        self.assertEqual(len(buddy_info.find('GetActivities')), 1)

        buddy_info.find('GetActivities')[0].reply(
            [('other-activity', 3),
             (peershare.entry_activity_id('uid-1'), 7),
             (peershare.entry_activity_id('uid-2'), 8)])
        sets = buddy_info.find('SetActivities')
        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0].args[0], [('other-activity', 3)])
        self.assertEqual(share._retractions, set())

    def test_a_retraction_does_not_write_over_a_fresh_advert(self):
        share = self._peershare()
        share._queue('uid-1')
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.holds.add('GetActivities')

        share._retract('uid-1')
        share._queue('uid-2')
        buddy_info.find('GetActivities')[0].reply(
            [(peershare.entry_activity_id('uid-1'), 7)])

        sets = buddy_info.find('SetActivities')
        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0].args[0],
                         [(peershare.entry_activity_id('uid-2'), 7)])

    def test_a_half_advertised_entry_is_not_named_early(self):
        # its AddActivity call is still in flight, so listing it now
        # would show peers a room with no name or colour yet
        share = self._peershare()
        share._queue('uid-1')
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.holds.add('GetActivities')
        share._retract('uid-1')
        buddy_info.holds.add('AddActivity')
        share._queue('uid-2')

        buddy_info.find('GetActivities')[0].reply(
            [(peershare.entry_activity_id('uid-1'), 7)])
        sets = buddy_info.find('SetActivities')
        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0].args[0], [])

    def test_a_read_that_blows_up_does_not_jam_retractions(self):
        share = self._peershare()
        share._queue('uid-1')
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.raises.add('GetActivities')
        with self.assertLogs(level=logging.ERROR):
            share._retract('uid-1')
        self.assertEqual(share._retractions, {'uid-1'})

        buddy_info.raises.discard('GetActivities')
        share._flush_retractions()
        self.assertEqual(len(buddy_info.find('SetActivities')), 1)
        self.assertEqual(share._retractions, set())

    def test_a_reads_jam_ends_with_its_connection(self):
        share = self._peershare()
        share._queue('uid-1')
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.holds.add('GetActivities')
        share._retract('uid-1')
        self.assertEqual(share._retractions, {'uid-1'})

        # the connection drops while the read is still outstanding,
        # so no reply is ever going to arrive for it
        old_conn = self.model.conn
        self.model.conn = None
        self.model.connection_changed()
        self.model.conn = old_conn
        buddy_info.holds.discard('GetActivities')
        self.model.connection_changed()
        self.assertEqual(len(buddy_info.find('SetActivities')), 1)
        self.assertEqual(share._retractions, set())

    def test_an_entry_shared_again_is_not_written_out_of_the_list(self):
        # a failed write puts its entries back in the queue, and by
        # the next round the child may have shared one of them again;
        # that entry must be left alone this time
        share = self._peershare()
        share._queue('uid-1')
        share._queue('uid-2')
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.replies['GetActivities'] = (
            [(peershare.entry_activity_id('uid-1'), 7),
             (peershare.entry_activity_id('uid-2'), 8)],)
        buddy_info.holds.add('SetActivities')
        share._retract('uid-1')

        self.model.conn[CONNECTION].errors['RequestHandles'] = 'no bus'
        with self.assertLogs(level=logging.ERROR):
            share._queue('uid-1')
            buddy_info.find('SetActivities')[0].fail('boom')
        self.assertIn('uid-1', share._pending)
        self.assertIn('uid-1', share._retractions)

        buddy_info.holds.discard('SetActivities')
        share._retract('uid-2')
        sets = buddy_info.find('SetActivities')
        self.assertEqual(len(sets), 2)
        self.assertEqual(sets[-1].args[0],
                         [(peershare.entry_activity_id('uid-1'), 7)])


# a friend's page gets drawn, so its fields are validated first


class TestTheIdAFriendSends(unittest.TestCase):

    def test_an_ordinary_id_is_carried(self):
        self.assertEqual(peershare.safe_uid('4f9a-22bc_1'), '4f9a-22bc_1')

    def test_an_id_that_names_a_path_is_refused(self):
        # the page's own machinery opens an id that names a real file,
        # so a friend cannot use it to point at our disk
        self.assertEqual(peershare.safe_uid('/etc/shadow'), '')
        self.assertEqual(peershare.safe_uid('../../home/kid/notes'), '')

    def test_an_id_that_is_not_a_string_is_refused(self):
        self.assertEqual(peershare.safe_uid(None), '')
        self.assertEqual(peershare.safe_uid({'uid': 'x'}), '')

    def test_an_endless_id_is_refused(self):
        self.assertEqual(peershare.safe_uid('a' * 400), '')


class TestTheKindAFriendClaims(unittest.TestCase):

    def test_an_ordinary_kind_is_carried(self):
        self.assertEqual(peershare.safe_mime('image/png'), 'image/png')

    def test_a_bundle_kind_is_refused(self):
        # a page claiming to be a bundle would send the Journal
        # looking for a file to install; a shared page is not a bundle
        for kind in peershare._BUNDLE_KINDS:
            self.assertEqual(peershare.safe_mime(kind), '')

    def test_a_kind_that_is_not_a_string_is_refused(self):
        self.assertEqual(peershare.safe_mime(None), '')


class TestTheTagsAFriendSends(unittest.TestCase):

    def test_ordinary_tags_are_carried(self):
        self.assertEqual(peershare.safe_tags('rockets moon'),
                         'rockets moon')

    def test_a_flood_of_tags_stops_at_a_page_full(self):
        # each tag becomes a widget on screen, and the wire limit
        # alone would still leave room for thousands of them
        tags = ' '.join('t%d' % number for number in range(4000))
        self.assertEqual(len(peershare.safe_tags(tags).split()),
                         peershare.TAG_LIMIT)

    def test_an_endless_tag_is_cut_to_a_tag(self):
        self.assertEqual(len(peershare.safe_tags('x' * 5000)),
                         peershare.TAG_CHARS)

    def test_control_marks_still_come_out(self):
        self.assertEqual(peershare.safe_tags('one\u202etwo'), 'onetwo')


class TestSynchronousFailures(_TransportCase):

    def test_an_advertise_that_blows_up_waits_its_turn_again(self):
        self.model.conn[CONNECTION].raises.add('RequestHandles')
        share = self._peershare()
        with self.assertLogs(level=logging.ERROR):
            share._queue('uid-1')

        self.assertNotIn('uid-1', share._shares)
        self.assertIn('uid-1', share._pending)
        self.assertTrue(self.timers)

    def test_a_late_error_after_a_retract_stays_retracted(self):
        buddy_info = self.model.conn[BUDDY_INFO]
        buddy_info.holds.add('AddActivity')
        buddy_info.holds.add('GetActivities')
        share = self._peershare()
        share._queue('uid-1')
        share._retract('uid-1')

        with self.assertLogs(level=logging.ERROR):
            buddy_info.find('AddActivity')[0].fail('connection reset')

        self.assertNotIn('uid-1', share._pending)
        self.assertNotIn('uid-1', share._shares)
        self.assertEqual(self.timers, [])

    def test_a_write_that_blows_up_keeps_the_retractions(self):
        buddy_info = self.model.conn[BUDDY_INFO]
        share = self._peershare()
        share._queue('uid-1')
        buddy_info.holds.add('GetActivities')
        share._retract('uid-1')

        buddy_info.raises.add('SetActivities')
        with self.assertLogs(level=logging.ERROR):
            buddy_info.find('GetActivities')[0].reply(
                [(peershare.entry_activity_id('uid-1'), 7)])

        self.assertEqual(share._retractions, {'uid-1'})
        self.assertFalse(share._retract_inflight)


class TestMissingBuddyInfo(_TransportCase):

    def test_a_connection_without_buddy_info_opens_no_room(self):
        self.model.conn = _fake_conn(buddy_info=False)
        share = self._peershare()
        with self.assertLogs(level=logging.WARNING) as caught:
            share._queue('uid-1')
            share._flush()

        self.assertEqual(self.model.conn[CONNECTION].names(), [])
        self.assertIn('uid-1', share._pending)
        self.assertEqual(share._shares, {})
        said = [record for record in caught.records
                if 'BuddyInfo' in record.getMessage()]
        self.assertEqual(len(said), 1)

    def test_the_next_connection_gets_a_fresh_try(self):
        self.model.conn = _fake_conn(buddy_info=False)
        share = self._peershare()
        with self.assertLogs(level=logging.WARNING):
            share._queue('uid-1')

        self.model.conn = _fake_conn()
        self.model.connection_changed()
        self.assertIn('uid-1', share._shares)


class TestServingVisitors(_TransportCase):
    """The line back is a one-to-one channel a visitor opens."""

    _PATH = '/org/fake/contact/1'

    def _share(self, uid='uid-1'):
        share = self._peershare()
        share._queue(uid)
        return share

    def _visitor_arrives(self, share, path=None):
        signals = self.model.conn[CONNECTION].signals
        signals['NewChannel'](path or self._PATH,
                              peershare.CHANNEL_TYPE_TEXT,
                              peershare.HANDLE_TYPE_CONTACT, 9, False)

    def _fetch(self, uid):
        return json.dumps({'peershare': peershare.PROTOCOL,
                           'kind': peershare.KIND_FETCH, 'uid': uid})

    def _ask(self, uid, text):
        return json.dumps({'peershare': peershare.PROTOCOL,
                           'kind': peershare.KIND_ASK, 'uid': uid,
                           'message': text})

    def test_both_signals_lead_to_one_channel(self):
        share = self._share()
        self._visitor_arrives(share)
        self.model.conn[REQUESTS].signals['NewChannels']([
            (self._PATH, {peershare.CHANNEL + '.ChannelType':
                          peershare.CHANNEL_TYPE_TEXT,
                          peershare.CHANNEL + '.TargetHandleType':
                          peershare.HANDLE_TYPE_CONTACT})])
        self.assertEqual(list(share._peers), [self._PATH])
        self.assertEqual(len(self.channel.handlers), 1)

    def test_a_channel_open_before_the_watch_is_swept_in(self):
        # salut outlives the shell, so a visitor's channel can already
        # be open before the watch starts and no NewChannel signal
        # will fire for it -- the sweep is what picks it up
        self.conn_proxy.existing = [
            (self._PATH, {peershare.CHANNEL + '.ChannelType':
                          peershare.CHANNEL_TYPE_TEXT,
                          peershare.CHANNEL + '.TargetHandleType':
                          peershare.HANDLE_TYPE_CONTACT})]
        share = self._share()

        self.assertIn((REQUESTS, 'Channels'), self.conn_proxy.gets)
        self.assertEqual(list(share._peers), [self._PATH])
        self.channel.receive(self._fetch('uid-1'))
        self.assertEqual(len(self.channel.sent), 1)

    def test_a_channel_we_opened_ourselves_is_served_too(self):
        # two children viewing each other's entries share one
        # channel, so the one our window requested is also where
        # their fetch arrives
        self._share()
        self.model.conn[CONNECTION].signals['NewChannel'](
            self._PATH, peershare.CHANNEL_TYPE_TEXT,
            peershare.HANDLE_TYPE_CONTACT, 9, True)
        self.channel.receive(self._fetch('uid-1'))
        self.assertEqual(len(self.channel.sent), 1)

    def test_a_room_channel_is_not_a_line_to_anybody(self):
        share = self._share()
        self.model.conn[CONNECTION].signals['NewChannel'](
            '/org/fake/room', peershare.CHANNEL_TYPE_TEXT,
            peershare.HANDLE_TYPE_ROOM, 7, False)
        self.assertEqual(share._peers, {})

    def test_an_answer_is_left_to_the_window_that_asked(self):
        share = self._share()
        self._visitor_arrives(share)
        self.channel.receive(json.dumps(peershare.build_entry_payload(
            {'uid': 'uid-1'}, color='#000,#FFF')), message_id=3)
        self.assertEqual(self.channel.acknowledged, [])
        self.assertEqual(self.channel.sent, [])

    def test_a_fetch_is_answered_on_the_same_channel(self):
        share = self._share()
        self._visitor_arrives(share)
        self.channel.receive(self._fetch('uid-1'))

        self.assertEqual(len(self.channel.sent), 1)
        page = json.loads(self.channel.sent[0])
        self.assertEqual(page['kind'], peershare.KIND_ENTRY)
        self.assertEqual(page['uid'], 'uid-1')
        self.assertEqual(page['title'], 'my rockit')
        self.assertEqual(self.channel.acknowledged, [1])
        self.assertEqual(self.channel.sent_types,
                         [peershare.MESSAGE_TYPE_PROTOCOL])
        # Telepathy spec values: NORMAL=0, ACTION=1, NOTICE=2.
        self.assertEqual(peershare.MESSAGE_TYPE_PROTOCOL, 2)

    def test_a_fetch_for_an_unshared_entry_is_not_answered(self):
        share = self._share()
        self._visitor_arrives(share)
        self.channel.receive(self._fetch('uid-nobody-shared'))
        self.assertEqual(self.channel.sent, [])
        self.assertEqual(self.channel.acknowledged, [1])

    def test_a_fetch_waiting_in_the_queue_is_answered_too(self):
        share = self._share()
        self.channel.pending = [(4, 0, 42, 0, 0, self._fetch('uid-1'))]
        self._visitor_arrives(share)
        self.assertEqual(len(self.channel.sent), 1)
        self.assertEqual(self.channel.acknowledged, [4])

    def test_a_friends_chat_is_left_where_they_will_find_it(self):
        share = self._share()
        self._visitor_arrives(share)
        for line in ('hello!', '{"not": "ours"}', ''):
            self.channel.receive(line, message_id=7)
        self.assertEqual(self.channel.acknowledged, [])
        self.assertEqual(self.channel.sent, [])

    def test_a_friends_chat_is_reported_to_the_stray_listener(self):
        heard = []
        peershare.set_stray_chat_cb(
            lambda channel_path, sender: heard.append((channel_path, sender)))
        self.addCleanup(peershare.set_stray_chat_cb, None)
        share = self._share()
        self._visitor_arrives(share)
        self.channel.receive('hello!', message_id=7, sender=42)
        self.assertEqual(heard, [(self._PATH, 42)])
        self.assertEqual(self.channel.acknowledged, [])

    def test_an_ask_lands_on_the_entry_it_names(self):
        share = self._share()
        self._visitor_arrives(share)
        self.channel.receive(self._ask('uid-1', 'how did you do the fins?'))

        self.assertEqual(len(self.written), 1)
        self.assertEqual(self.written[0]['uid'], 'uid-1')
        self.assertEqual(
            json.loads(self.written[0]['comments']),
            [{'from': '', 'message': 'how did you do the fins?'}])

    def test_an_ask_for_an_unshared_entry_is_dropped(self):
        share = self._share()
        self._visitor_arrives(share)
        self.channel.receive(self._ask('uid-nobody-shared', 'how?'))
        self.assertEqual(self.written, [])

    def test_a_lost_connection_takes_the_listeners_with_it(self):
        share = self._share()
        self._visitor_arrives(share)
        matches = list(self.channel.matches)

        self.model.conn = None
        self.model.connection_changed()

        self.assertEqual(share._peers, {})
        self.assertIsNone(share._bus_name)
        for match in matches:
            match.remove.assert_called_once_with()

    def test_the_next_connection_listens_again(self):
        share = self._share()
        self._visitor_arrives(share)
        self.model.conn = None
        self.model.connection_changed()

        self.model.conn = _fake_conn()
        self.model.connection_changed()
        self._visitor_arrives(share)
        self.channel.receive(self._fetch('uid-1'))
        self.assertEqual(len(self.channel.sent), 1)


class TestAskLeg(_TransportCase):

    def test_a_delivered_question_is_handed_to_the_guard(self):
        share = self._peershare()
        share._queue('uid-1')
        guard = Mock()
        self._patch(peershare.reflectguard, 'get_guard', lambda: guard)

        share._take_ask('uid-1', 42, 'how did you do the fins?')

        self.assertEqual(len(self.written), 1)
        self.assertEqual(
            json.loads(self.written[0]['comments']),
            [{'from': '', 'message': 'how did you do the fins?'}])
        guard.note_delivered_comment.assert_called_once_with(
            'uid-1', {'from': '', 'message': 'how did you do the fins?'})


if __name__ == '__main__':
    unittest.main()
