# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from jarabe.model.aodrefine import apply_patches
from jarabe.model.aodrefine import build_refine_system_prompt
from jarabe.model.aodrefine import build_refine_user_prompt
from jarabe.model.aodrefine import parse_search_replace


_SAMPLE_SOURCE = (
    'from sugar3.activity import activity\n'
    '\n'
    '\n'
    'class GeneratedActivity(activity.Activity):\n'
    '    def __init__(self, handle):\n'
    '        activity.Activity.__init__(self, handle)\n'
    '        self._score = 0\n'
    '        self._build_ui()\n'
    '\n'
    '    def _build_ui(self):\n'
    '        self._label = Gtk.Label("Score: 0")\n'
    '        self.set_canvas(self._label)\n'
    '\n'
    '    def write_file(self, file_path):\n'
    '        pass\n'
    '\n'
    '    def read_file(self, file_path):\n'
    '        pass\n'
)


class TestParseSearchReplace(unittest.TestCase):

    def test_parses_single_block(self):
        response = (
            '<<<<<<< SEARCH\n'
            '        self._score = 0\n'
            '=======\n'
            '        self._score = 0\n'
            '        self._undo_stack = []\n'
            '>>>>>>> REPLACE\n'
        )
        patches = parse_search_replace(response)
        self.assertEqual(1, len(patches))
        self.assertEqual(
            '        self._score = 0',
            patches[0][0],
        )
        self.assertEqual(
            '        self._score = 0\n        self._undo_stack = []',
            patches[0][1],
        )

    def test_parses_multiple_blocks(self):
        response = (
            '<<<<<<< SEARCH\n'
            '        self._score = 0\n'
            '=======\n'
            '        self._score = 100\n'
            '>>>>>>> REPLACE\n'
            '\n'
            '<<<<<<< SEARCH\n'
            '        self._label = Gtk.Label("Score: 0")\n'
            '=======\n'
            '        self._label = Gtk.Label("Score: 100")\n'
            '>>>>>>> REPLACE\n'
        )
        patches = parse_search_replace(response)
        self.assertEqual(2, len(patches))

    def test_full_regen_returns_none(self):
        patches = parse_search_replace('FULLREGEN')
        self.assertIsNone(patches)

    def test_full_regen_with_trailing_text_returns_none(self):
        patches = parse_search_replace('FULLREGEN\n')
        self.assertIsNone(patches)

    def test_missing_divider_raises(self):
        response = (
            '<<<<<<< SEARCH\n'
            'some code\n'
            '>>>>>>> REPLACE\n'
        )
        with self.assertRaises(ValueError):
            parse_search_replace(response)

    def test_missing_replace_marker_raises(self):
        response = (
            '<<<<<<< SEARCH\n'
            'some code\n'
            '=======\n'
            'new code\n'
        )
        with self.assertRaises(ValueError):
            parse_search_replace(response)

    def test_empty_search_raises(self):
        response = (
            '<<<<<<< SEARCH\n'
            '=======\n'
            'new code\n'
            '>>>>>>> REPLACE\n'
        )
        with self.assertRaises(ValueError):
            parse_search_replace(response)

    def test_no_blocks_raises(self):
        with self.assertRaises(ValueError):
            parse_search_replace('Here are the changes:\nadd a button')

    def test_strips_code_fences_around_blocks(self):
        response = (
            '```\n'
            '<<<<<<< SEARCH\n'
            '        self._score = 0\n'
            '=======\n'
            '        self._score = 100\n'
            '>>>>>>> REPLACE\n'
            '```\n'
        )
        patches = parse_search_replace(response)
        self.assertEqual(1, len(patches))


class TestApplyPatches(unittest.TestCase):

    def test_applies_single_patch(self):
        patches = [('        self._score = 0',
                    '        self._score = 100')]
        patched, applied, failed = apply_patches(_SAMPLE_SOURCE, patches)
        self.assertEqual(1, applied)
        self.assertEqual(0, failed)
        self.assertIn('self._score = 100', patched)
        self.assertNotIn('self._score = 0\n', patched)

    def test_applies_multi_line_patch(self):
        search = '        self._score = 0\n        self._build_ui()'
        replace = '        self._score = 0\n        self._undo_stack = []\n        self._build_ui()'
        patches = [(search, replace)]
        patched, applied, failed = apply_patches(_SAMPLE_SOURCE, patches)
        self.assertEqual(1, applied)
        self.assertEqual(0, failed)
        self.assertIn('self._undo_stack = []', patched)

    def test_failed_patch_counted(self):
        patches = [('        self._nonexistent = 42',
                    '        self._new = 99')]
        patched, applied, failed = apply_patches(_SAMPLE_SOURCE, patches)
        self.assertEqual(0, applied)
        self.assertEqual(1, failed)
        self.assertEqual(_SAMPLE_SOURCE, patched)

    def test_whitespace_tolerant_matching(self):
        source = '    self._score = 0   \n'
        patches = [('    self._score = 0', '    self._score = 100')]
        patched, applied, failed = apply_patches(source, patches)
        self.assertEqual(1, applied)
        self.assertEqual(0, failed)
        self.assertIn('self._score = 100', patched)

    def test_multiple_patches_applied_in_order(self):
        patches = [
            ('        self._score = 0', '        self._score = 100'),
            ('        self._label = Gtk.Label("Score: 0")',
             '        self._label = Gtk.Label("Score: 100")'),
        ]
        patched, applied, failed = apply_patches(_SAMPLE_SOURCE, patches)
        self.assertEqual(2, applied)
        self.assertEqual(0, failed)
        self.assertIn('self._score = 100', patched)
        self.assertIn('Score: 100', patched)

    def test_empty_replace_deletes_lines(self):
        search = '        self._score = 0\n'
        patches = [(search, '')]
        patched, applied, failed = apply_patches(_SAMPLE_SOURCE, patches)
        self.assertEqual(1, applied)
        self.assertNotIn('self._score = 0', patched)


class TestRefinePrompts(unittest.TestCase):

    def test_system_prompt_mentions_search_replace(self):
        prompt = build_refine_system_prompt()
        self.assertIn('SEARCH', prompt)
        self.assertIn('REPLACE', prompt)
        self.assertIn('FULLREGEN', prompt)

    def test_user_prompt_includes_source(self):
        prompt = build_refine_user_prompt(
            _SAMPLE_SOURCE, 'add an undo button')
        self.assertIn('GeneratedActivity', prompt)
        self.assertIn('add an undo button', prompt)
        self.assertIn('SEARCH/REPLACE', prompt)

    def test_user_prompt_includes_plan_context(self):
        prompt = build_refine_user_prompt(
            _SAMPLE_SOURCE, 'add undo', plan_context='{"template": "canvas"}')
        self.assertIn('canvas', prompt)


if __name__ == '__main__':
    unittest.main()
