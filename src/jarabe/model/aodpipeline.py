# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import time

from sugar3 import env

from jarabe.model.aodcodegen import build_codegen_system_prompt
from jarabe.model.aodcodegen import build_codegen_user_prompt
from jarabe.model.aodgenerator import build_plan
from jarabe.model.aodgenerator import create_prototype_activity
from jarabe.model.aodgenerator import enrich_plan
from jarabe.model.aodgenerator import normalize_plan
from jarabe.model.aodgenerator import package_project
from jarabe.model.aodgenerator import read_project_files
from jarabe.model.aodllm import ProviderError
from jarabe.model.aodllm import get_configured_provider
from jarabe.model.aodprompts import build_system_prompt
from jarabe.model.aodprompts import build_user_prompt
from jarabe.model.aodrag import build_corpus
from jarabe.model.aodrag import search
from jarabe.model.aodrefine import build_refine_system_prompt
from jarabe.model.aodrefine import build_refine_user_prompt
from jarabe.model.aodrefine import parse_search_replace
from jarabe.model.aodrefine import apply_patches


class PipelineError(Exception):
    pass


_LOCAL_PROVIDER_NAMES = ('local', 'local-template')


def _env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


_CODEGEN_ATTEMPT_LIMIT = _env_int('AOD_CODEGEN_ATTEMPT_LIMIT', 3)


def generate_activity(spec, output_root=None, provider=None,
                      provider_name='default', use_rag=True,
                      progress_cb=None, pace=False, package_bundle=True,
                      template_fallback=False):
    """Run prompt grounding, provider planning, and generation.

    When template_fallback is True and the provider fails to deliver valid
    activity code, the pipeline renders activity.py from the local template
    using the provider's plan instead of raising. The plan records
    codegen_fallback_reason so callers can surface what happened to the user.
    The default stays False so the pipeline's strict no-fallback contract
    remains the default for tests and CLI callers that want to fail fast.
    """
    progress = _PipelineProgress(progress_cb, pace)
    progress.report('planning', 0.06,
                    'Reading the prompt and classroom goal')
    selected_provider = provider
    provider_error = ''
    references = []
    provider_required = (
        selected_provider is not None or
        provider_name not in _LOCAL_PROVIDER_NAMES
    )

    if selected_provider is None and provider_name not in (
            'local', 'local-template'):
        try:
            selected_provider = get_configured_provider(provider_name)
        except ProviderError as error:
            provider_error = str(error)

    if provider_required and selected_provider is None:
        if provider_error:
            raise PipelineError(
                'Configured model is required for RAG generation: %s'
                % provider_error
            )
        raise PipelineError(
            'No configured model is available. Save an API key and choose '
            'a provider before generating.'
        )

    if selected_provider is not None:
        use_rag = True

    if selected_provider is not None:
        progress.report('planning', 0.16,
                        'Preparing Sugar example context for the model')
    else:
        progress.report('planning', 0.16,
                        'Drafting local activity structure')
        local_plan = build_plan(spec)

    if use_rag:
        if selected_provider is not None:
            progress.report('grounding', 0.24,
                            'Retrieving Sugar activity examples for context')
            template_filter = ''
            reference_limit = 10
        else:
            progress.report('grounding', 0.24,
                            'Searching Sugar activity patterns')
            template_filter = local_plan['template']
            reference_limit = 4
        corpus = build_corpus()
        references = search(
            spec.prompt,
            limit=reference_limit,
            template=template_filter,
            corpus=corpus,
        )
        progress.report('grounding', 0.34,
                        'Selecting useful Sugar API and interaction patterns')

    if selected_provider is not None:
        system_prompt = build_system_prompt(spec, references)
        user_prompt = build_user_prompt(spec)
        progress.report('provider', 0.43,
                        'Asking the configured model to plan from RAG context')
        try:
            provider_plan = selected_provider.generate_plan(
                system_prompt,
                user_prompt,
            )
            plan = normalize_plan(spec, provider_plan)
            provider_used = selected_provider.name
            model_used = selected_provider.model
            progress.report('provider', 0.52,
                            'Checking the model plan')
        except (ProviderError, ValueError) as error:
            provider_error = _redact_provider_error(
                error,
                selected_provider,
            )
            if not template_fallback:
                raise PipelineError(
                    'Provider did not answer: %s' % provider_error
                )
            # Provider unavailable but caller asked for graceful degradation:
            # build the activity from the local template so the user still
            # gets something usable without burning further API credits.
            progress.report(
                'provider', 0.46,
                'Provider did not answer; using local template instead',
            )
            plan = build_plan(spec)
            provider_used = 'local'
            model_used = ''
            selected_provider = None
    else:
        plan = local_plan
        provider_used = 'local'
        model_used = ''
        progress.report('provider', 0.43,
                        'Using the local activity builder')

    if output_root is None:
        output_root = env.get_profile_path(os.path.join('aod', 'projects'))

    plan = enrich_plan(spec, plan, references)
    plan = dict(plan)
    plan['provider'] = provider_used
    plan['model'] = model_used
    if provider_error:
        plan['provider_fallback_reason'] = provider_error

    activity_source = None
    plan['code_source'] = 'template'
    if selected_provider is not None and provider_used != 'local':
        activity_source, code_error, code_attempts = (
            _generate_activity_source_with_provider(
                selected_provider,
                spec,
                plan,
                references,
                progress,
            )
        )
        plan['codegen_attempts'] = code_attempts
        if activity_source:
            plan['code_source'] = 'provider'
            plan['codegen_provider'] = selected_provider.name
            plan['codegen_model'] = selected_provider.model
        elif code_error:
            if template_fallback:
                plan['codegen_fallback_reason'] = code_error
                plan['code_source'] = 'template_after_codegen_failure'
                progress.report(
                    'generating', 0.58,
                    'Provider code failed validation; using local '
                    'template instead',
                )
            else:
                raise PipelineError(
                    'Provider could not generate valid activity code: %s'
                    % code_error
                )
        else:
            # Provider only supports planning, not code generation.
            # Fall back to the local template renderer.
            plan['codegen_fallback_reason'] = (
                'Provider does not support activity source generation; '
                'using template renderer.'
            )

    progress.report('generating', 0.60,
                    'Expanding the plan into activity screens')
    result = create_prototype_activity(
        spec,
        output_root,
        plan=plan,
        package_bundle=False,
        activity_source=activity_source,
    )
    result.provider = provider_used
    result.model = model_used

    progress.report('assembling', 0.78,
                    'Assembling the activity project')
    plan_path = os.path.join(result.project_path, 'aod_plan.json')
    with open(plan_path, 'w', encoding='utf-8') as plan_file:
        json.dump(result.plan, plan_file, indent=2, sort_keys=True)
        plan_file.write('\n')

    if package_bundle:
        progress.report('packaging', 0.88,
                        'Packaging the XO bundle')
        package_generation_result(result)

    progress.report('ready', 1.0, 'Activity project is ready')
    return result


def package_generation_result(result):
    """Build the XO bundle for an already generated project."""
    if result.bundle_path and os.path.isfile(result.bundle_path):
        return result.bundle_path

    result.bundle_path = package_project(result.project_path)
    plan_path = os.path.join(result.project_path, 'aod_plan.json')
    with open(plan_path, 'w', encoding='utf-8') as plan_file:
        json.dump(result.plan, plan_file, indent=2, sort_keys=True)
        plan_file.write('\n')
    result.files = read_project_files(result.project_path)
    return result.bundle_path


def _progress(callback, stage, fraction, message, metadata=None):
    if callback is not None:
        try:
            if metadata is None:
                callback(stage, fraction, message)
            else:
                callback(stage, fraction, message, metadata)
        except TypeError:
            callback(stage, fraction, message)


class _PipelineProgress:
    """Progress reporter with optional UI pacing for real service jobs."""

    def __init__(self, callback, pace=False):
        self._callback = callback
        self._pace = pace

    def report(self, stage, fraction, message, metadata=None):
        _progress(self._callback, stage, fraction, message, metadata)
        if not self._pace:
            return

        end_time = time.time() + 0.45
        while time.time() < end_time:
            time.sleep(0.09)
            _progress(self._callback, stage, fraction, message)

    def report_immediate(self, stage, fraction, message, metadata=None):
        """Report progress without the pacing sleep.

        Used for streaming token updates where blocking the response
        thread would slow down how fast new tokens arrive.
        """
        _progress(self._callback, stage, fraction, message, metadata)


def _redact_provider_error(error, provider):
    message = str(error)
    api_key = getattr(provider, '_api_key', '')
    if api_key:
        message = message.replace(api_key, '[redacted]')
    return message


_STREAM_REPORT_INTERVAL_SECONDS = 0.08


def _make_codegen_stream_callback(progress, attempt):
    """Build a stream callback that forwards partial codegen text to the UI.

    The callback is debounced so the UI is not repainted on every single
    token; intermediate updates land at most once per ~80ms. The first
    and final chunks are always reported so the preview lights up
    immediately and reflects the final draft.
    """
    state = {'last_emit': 0.0, 'last_text': ''}

    def report_partial(partial_text):
        if not isinstance(partial_text, str):
            return
        state['last_text'] = partial_text
        now = time.time()
        if now - state['last_emit'] < _STREAM_REPORT_INTERVAL_SECONDS:
            return
        state['last_emit'] = now
        progress.report_immediate(
            'generating',
            0.58,
            'Streaming activity.py from the model '
            '(%d chars)' % len(partial_text),
            {
                'draft_activity_source': partial_text,
                'codegen_attempt': attempt,
                'codegen_streaming': True,
            },
        )

    return report_partial


def _generate_activity_source_with_provider(provider, spec, plan, references,
                                           progress):
    generate_source = getattr(provider, 'generate_activity_source', None)
    if not callable(generate_source):
        return None, '', 0

    progress.report('generating', 0.56,
                    'Asking the model to write activity.py')

    stream_callback = _make_codegen_stream_callback(progress, 1)
    system_prompt = build_codegen_system_prompt(spec, plan, references)
    user_prompt = build_codegen_user_prompt(spec, plan)
    try:
        try:
            source = generate_source(
                system_prompt,
                user_prompt,
                stream_callback=stream_callback,
            )
        except TypeError:
            # Older providers / test doubles may not accept
            # stream_callback; fall back to the non-streaming call.
            source = generate_source(system_prompt, user_prompt)
    except ProviderError as error:
        return None, _redact_provider_error(error, provider), 1
    except ValueError as error:
        return None, str(error), 1

    progress.report(
        'generating',
        0.64,
        'Model returned activity.py',
        {
            'draft_activity_source': source,
            'codegen_attempt': 1,
        },
    )
    return source, '', 1


def _has_refinement(provider):
    """Check if a provider supports the raw text generation needed for refinement."""
    generate_text = getattr(provider, 'generate_text', None)
    return callable(generate_text)


def refine_activity(spec, current_source, current_plan, output_root,
                    provider=None, provider_name='default',
                    progress_cb=None, pace=False,
                    package_bundle=False):
    """Refine an existing activity.py using SEARCH/REPLACE blocks.

    Tries the cheap SEARCH/REPLACE path first (~1k output tokens).  If
    the model requests FULLREGEN, or any patch fails to match, falls
    back to full regeneration (skipping the planner call by reusing
    current_plan).

    Returns a GenerationResult like generate_activity().
    """
    progress = _PipelineProgress(progress_cb, pace)
    selected_provider = provider
    if selected_provider is None and provider_name not in (
            'local', 'local-template'):
        try:
            selected_provider = get_configured_provider(provider_name)
        except ProviderError as error:
            raise PipelineError(
                'Configured model is required for refinement: %s' % error
            )

    if selected_provider is None:
        raise PipelineError(
            'A configured model is required for refinement.'
        )

    generate_source = getattr(
        selected_provider, 'generate_activity_source', None)
    if not callable(generate_source):
        raise PipelineError(
            'Provider does not support activity source generation.'
        )

    if output_root is None:
        output_root = env.get_profile_path(os.path.join('aod', 'projects'))

    refinement_request = spec.prompt
    plan_context = json.dumps({
        'template': current_plan.get('template', ''),
        'activity_kind': current_plan.get('activity_kind', ''),
        'interaction_model': current_plan.get('interaction_model', ''),
    }, indent=2)

    progress.report('generating', 0.30,
                    'Asking the model for targeted edits')

    generate_text = getattr(selected_provider, 'generate_text', None)
    if not callable(generate_text):
        generate_text = None

    patched_source = None
    refine_method = 'search_replace'
    try:
        if generate_text is not None:
            response = generate_text(
                build_refine_system_prompt(),
                build_refine_user_prompt(
                    current_source,
                    refinement_request,
                    plan_context=plan_context,
                ),
            )
        else:
            response = None
            refine_method = 'full_regen'
    except (ProviderError, ValueError) as error:
        progress.report(
            'generating', 0.35,
            'Edit request failed; falling back to full regeneration')
        response = None
        refine_method = 'full_regen'

    if response is not None:
        try:
            patches = parse_search_replace(response)
        except ValueError:
            patches = None
            refine_method = 'full_regen'

        if patches is None:
            refine_method = 'full_regen'
            progress.report(
                'generating', 0.40,
                'Model requested full regeneration')
        else:
            progress.report(
                'generating', 0.55,
                'Applying %d targeted edits' % len(patches),
            )
            patched, applied, failed = apply_patches(
                current_source, patches)
            if failed > 0 or applied == 0:
                progress.report(
                    'generating', 0.45,
                    '%d edits matched, %d failed; '
                    'falling back to full regeneration'
                    % (applied, failed),
                )
                refine_method = 'full_regen'
                patched_source = None
            else:
                patched_source = patched
                progress.report(
                    'generating', 0.70,
                    'Edits applied successfully')

    if patched_source is None:
        progress.report('generating', 0.55,
                        'Regenerating full activity.py')
        activity_source, code_error, code_attempts = (
            _generate_activity_source_with_provider(
                selected_provider,
                spec,
                current_plan,
                (),
                progress,
            )
        )
        if not activity_source:
            raise PipelineError(
                'Refinement failed: %s' % (code_error or 'no source')
            )
        patched_source = activity_source

    plan = dict(current_plan)
    plan['code_source'] = 'provider'
    plan['refine_method'] = refine_method
    plan['codegen_provider'] = selected_provider.name
    plan['codegen_model'] = selected_provider.model

    progress.report('generating', 0.80,
                    'Assembling the refined project')
    result = create_prototype_activity(
        spec,
        output_root,
        plan=plan,
        package_bundle=False,
        activity_source=patched_source,
    )
    result.provider = selected_provider.name
    result.model = selected_provider.model

    plan_path = os.path.join(result.project_path, 'aod_plan.json')
    with open(plan_path, 'w', encoding='utf-8') as plan_file:
        json.dump(result.plan, plan_file, indent=2, sort_keys=True)
        plan_file.write('\n')

    if package_bundle:
        progress.report('packaging', 0.95, 'Packaging the XO bundle')
        package_generation_result(result)

    progress.report('ready', 1.0, 'Refined activity is ready')
    return result
