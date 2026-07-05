# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from jarabe.model.aodicons import render_activity_icon


class TestActivityIcons(unittest.TestCase):

    def test_icon_uses_sugar_color_entities(self):
        svg = render_activity_icon({'name': 'Quiz Fun', 'template': 'quiz'})
        self.assertIn('<!ENTITY stroke_color', svg)
        self.assertIn('<!ENTITY fill_color', svg)
        self.assertIn('&stroke_color;', svg)
        self.assertIn('&fill_color;', svg)
        self.assertIn('viewBox="0 0 55 55"', svg)

    def test_template_selects_glyph(self):
        quiz = render_activity_icon({'name': 'A', 'template': 'quiz'})
        chess = render_activity_icon({'name': 'A', 'template': 'chess'})
        self.assertNotEqual(quiz, chess)

    def test_category_fallback_selects_glyph(self):
        science = render_activity_icon(
            {'name': 'A', 'template': 'weird', 'category': 'science'})
        default = render_activity_icon(
            {'name': 'A', 'template': 'weird', 'category': 'weird'})
        self.assertNotEqual(science, default)

    def test_same_plan_is_deterministic(self):
        plan = {'name': 'Star Counter', 'template': 'grid'}
        self.assertEqual(render_activity_icon(plan),
                         render_activity_icon(plan))

    def test_different_names_vary_accent(self):
        one = render_activity_icon({'name': 'Alpha', 'template': 'grid'})
        two = render_activity_icon({'name': 'Bravo!', 'template': 'grid'})
        self.assertNotEqual(one, two)

    def test_malformed_plan_falls_back(self):
        svg = render_activity_icon({'name': None, 'template': 12345})
        self.assertIn('&stroke_color;', svg)


if __name__ == '__main__':
    unittest.main()
