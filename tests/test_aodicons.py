# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import unittest
from unittest import mock

from jarabe.model.aodicons import render_activity_icon
from jarabe.model.aodicons import request_icon_svg
from jarabe.model.aodicons import sanitize_icon_svg
from jarabe.model.aodspec import ActivitySpec

_GOOD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="55" height="55" '
    'viewBox="0 0 55 55">\n'
    '  <path d="M27 8 L35 30 L27 26 L19 30 Z" fill="&fill_color;" '
    'stroke="&stroke_color;" stroke-width="3" '
    'stroke-linejoin="round"/>\n'
    '  <circle cx="27" cy="40" r="4" fill="&stroke_color;"/>\n'
    '</svg>'
)


class _IconProvider:
    name = 'icon-fake'
    model = 'icon-1'

    def __init__(self, response):
        self.response = response
        self.calls = 0

    def generate_text(self, system_prompt, user_prompt, timeout=120,
                      stream_callback=None):
        self.calls += 1
        return self.response


def _spec():
    return ActivitySpec('Space Racer', 'Make a space racing game.',
                        'games', 'MIT')


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


class TestSanitizeIconSvg(unittest.TestCase):

    def test_accepts_clean_svg_and_adds_entity_header(self):
        result = sanitize_icon_svg(_GOOD_SVG)
        self.assertIsNotNone(result)
        self.assertIn('<!ENTITY stroke_color', result)
        self.assertIn('&fill_color;', result)

    def test_extracts_svg_from_fenced_prose(self):
        wrapped = 'Here is your icon!\n```svg\n%s\n```\nEnjoy.' % _GOOD_SVG
        result = sanitize_icon_svg(wrapped)
        self.assertIsNotNone(result)
        self.assertNotIn('```', result)
        self.assertNotIn('Enjoy', result)

    def test_rejects_script(self):
        bad = _GOOD_SVG.replace(
            '</svg>', '<script>alert(1)</script></svg>')
        self.assertIsNone(sanitize_icon_svg(bad))

    def test_rejects_event_handlers(self):
        bad = _GOOD_SVG.replace('<circle ', '<circle onload="x()" ')
        self.assertIsNone(sanitize_icon_svg(bad))

    def test_rejects_external_references(self):
        bad = _GOOD_SVG.replace(
            '<circle', '<a href="https://evil.example"><circle')
        self.assertIsNone(sanitize_icon_svg(bad))

    def test_rejects_wrong_viewbox(self):
        bad = _GOOD_SVG.replace('viewBox="0 0 55 55"',
                                'viewBox="0 0 100 100"')
        self.assertIsNone(sanitize_icon_svg(bad))

    def test_rejects_literal_colors_without_entities(self):
        bad = _GOOD_SVG.replace('&stroke_color;', '#ff0000')
        self.assertIsNone(sanitize_icon_svg(bad))

    def test_rejects_non_svg_and_broken_xml(self):
        self.assertIsNone(sanitize_icon_svg('I cannot draw that.'))
        self.assertIsNone(sanitize_icon_svg(None))
        self.assertIsNone(sanitize_icon_svg(
            '<svg viewBox="0 0 55 55" &stroke_color; <circle</svg>'))


class TestRequestIconSvg(unittest.TestCase):

    def setUp(self):
        self.env = {'AOD_AI_ICON': 'on'}

    def test_good_reply_returns_sanitized_icon(self):
        provider = _IconProvider(_GOOD_SVG)
        with mock.patch.dict(os.environ, self.env):
            icon = request_icon_svg(provider, _spec(), {'summary': 'x'})
        self.assertIsNotNone(icon)
        self.assertIn('<!ENTITY stroke_color', icon)
        self.assertEqual(1, provider.calls)

    def test_garbage_reply_returns_none(self):
        provider = _IconProvider('Sorry, no.')
        with mock.patch.dict(os.environ, self.env):
            self.assertIsNone(
                request_icon_svg(provider, _spec(), {}))

    def test_provider_error_returns_none(self):
        provider = _IconProvider(_GOOD_SVG)
        provider.generate_text = mock.Mock(
            side_effect=RuntimeError('offline'))
        with mock.patch.dict(os.environ, self.env):
            self.assertIsNone(
                request_icon_svg(provider, _spec(), {}))

    def test_disabled_by_env_skips_call(self):
        provider = _IconProvider(_GOOD_SVG)
        with mock.patch.dict(os.environ, {'AOD_AI_ICON': 'off'}):
            self.assertIsNone(
                request_icon_svg(provider, _spec(), {}))
        self.assertEqual(0, provider.calls)

    def test_provider_without_generate_text_returns_none(self):
        class Planner:
            pass
        with mock.patch.dict(os.environ, self.env):
            self.assertIsNone(
                request_icon_svg(Planner(), _spec(), {}))


if __name__ == '__main__':
    unittest.main()
