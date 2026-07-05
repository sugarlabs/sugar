# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import unittest
from unittest import mock

from jarabe.model.aodcritic import run_critic_round
from jarabe.model.aodgenerator import enrich_plan
from jarabe.model.aodtemplates import render_activity_source
from jarabe.model.aodspec import ActivitySpec

_CRITIC_ENV = {'AOD_CRITIC': 'on', 'AOD_RUNTIME_CHECK': 'off'}


class _CriticProvider:
    name = 'critic-fake'
    model = 'critic-1'

    def __init__(self, response):
        self.response = response
        self.calls = 0
        self.observed_prompts = []

    def generate_text(self, system_prompt, user_prompt, timeout=120,
                      stream_callback=None):
        self.calls += 1
        self.observed_prompts.append((system_prompt, user_prompt))
        return self.response


class _NoTextProvider:
    name = 'plan-only'
    model = 'plan-1'


def _spec_and_source():
    spec = ActivitySpec(
        'Critic Probe',
        'Make a fractions quiz.',
        'logic_math',
        'MIT',
    )
    plan = enrich_plan(spec, {
        'template': 'quiz',
        'summary': 'Critic probe.',
        'learner_goal': 'Practice fractions.',
        'learner_steps': ['Try', 'Explain', 'Share'],
    })
    return spec, plan, render_activity_source(spec, plan)


def _patch_block(search, replace):
    return (
        '<<<<<<< SEARCH\n%s\n=======\n%s\n>>>>>>> REPLACE\n'
        % (search, replace)
    )


class TestCriticRound(unittest.TestCase):

    def setUp(self):
        self.spec, self.plan, self.source = _spec_and_source()

    def test_ok_reply_keeps_source(self):
        provider = _CriticProvider('OK')
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('ok', self.plan['critic'])
        self.assertEqual(1, provider.calls)

    def test_valid_patch_is_applied(self):
        provider = _CriticProvider(_patch_block(
            '        self.max_participants = 1',
            '        self.max_participants = 1  # critic-touched',
        ))
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertIn('# critic-touched', result)
        self.assertEqual('patched:1', self.plan['critic'])

    def test_garbage_reply_keeps_source(self):
        provider = _CriticProvider('Sure! Here are my thoughts...')
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('skipped', self.plan['critic'])

    def test_fullregen_is_refused(self):
        provider = _CriticProvider('FULLREGEN')
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('skipped', self.plan['critic'])

    def test_unmatched_patch_keeps_source(self):
        provider = _CriticProvider(_patch_block(
            'this line does not exist anywhere',
            'replacement',
        ))
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('skipped', self.plan['critic'])

    def test_validation_breaking_patch_keeps_source(self):
        provider = _CriticProvider(_patch_block(
            'class GeneratedActivity(activity.Activity):',
            'class GeneratedActivity(object):',
        ))
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('skipped', self.plan['critic'])

    def test_provider_error_keeps_source(self):
        provider = _CriticProvider('OK')
        provider.generate_text = mock.Mock(
            side_effect=RuntimeError('critic offline'))
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('skipped', self.plan['critic'])

    def test_disabled_by_env_skips_call(self):
        provider = _CriticProvider('OK')
        env = dict(_CRITIC_ENV, AOD_CRITIC='off')
        with mock.patch.dict(os.environ, env):
            result = run_critic_round(
                provider, self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('skipped', self.plan['critic'])
        self.assertEqual(0, provider.calls)

    def test_provider_without_generate_text_skips(self):
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            result = run_critic_round(
                _NoTextProvider(), self.spec, self.plan, self.source)
        self.assertEqual(self.source, result)
        self.assertEqual('skipped', self.plan['critic'])

    def test_warnings_appear_in_prompt(self):
        provider = _CriticProvider('OK')
        with mock.patch.dict(os.environ, _CRITIC_ENV):
            run_critic_round(
                provider, self.spec, self.plan, self.source,
                warnings=['Score is never shown to the learner.'])
        _system, user = provider.observed_prompts[0]
        self.assertIn('Score is never shown to the learner.', user)


if __name__ == '__main__':
    unittest.main()
