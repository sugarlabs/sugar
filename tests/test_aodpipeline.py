# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from jarabe.model.aodgenerator import enrich_plan
from jarabe.model.aodllm import ProviderError
from jarabe.model.aodpipeline import generate_activity
from jarabe.model.aodpipeline import PipelineError
from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodtemplates import render_activity_source


class _FakeProvider:
    name = 'fake'
    model = 'fake-1'

    def generate_plan(self, system_prompt, user_prompt, timeout=45):
        if 'Sugar Activity API reference' not in system_prompt:
            raise AssertionError('Missing Sugar reference')
        return {
            'template': 'quiz',
            'activity_kind': 'partner fraction lab',
            'summary': 'A generated fractions quiz.',
            'learner_goal': 'Explain one fraction strategy.',
            'learner_steps': ['Try', 'Explain', 'Remix'],
            'interaction_model': 'Partners build, compare, and explain.',
            'ui_regions': ['Builder', 'Comparison', 'Reflection'],
            'state_schema': 'Saved answers and explanations.',
            'word_bank': ['fraction', 'numerator'],
        }


class _FailingProvider:
    name = 'failing'
    model = 'failing-1'

    def generate_plan(self, system_prompt, user_prompt, timeout=45):
        raise ProviderError('offline for test')


class _LeakyFailingProvider:
    name = 'leaky'
    model = 'leaky-1'

    def __init__(self):
        self._api_key = 'pipeline-secret-key'

    def generate_plan(self, system_prompt, user_prompt, timeout=45):
        raise ProviderError(
            'Provider echoed %s in an error.' % self._api_key
        )


class _CodegenProvider(_FakeProvider):

    def __init__(self, source):
        self.source = source
        self.codegen_calls = 0

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90):
        self.codegen_calls += 1
        if 'complete Python source for activity.py' not in system_prompt:
            raise AssertionError('Missing code generation instructions')
        return self.source


class _RetryCodegenProvider(_FakeProvider):

    def __init__(self, source):
        self.source = source
        self.codegen_calls = 0

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90):
        self.codegen_calls += 1
        if self.codegen_calls == 1:
            return 'class NotActivity:\n    pass\n'
        if 'Generated source must define exactly one Activity subclass.' \
                not in user_prompt:
            raise AssertionError('Missing validation feedback')
        return self.source


class _QualityRetryCodegenProvider(_FakeProvider):

    def __init__(self, generic_source, specific_source):
        self.generic_source = generic_source
        self.specific_source = specific_source
        self.codegen_calls = 0

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90):
        self.codegen_calls += 1
        if self.codegen_calls == 1:
            return self.generic_source
        if 'Drawing requests must use a Gtk.DrawingArea' not in user_prompt:
            raise AssertionError('Missing prompt-specific validation feedback')
        return self.specific_source


class _FailingCodegenProvider(_FakeProvider):

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90):
        raise ProviderError('codegen offline for test')


class TestAodPipeline(unittest.TestCase):

    def setUp(self):
        self.output_root = tempfile.mkdtemp(prefix='aod-pipeline-test-')
        self.spec = ActivitySpec(
            'Fraction Quest',
            'Make a fractions quiz.',
            'logic_math',
            'MIT',
        )

    def tearDown(self):
        shutil.rmtree(self.output_root)

    def test_provider_plan_runs_end_to_end(self):
        events = []
        provider = _CodegenProvider(_valid_activity_source(self.spec))
        result = generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
            progress_cb=lambda *event: events.append(event),
        )
        self.assertEqual('fake', result.provider)
        self.assertEqual('quiz', result.plan['template'])
        self.assertEqual('partner fraction lab', result.plan['activity_kind'])
        self.assertEqual(
            'Partners build, compare, and explain.',
            result.plan['interaction_model'],
        )
        self.assertEqual(
            ['Builder', 'Comparison', 'Reflection'],
            result.plan['ui_regions'],
        )
        self.assertTrue(os.path.isfile(result.bundle_path))
        self.assertEqual('ready', events[-1][0])

        with open(
                os.path.join(result.project_path, 'aod_plan.json'),
                encoding='utf-8') as plan_file:
            saved_plan = json.load(plan_file)
        self.assertEqual('fake', saved_plan['provider'])

    def test_provider_rag_search_is_not_template_filtered(self):
        search_calls = []

        def fake_search(query, limit=5, template='', corpus=None):
            search_calls.append({
                'query': query,
                'limit': limit,
                'template': template,
            })
            return []

        with mock.patch('jarabe.model.aodpipeline.search', fake_search):
            generate_activity(
                self.spec,
                self.output_root,
                provider=_CodegenProvider(_valid_activity_source(self.spec)),
                use_rag=True,
            )

        self.assertEqual('', search_calls[0]['template'])
        self.assertGreaterEqual(search_calls[0]['limit'], 6)

    def test_provider_failure_fails_without_template_fallback(self):
        with self.assertRaises(PipelineError) as raised:
            generate_activity(
                self.spec,
                self.output_root,
                provider=_FailingProvider(),
            )

        self.assertIn('Provider did not answer', str(raised.exception))
        self.assertIn('offline for test', str(raised.exception))

    def test_provider_key_is_redacted_from_persisted_error(self):
        provider = _LeakyFailingProvider()
        with self.assertRaises(PipelineError) as raised:
            generate_activity(
                self.spec,
                self.output_root,
                provider=provider,
            )

        message = str(raised.exception)
        self.assertNotIn(provider._api_key, message)
        self.assertIn('[redacted]', message)

    def test_provider_codegen_source_is_used(self):
        provider = _CodegenProvider(_valid_activity_source(self.spec))

        result = generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
        )

        self.assertEqual('provider', result.plan['code_source'])
        self.assertEqual(1, provider.codegen_calls)
        self.assertIn('# provider-codegen-marker', result.files['activity.py'])

    def test_provider_codegen_reports_draft_source_progress(self):
        events = []
        provider = _CodegenProvider(_valid_activity_source(self.spec))

        generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
            progress_cb=lambda *event: events.append(event),
        )

        draft_events = [
            event for event in events
            if len(event) == 4 and
            isinstance(event[3], dict) and
            event[3].get('draft_activity_source')
        ]
        self.assertEqual(1, len(draft_events))
        self.assertIn(
            '# provider-codegen-marker',
            draft_events[0][3]['draft_activity_source'],
        )

    def test_provider_codegen_retries_after_validation_error(self):
        provider = _RetryCodegenProvider(_valid_activity_source(self.spec))

        result = generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
        )

        self.assertEqual('provider', result.plan['code_source'])
        self.assertEqual(2, provider.codegen_calls)
        self.assertEqual(2, result.plan['codegen_attempts'])

    def test_provider_codegen_failure_fails_without_template_fallback(self):
        with self.assertRaises(PipelineError) as raised:
            generate_activity(
                self.spec,
                self.output_root,
                provider=_FailingCodegenProvider(),
            )

        self.assertIn('Provider could not generate valid activity code',
                      str(raised.exception))
        self.assertIn('codegen offline for test', str(raised.exception))

    def test_template_fallback_recovers_when_codegen_fails(self):
        result = generate_activity(
            self.spec,
            self.output_root,
            provider=_FailingCodegenProvider(),
            template_fallback=True,
        )

        self.assertEqual(
            'template_after_codegen_failure',
            result.plan['code_source'],
        )
        self.assertIn('codegen_fallback_reason', result.plan)
        self.assertIn(
            'codegen offline for test',
            result.plan['codegen_fallback_reason'],
        )
        self.assertTrue(os.path.isfile(
            os.path.join(result.project_path, 'activity.py')
        ))

    def test_template_fallback_recovers_when_plan_fails(self):
        result = generate_activity(
            self.spec,
            self.output_root,
            provider=_FailingProvider(),
            template_fallback=True,
        )

        self.assertEqual('local', result.provider)
        self.assertTrue(os.path.isfile(
            os.path.join(result.project_path, 'activity.py')
        ))

    def test_provider_codegen_retries_generic_source_for_prompt(self):
        spec = ActivitySpec(
            'Draw Together',
            'Make an activity where two students can draw together.',
            'creation',
            'MIT',
        )
        generic_plan = enrich_plan(spec, {
            'template': 'narrative',
            'summary': 'A generic writing activity.',
            'learner_goal': 'Write together.',
            'learner_steps': ['Write', 'Share'],
        })
        specific_plan = enrich_plan(spec, {
            'template': 'canvas',
            'summary': 'A drawing canvas for Student A and Student B.',
            'learner_goal': 'Students draw together.',
            'learner_steps': ['Student A draws', 'Student B draws'],
            'interaction_model': 'Students switch turns and draw together.',
        })
        provider = _QualityRetryCodegenProvider(
            render_activity_source(spec, generic_plan),
            render_activity_source(spec, specific_plan) +
            '\n# Student A and Student B switch turns together.\n',
        )

        result = generate_activity(
            spec,
            self.output_root,
            provider=provider,
        )

        self.assertEqual('provider', result.plan['code_source'])
        self.assertEqual(2, provider.codegen_calls)
        self.assertIn('DrawingArea', result.files['activity.py'])


def _valid_activity_source(spec):
    plan = enrich_plan(spec, {
        'template': 'quiz',
        'summary': 'Provider generated source.',
        'learner_goal': 'Practice provider code.',
        'learner_steps': ['Try', 'Explain', 'Share'],
    })
    return render_activity_source(spec, plan) + '\n# provider-codegen-marker\n'
