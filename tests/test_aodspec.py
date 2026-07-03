# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodspec import name_from_prompt


class TestActivitySpec(unittest.TestCase):

    def test_valid_spec(self):
        spec = ActivitySpec(
            name='Fraction Quest',
            prompt='Create a game for practicing fractions.',
            category='logic_math',
            license_id='MIT',
        )
        self.assertEqual([], spec.validate())

    def test_reports_all_invalid_fields(self):
        spec = ActivitySpec('', '', 'unknown', 'unknown')
        errors = spec.validate()
        self.assertIn('Activity name is required.', errors)
        self.assertIn('Activity prompt is required.', errors)
        self.assertIn('Unknown activity category: unknown', errors)
        self.assertIn('Unknown activity license: unknown', errors)

    def test_dictionary_round_trip(self):
        original = ActivitySpec(
            name='Fraction Quest',
            prompt='Create a fractions activity.',
            category='logic_math',
            license_id='MIT',
            template='quiz',
            age_band='8-10',
            learner_goal='Recognize equivalent fractions.',
        )
        self.assertEqual(
            original,
            ActivitySpec.from_dict(original.to_dict()),
        )

    def test_science_and_language_categories_are_valid(self):
        for category in ('science', 'language'):
            spec = ActivitySpec(
                name='Explore Plants',
                prompt='Measure plant growth over time.',
                category=category,
                license_id='MIT',
            )
            self.assertEqual([], spec.validate())

    def test_normalized_coerces_unknown_soft_fields(self):
        spec = ActivitySpec(
            name='X' * 120,
            prompt='  Build something fun.  ',
            category='not-a-category',
            license_id='MIT',
            template='not-a-template',
            age_band='   ',
            code_size='huge',
        ).normalized()
        self.assertEqual('creation', spec.category)
        self.assertEqual('auto', spec.template)
        self.assertEqual('standard', spec.code_size)
        self.assertEqual('all', spec.age_band)
        self.assertEqual(80, len(spec.name))
        self.assertEqual([], spec.validate())

    def test_name_from_prompt_ignores_instruction_words(self):
        self.assertEqual(
            'Fractions Quiz Children',
            name_from_prompt('Create a fractions quiz for children'),
        )
