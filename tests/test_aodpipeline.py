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
                                 timeout=90, stream_callback=None):
        self.codegen_calls += 1
        if 'complete Python source for activity.py' not in system_prompt:
            raise AssertionError('Missing code generation instructions')
        return self.source


class _StreamingCodegenProvider(_FakeProvider):
    """Provider that emits the source as several streamed chunks."""

    def __init__(self, source, chunk_size=200):
        self.source = source
        self.chunk_size = chunk_size
        self.codegen_calls = 0
        self.observed_partials = []

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90, stream_callback=None):
        self.codegen_calls += 1
        accumulated = ''
        for index in range(0, len(self.source), self.chunk_size):
            accumulated += self.source[index:index + self.chunk_size]
            if stream_callback is not None:
                stream_callback(accumulated)
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


class _RuntimeCrashRetryProvider(_FakeProvider):
    """First source passes static checks but crashes when run."""

    def __init__(self, clean_source):
        self.clean_source = clean_source
        self.crashing_source = clean_source.replace(
            'self._build_canvas()',
            'self._build_canvas()\n'
            '        raise RuntimeError("boom-at-runtime")',
            1,
        )
        assert self.crashing_source != clean_source
        self.codegen_calls = 0
        self.observed_retry_prompts = []

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90):
        self.codegen_calls += 1
        if self.codegen_calls == 1:
            return self.crashing_source
        self.observed_retry_prompts.append(user_prompt)
        return self.clean_source


class _CriticOkProvider(_CodegenProvider):
    """Codegen provider whose critic review replies OK."""

    def __init__(self, source):
        _CodegenProvider.__init__(self, source)
        self.critic_calls = 0

    def generate_text(self, system_prompt, user_prompt, timeout=120,
                      stream_callback=None):
        if 'reviewing a Sugar activity' not in system_prompt:
            raise AssertionError('Expected the critic system prompt')
        self.critic_calls += 1
        return 'OK'


class _IconDrawingProvider(_CodegenProvider):
    """Codegen provider that also draws the activity icon."""

    ICON_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="55" height="55" '
        'viewBox="0 0 55 55">\n'
        '  <path d="M27 8 L35 30 L27 26 L19 30 Z" fill="&fill_color;" '
        'stroke="&stroke_color;" stroke-width="3" '
        'stroke-linejoin="round"/>\n'
        '</svg>'
    )

    def __init__(self, source):
        _CodegenProvider.__init__(self, source)
        self.icon_calls = 0

    def generate_text(self, system_prompt, user_prompt, timeout=120,
                      stream_callback=None):
        if 'draw icons for Sugar' not in system_prompt:
            raise AssertionError('Expected the icon system prompt')
        self.icon_calls += 1
        return self.ICON_SVG


class _FailingCodegenProvider(_FakeProvider):

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90):
        raise ProviderError('codegen offline for test')


class _EnhancingCodegenProvider(_CodegenProvider):
    """Codegen provider that also supports prompt enhancement."""

    ENHANCED = (
        'A fractions quiz where learners pick equivalent fractions.\n'
        '- Tap the fraction card that matches the target\n'
        '- Score panel and streak counter\n'
        '- Wins after ten correct answers\n'
        '- Practices equivalent fractions\n'
        '- Saves score history to the Journal')

    def __init__(self, source, fail_enhance=False):
        _CodegenProvider.__init__(self, source)
        self.enhance_calls = 0
        self.observed_plan_prompts = []
        self.fail_enhance = fail_enhance

    def generate_text(self, system_prompt, user_prompt, timeout=120,
                      stream_callback=None):
        self.enhance_calls += 1
        if self.fail_enhance:
            raise ProviderError('enhancer offline')
        if 'Sugar (GTK3) learning activity' not in system_prompt:
            raise AssertionError('Missing enhancement instructions')
        return self.ENHANCED

    def generate_plan(self, system_prompt, user_prompt, timeout=45):
        self.observed_plan_prompts.append(user_prompt)
        return _CodegenProvider.generate_plan(
            self, system_prompt, user_prompt, timeout)


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

    def test_short_prompt_is_enhanced_before_planning(self):
        events = []
        provider = _EnhancingCodegenProvider(
            _valid_activity_source(self.spec))

        result = generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
            progress_cb=lambda *event: events.append(event),
        )

        self.assertEqual(1, provider.enhance_calls)
        stages = [event[0] for event in events]
        self.assertIn('enhancing', stages)
        self.assertLess(stages.index('enhancing'), stages.index('planning'))
        metadata_events = [
            event[3] for event in events
            if len(event) > 3 and isinstance(event[3], dict)]
        self.assertTrue(any(
            meta.get('enhanced_prompt') == provider.ENHANCED
            for meta in metadata_events))
        self.assertIn(provider.ENHANCED.splitlines()[0],
                      provider.observed_plan_prompts[0])
        self.assertEqual('Make a fractions quiz.',
                         result.plan['original_prompt'])
        self.assertEqual(provider.ENHANCED, result.plan['enhanced_prompt'])
        self.assertEqual(provider.ENHANCED, result.spec.prompt)

    def test_enhancement_disabled_skips_enhancer(self):
        provider = _EnhancingCodegenProvider(
            _valid_activity_source(self.spec))
        result = generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
            enhance=False,
        )
        self.assertEqual(0, provider.enhance_calls)
        self.assertNotIn('enhanced_prompt', result.plan)

    def test_detailed_prompt_skips_enhancer(self):
        provider = _EnhancingCodegenProvider(
            _valid_activity_source(self.spec))
        long_spec = ActivitySpec(
            'Fraction Quest',
            'Make a fractions quiz. ' + 'Learners compare cards. ' * 25,
            'logic_math',
            'MIT',
        )
        generate_activity(
            long_spec,
            self.output_root,
            provider=provider,
        )
        self.assertEqual(0, provider.enhance_calls)

    def test_enhancer_failure_falls_back_to_original_prompt(self):
        provider = _EnhancingCodegenProvider(
            _valid_activity_source(self.spec), fail_enhance=True)
        result = generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
        )
        self.assertEqual(1, provider.enhance_calls)
        self.assertNotIn('enhanced_prompt', result.plan)
        self.assertIn('Make a fractions quiz.',
                      provider.observed_plan_prompts[0])

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

    def test_provider_codegen_streams_partial_source_to_progress_cb(self):
        source = _valid_activity_source(self.spec)
        provider = _StreamingCodegenProvider(source, chunk_size=400)
        drafts = []

        def progress_cb(stage, fraction, message, metadata=None):
            if isinstance(metadata, dict) and \
                    metadata.get('codegen_streaming'):
                drafts.append(metadata.get('draft_activity_source', ''))

        generate_activity(
            self.spec,
            self.output_root,
            provider=provider,
            progress_cb=progress_cb,
        )

        # At least one streamed draft should reach the progress callback,
        # and the latest streamed text should be a prefix of the final
        # accepted source (so the UI shows real partial code).
        self.assertGreaterEqual(len(drafts), 1)
        for draft in drafts:
            self.assertTrue(source.startswith(draft))
        self.assertTrue(len(drafts[-1]) > 0)

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

    def test_critic_round_runs_after_accepted_source(self):
        provider = _CriticOkProvider(_valid_activity_source(self.spec))
        with mock.patch.dict(os.environ, {'AOD_CRITIC': 'on'}):
            result = generate_activity(
                self.spec,
                self.output_root,
                provider=provider,
                enhance=False,
            )
        self.assertEqual(1, provider.critic_calls)
        self.assertEqual('ok', result.plan['critic'])
        self.assertEqual('provider', result.plan['code_source'])

    def test_ai_icon_is_used_when_provider_draws_one(self):
        provider = _IconDrawingProvider(_valid_activity_source(self.spec))
        with mock.patch.dict(os.environ, {'AOD_AI_ICON': 'on'}):
            result = generate_activity(
                self.spec,
                self.output_root,
                provider=provider,
                enhance=False,
            )
        self.assertEqual(1, provider.icon_calls)
        self.assertEqual('ai', result.plan['icon_source'])
        icon_path = os.path.join(result.project_path, 'activity',
                                 'activity.svg')
        with open(icon_path, encoding='utf-8') as icon_file:
            svg = icon_file.read()
        self.assertIn('M27 8 L35 30', svg)
        self.assertIn('<!ENTITY stroke_color', svg)

    def test_icon_falls_back_when_provider_cannot_draw(self):
        provider = _CodegenProvider(_valid_activity_source(self.spec))
        with mock.patch.dict(os.environ, {'AOD_AI_ICON': 'on'}):
            result = generate_activity(
                self.spec,
                self.output_root,
                provider=provider,
            )
        self.assertEqual('generated', result.plan['icon_source'])
        icon_path = os.path.join(result.project_path, 'activity',
                                 'activity.svg')
        with open(icon_path, encoding='utf-8') as icon_file:
            svg = icon_file.read()
        self.assertIn('<!ENTITY stroke_color', svg)
        self.assertNotIn('M27 8 L35 30', svg)

    def test_runtime_check_marker_recorded_when_disabled(self):
        provider = _CodegenProvider(_valid_activity_source(self.spec))
        with mock.patch.dict(os.environ, {'AOD_RUNTIME_CHECK': 'off'}):
            result = generate_activity(
                self.spec,
                self.output_root,
                provider=provider,
            )
        self.assertEqual('skipped: disabled', result.plan['runtime_check'])

    @unittest.skipUnless(
        os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'),
        'needs a display')
    def test_provider_codegen_retries_after_runtime_crash(self):
        provider = _RuntimeCrashRetryProvider(
            _valid_activity_source(self.spec))
        with mock.patch.dict(os.environ, {'AOD_RUNTIME_CHECK': 'on'}):
            result = generate_activity(
                self.spec,
                self.output_root,
                provider=provider,
            )
        self.assertEqual(2, provider.codegen_calls)
        self.assertIn('crashed when run',
                      provider.observed_retry_prompts[0])
        self.assertIn('boom-at-runtime',
                      provider.observed_retry_prompts[0])
        self.assertEqual('provider', result.plan['code_source'])
        self.assertEqual('passed', result.plan['runtime_check'])


def _valid_activity_source(spec):
    plan = enrich_plan(spec, {
        'template': 'quiz',
        'summary': 'Provider generated source.',
        'learner_goal': 'Practice provider code.',
        'learner_steps': ['Try', 'Explain', 'Share'],
    })
    return render_activity_source(spec, plan) + '\n# provider-codegen-marker\n'
