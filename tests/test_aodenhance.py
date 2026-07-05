# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from jarabe.model.aodenhance import _clean
from jarabe.model.aodenhance import build_enhance_system_prompt
from jarabe.model.aodenhance import enhance_prompt
from jarabe.model.aodenhance import needs_enhancement
from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodspec import MAX_PROMPT_LENGTH


class _FakeEnhancer:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_text(self, system_prompt, user_prompt, timeout=120,
                      stream_callback=None):
        self.calls.append((system_prompt, user_prompt))
        return self.response


class _BrokenEnhancer:
    def generate_text(self, *args, **kwargs):
        raise RuntimeError('provider exploded')


class TestNeedsEnhancement(unittest.TestCase):

    def test_short_prompt_qualifies(self):
        self.assertTrue(needs_enhancement('space racer 2d game'))

    def test_empty_prompt_does_not(self):
        self.assertFalse(needs_enhancement(''))
        self.assertFalse(needs_enhancement('   '))

    def test_long_prompt_skips(self):
        self.assertFalse(needs_enhancement('word ' * 45))
        self.assertFalse(needs_enhancement('x' * 450))


class TestEnhancePrompt(unittest.TestCase):

    def test_success_uses_provider_and_cleans(self):
        provider = _FakeEnhancer(
            '```\nA counting game where kids tap ten ladybugs on a '
            'meadow.\n- Tap each ladybug to count it aloud\n```')
        spec = ActivitySpec('Bugs', 'counting game', 'logic_math', 'MIT')

        text, enhanced = enhance_prompt(provider, 'counting game', spec)

        self.assertTrue(enhanced)
        self.assertTrue(text.startswith('A counting game'))
        self.assertNotIn('```', text)
        system_prompt, user_prompt = provider.calls[0]
        self.assertIn('Sugar (GTK3) learning activity', system_prompt)
        self.assertIn('counting game', user_prompt)
        self.assertIn('logic_math', user_prompt)

    def test_provider_failure_falls_back(self):
        text, enhanced = enhance_prompt(_BrokenEnhancer(), 'a quiz idea')
        self.assertEqual('a quiz idea', text)
        self.assertFalse(enhanced)

    def test_tiny_response_falls_back(self):
        text, enhanced = enhance_prompt(_FakeEnhancer('ok'), 'a quiz idea')
        self.assertEqual('a quiz idea', text)
        self.assertFalse(enhanced)

    def test_no_provider_falls_back(self):
        text, enhanced = enhance_prompt(None, 'a quiz idea')
        self.assertEqual('a quiz idea', text)
        self.assertFalse(enhanced)


class TestClean(unittest.TestCase):

    def test_strips_quotes_and_collapses_blank_runs(self):
        self.assertEqual('line one\n\nline two',
                         _clean('"line one\n\n\n\nline two"'))

    def test_clamps_overlong_text(self):
        cleaned = _clean('y' * (MAX_PROMPT_LENGTH + 500))
        self.assertLessEqual(len(cleaned), MAX_PROMPT_LENGTH)

    def test_non_string_is_empty(self):
        self.assertEqual('', _clean(None))
        self.assertEqual('', _clean(123))

    def test_system_prompt_mentions_plain_text(self):
        self.assertIn('PLAIN TEXT', build_enhance_system_prompt())


if __name__ == '__main__':
    unittest.main()
