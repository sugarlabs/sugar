# Copyright (C) 2026, Sugar Labs
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

import unittest

from jarabe.journal.queryhelpers import apply_prefix_wildcards
from jarabe.journal.queryhelpers import normalize_uid
from jarabe.journal.queryhelpers import query_for_find_ids


class ApplyPrefixWildcardsTest(unittest.TestCase):

    def test_prefix_search_appends_wildcard(self):
        query = {'query': 'term'}
        apply_prefix_wildcards(query)
        self.assertEqual(query['query'], 'term*')

    def test_multi_word_search_appends_wildcard_per_word(self):
        query = {'query': 'foo bar'}
        apply_prefix_wildcards(query)
        self.assertEqual(query['query'], 'foo* bar*')

    def test_quoted_search_is_unchanged(self):
        query = {'query': '"exact title"'}
        apply_prefix_wildcards(query)
        self.assertEqual(query['query'], '"exact title"')

    def test_empty_query_is_unchanged(self):
        query = {'order_by': ['+timestamp']}
        apply_prefix_wildcards(query)
        self.assertNotIn('query', query)


class FindIdsQueryTest(unittest.TestCase):

    def test_select_all_uses_wildcard_query_not_original_text(self):
        # Journal list find() uses the processed query. Select All used to
        # call find_ids() with the original text, so "term" showed Terminal
        # entries but selected none of them.
        original = {
            'query': 'term',
            'mountpoints': ['/'],
            'order_by': ['+timestamp'],
        }
        processed = original.copy()
        apply_prefix_wildcards(processed)

        sent = query_for_find_ids(processed)
        self.assertEqual(sent['query'], 'term*')
        self.assertNotIn('mountpoints', sent)
        self.assertNotEqual(original['query'], sent['query'])

    def test_find_ids_query_matches_visible_find_query(self):
        query = {'query': 'term', 'order_by': ['+timestamp']}
        apply_prefix_wildcards(query)
        sent = query_for_find_ids(query)
        self.assertEqual(sent['query'], query['query'])


class NormalizeUidTest(unittest.TestCase):

    def test_bytes_and_str_compare_equal(self):
        selected = [normalize_uid(b'uid-1')]
        self.assertIn(normalize_uid('uid-1'), selected)
        self.assertIn(normalize_uid(b'uid-1'), selected)

    def test_none_stays_none(self):
        self.assertIsNone(normalize_uid(None))


if __name__ == '__main__':
    unittest.main()
