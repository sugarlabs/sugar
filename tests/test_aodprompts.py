# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from jarabe.model.aodprompts import build_system_prompt
from jarabe.model.aodprompts import extract_json_object
from jarabe.model.aodspec import ActivitySpec


class TestAodPrompts(unittest.TestCase):

    def test_system_prompt_contains_sugar_constraints(self):
        spec = ActivitySpec(
            'Story Studio',
            'Create a story writing activity.',
            'creation',
            'MIT',
            template='narrative',
        )
        prompt = build_system_prompt(spec)
        self.assertIn('Subclass sugar3.activity.activity.Activity', prompt)
        self.assertIn('Return one JSON object', prompt)
        self.assertIn('canvas, carrom, chess, grid', prompt)
        self.assertIn('provider code generator owns', prompt)
        self.assertIn('not templates to copy', prompt)
        self.assertNotIn('local generator owns Python source', prompt)
        self.assertIn('large editable area', prompt)

    def test_system_prompt_supports_science_and_language(self):
        for category, expected in (
                ('science', 'experimenting'),
                ('language', 'storytelling')):
            spec = ActivitySpec(
                'Explore', 'Measure plant growth.', category, 'MIT')
            self.assertIn(expected, build_system_prompt(spec))

    def test_system_prompt_falls_back_on_unknown_category(self):
        spec = ActivitySpec(
            'Explore', 'Measure plant growth.', 'mystery', 'MIT')
        self.assertIn('learner-owned', build_system_prompt(spec))

    def test_extracts_fenced_json(self):
        value = extract_json_object(
            '```json\n{"template": "quiz", "summary": "Test"}\n```'
        )
        self.assertEqual('quiz', value['template'])

    def test_rejects_non_object_json(self):
        with self.assertRaises(ValueError):
            extract_json_object('["not", "an", "object"]')
