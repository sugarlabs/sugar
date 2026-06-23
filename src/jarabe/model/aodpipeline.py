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
from jarabe.model.aodvalidator import validate_bundle
from jarabe.model.aodvalidator import validate_activity_source_for_request
from jarabe.model.aodvalidator import validate_project


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
    """Run prompt grounding, provider planning, generation, and validation.

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

    progress.report('validating', 0.78,
                    'Checking Python source and activity metadata')
    project_report = validate_project(result.project_path)
    if project_report.errors:
        raise PipelineError('\n'.join(project_report.errors))
    result.plan['validation'] = {
        'project_warnings': project_report.warnings,
    }
    plan_path = os.path.join(result.project_path, 'aod_plan.json')
    with open(plan_path, 'w', encoding='utf-8') as plan_file:
        json.dump(result.plan, plan_file, indent=2, sort_keys=True)
        plan_file.write('\n')

    if package_bundle:
        progress.report('packaging', 0.88,
                        'Packaging the XO bundle')
        package_generation_result(result)
        progress.report('validating', 0.94,
                        'Validating the packaged XO')

    progress.report('ready', 1.0, 'Activity project is ready')
    return result


def package_generation_result(result):
    """Build and validate the XO bundle for an already generated project."""
    if result.bundle_path and os.path.isfile(result.bundle_path):
        return result.bundle_path

    result.bundle_path = package_project(result.project_path)
    bundle_report = validate_bundle(result.bundle_path)
    if bundle_report.errors:
        raise PipelineError('\n'.join(bundle_report.errors))

    validation = result.plan.setdefault('validation', {})
    validation['bundle_warnings'] = bundle_report.warnings
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


def _redact_provider_error(error, provider):
    message = str(error)
    api_key = getattr(provider, '_api_key', '')
    if api_key:
        message = message.replace(api_key, '[redacted]')
    return message


def _generate_activity_source_with_provider(provider, spec, plan, references,
                                           progress):
    generate_source = getattr(provider, 'generate_activity_source', None)
    if not callable(generate_source):
        return None, '', 0

    validation_feedback = ''
    last_error = ''
    for attempt in range(1, _CODEGEN_ATTEMPT_LIMIT + 1):
        if attempt == 1:
            progress.report('generating', 0.56,
                            'Asking the model to write activity.py')
        else:
            progress.report(
                'generating', 0.56,
                'Asking the model to repair activity.py '
                '(attempt %d of %d)' % (attempt, _CODEGEN_ATTEMPT_LIMIT),
            )

        try:
            source = generate_source(
                build_codegen_system_prompt(spec, plan, references),
                build_codegen_user_prompt(
                    spec,
                    plan,
                    validation_feedback,
                ),
            )
        except ProviderError as error:
            return None, _redact_provider_error(error, provider), attempt
        except ValueError as error:
            last_error = str(error)
            validation_feedback = last_error
            progress.report(
                'generating', 0.56,
                'Attempt %d did not produce valid code; retrying'
                % attempt,
            )
            continue

        progress.report(
            'validating',
            0.64,
            'Model returned activity.py; validating the draft',
            {
                'draft_activity_source': source,
                'codegen_attempt': attempt,
            },
        )
        report = validate_activity_source_for_request(source, spec, plan)
        if report.valid:
            if report.warnings:
                plan.setdefault('codegen_warnings', []).extend(
                    report.warnings[:4]
                )
            return source, '', attempt

        validation_feedback = _format_codegen_feedback(report)
        last_error = (
            'Provider generated code did not pass validation: %s'
            % validation_feedback
        )

    return None, last_error, _CODEGEN_ATTEMPT_LIMIT


def _format_codegen_feedback(report):
    items = list(report.errors[:8])
    if report.warnings:
        items.extend(
            'Warning: %s' % warning
            for warning in report.warnings[:3]
        )
    return '\n'.join(items)
