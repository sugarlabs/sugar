# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
import os
import threading

from jarabe.model.aodcredentials import AODCredentialStore
from jarabe.model.aodcredentials import CredentialStoreError
from jarabe.model.aodgenerator import restore_generation_result
from jarabe.model.aodjobs import AODJob
from jarabe.model.aodjobs import AODJobStore
from jarabe.model.aodjobs import STATUS_FINISHED
from jarabe.model.aodjobs import STATUS_GENERATING
from jarabe.model.aodjobs import STATUS_GROUNDING
from jarabe.model.aodjobs import STATUS_PACKAGING
from jarabe.model.aodjobs import STATUS_PLANNING
from jarabe.model.aodjobs import STATUS_PROVIDER
from jarabe.model.aodjobs import STATUS_QUEUED
from jarabe.model.aodjobs import STATUS_VALIDATING
from jarabe.model.aodllm import create_provider
from jarabe.model.aodllm import get_default_provider_name
from jarabe.model.aodllm import get_local_provider_name
from jarabe.model.aodllm import get_provider_statuses
from jarabe.model.aodllm import normalize_provider_name
from jarabe.model.aodpipeline import generate_activity
from jarabe.model.aodqueue import AODJobQueue
from jarabe.model.aodsessions import AODMessage
from jarabe.model.aodsessions import AODRevision
from jarabe.model.aodsessions import AODSessionStore
from jarabe.model.aodsessions import ROLE_ASSISTANT
from jarabe.model.aodsessions import ROLE_USER
from jarabe.model.aodsessions import TYPE_ERROR
from jarabe.model.aodsessions import TYPE_PROMPT
from jarabe.model.aodsessions import TYPE_RESULT
from jarabe.model.aodsessions import TYPE_STATUS


class JobCancelled(Exception):
    pass


class AODService:
    """Local backend service for generated Sugar activities."""

    def __init__(self, job_store=None, worker_count=1,
                 credential_store=None, session_store=None):
        self._store = job_store or AODJobStore()
        self._credential_store = credential_store or AODCredentialStore()
        self._session_store = session_store or AODSessionStore()
        self._lock = threading.RLock()
        self._callbacks = {}
        self._jobs = {}
        self._provider_overrides = {}
        self._job_providers = {}
        self._load_jobs()
        self._queue = AODJobQueue(self._run_job, worker_count=worker_count)

    def submit_activity(self, spec, provider_name='default', use_rag=True,
                        output_root=None, callback=None, session_id='',
                        parent_revision_id='', user_prompt=None):
        errors = spec.validate()
        if errors:
            raise ValueError('\n'.join(errors))

        provider_name = normalize_provider_name(provider_name)
        if provider_name == 'default':
            provider_name = self.preferred_provider_name()
        session = self._ensure_session(spec, session_id)
        prompt_text = user_prompt or spec.prompt
        job = AODJob.create(
            spec,
            provider_name=provider_name,
            use_rag=use_rag,
            output_root=output_root,
            session_id=session.session_id,
            parent_revision_id=parent_revision_id,
            user_prompt=prompt_text,
        )
        if callback is not None:
            self.watch(job.job_id, callback)

        with self._lock:
            self._jobs[job.job_id] = job
            provider = self._provider_overrides.get(provider_name)
            if provider is None:
                provider = self._load_saved_provider(provider_name)
            if provider is not None:
                self._job_providers[job.job_id] = provider
            self._store.save(job)

        self._record_user_prompt(session.session_id, job, prompt_text)
        self._notify(job)
        self._queue.submit(job)
        return job

    def watch(self, job_id, callback):
        with self._lock:
            self._callbacks.setdefault(job_id, []).append(callback)

    def unwatch(self, job_id, callback=None):
        with self._lock:
            if job_id not in self._callbacks:
                return
            if callback is None:
                del self._callbacks[job_id]
                return
            self._callbacks[job_id] = [
                item for item in self._callbacks[job_id]
                if item != callback
            ]
            if not self._callbacks[job_id]:
                del self._callbacks[job_id]

    def get_job(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self):
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda job: job.created_at,
                reverse=True,
            )

    def get_session(self, session_id):
        return self._session_store.load(session_id)

    def list_sessions(self):
        return self._session_store.list_sessions()

    def cancel_job(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.is_terminal():
                return False
            job.request_cancel()
            if job.status == STATUS_QUEUED:
                job.cancel()
            self._store.save(job)
        self._notify(job)
        return True

    def provider_statuses(self):
        statuses = get_provider_statuses()
        with self._lock:
            overrides = dict(self._provider_overrides)

        for status in statuses:
            provider = overrides.get(status['name'])
            credentials = self._credential_store.provider_status(
                status['name']
            ) if status['name'] in (
                'gemini', 'openai', 'deepseek', 'qwen', 'moonshot',
                'opencode', 'opencode-go', 'freemodel', 'claude', 'ollama') else {}
            ollama_configured = status['name'] == 'ollama' and any((
                credentials.get('model'),
                credentials.get('endpoint'),
            ))
            if provider is not None:
                status['available'] = True
                status['configured'] = True
                status['model'] = provider.model
                status['reason'] = ''
            elif credentials.get('has_api_key') or ollama_configured:
                status['available'] = True
                status['configured'] = True
                status['model'] = credentials.get('model') or status['model']
                status['reason'] = ''
        return statuses

    def configure_provider(self, provider_name, api_key=None, model=None,
                           endpoint=None, persist=False):
        provider_name = normalize_provider_name(provider_name)
        if persist:
            self._credential_store.save_provider(
                provider_name,
                api_key=api_key,
                model=model,
                endpoint=endpoint,
            )

        saved = self._credential_store.load_provider(provider_name)
        provider = create_provider(
            provider_name,
            api_key=api_key or saved['api_key'] or None,
            model=model or saved['model'] or None,
            endpoint=endpoint or saved['endpoint'] or None,
        )
        if provider is None:
            return None
        return self.register_provider(provider)

    def provider_credential_status(self, provider_name):
        provider_name = normalize_provider_name(provider_name)
        return self._credential_store.provider_status(provider_name)

    def remove_provider_api_key(self, provider_name):
        provider_name = normalize_provider_name(provider_name)
        removed = self._credential_store.remove_api_key(provider_name)
        self.clear_provider(provider_name)
        return removed

    def register_provider(self, provider):
        provider_name = normalize_provider_name(provider.name)
        if provider_name in ('default', 'local-template'):
            raise ValueError(
                'Only concrete LLM providers can be registered.'
            )
        if not callable(getattr(provider, 'generate_plan', None)):
            raise TypeError('Provider must define generate_plan().')

        with self._lock:
            self._provider_overrides[provider_name] = provider
        return provider

    def clear_provider(self, provider_name):
        provider_name = normalize_provider_name(provider_name)
        with self._lock:
            self._provider_overrides.pop(provider_name, None)

    def has_runtime_provider(self, provider_name):
        provider_name = normalize_provider_name(provider_name)
        with self._lock:
            return provider_name in self._provider_overrides

    def preferred_local_provider_name(self):
        if self.has_runtime_provider('ollama'):
            return 'ollama'
        ollama = self._credential_store.provider_status('ollama')
        if ollama['model'] or ollama['endpoint']:
            return 'ollama'
        return get_local_provider_name()

    def preferred_provider_name(self):
        saved_provider = \
            self._credential_store.get_default_provider_name()
        if saved_provider:
            return saved_provider
        return get_default_provider_name()

    def shutdown(self, wait=True):
        self._queue.shutdown(wait=wait)

    def _load_jobs(self):
        for job in self._store.list_jobs():
            if not job.is_terminal():
                job.fail('Sugar restarted before this job finished.')
                self._store.save(job)
            elif job.status == STATUS_FINISHED:
                try:
                    job.result = restore_generation_result(
                        job.spec,
                        job.result_summary,
                    )
                except (OSError, TypeError, ValueError):
                    logging.exception(
                        'Could not restore Activity-on-Demand result'
                    )
                    job.result = None
                if job.result is None:
                    job.fail(
                        'Generated activity artifacts are no longer available.'
                    )
                    self._store.save(job)
            self._jobs[job.job_id] = job

    def _ensure_session(self, spec, session_id=''):
        if session_id:
            session = self._session_store.load(session_id)
            if session is not None:
                return session
        return self._session_store.create_session(spec)

    def _record_user_prompt(self, session_id, job, prompt_text):
        message = AODMessage.create(
            ROLE_USER,
            prompt_text,
            message_type=TYPE_PROMPT,
            job_id=job.job_id,
        )
        self._session_store.append_message(session_id, message)

        status = AODMessage.create(
            ROLE_ASSISTANT,
            'Generating Sugar activity...',
            message_type=TYPE_STATUS,
            job_id=job.job_id,
        )
        self._session_store.append_message(session_id, status)

    def _run_job(self, job):
        try:
            self._run_job_inner(job)
        finally:
            with self._lock:
                self._job_providers.pop(job.job_id, None)

    def _load_saved_provider(self, provider_name):
        if provider_name not in ('gemini', 'openai', 'openrouter',
                                 'deepseek', 'qwen', 'moonshot', 'opencode',
                                 'opencode-go', 'freemodel', 'claude',
                                 'ollama'):
            return None

        try:
            saved = self._credential_store.load_provider(provider_name)
            if provider_name != 'ollama' and not saved['api_key']:
                return None
            if provider_name == 'ollama' and not (
                    saved['model'] or saved['endpoint']):
                return None

            return create_provider(
                provider_name,
                api_key=saved['api_key'] or None,
                model=saved['model'] or None,
                endpoint=saved['endpoint'] or None,
            )
        except (CredentialStoreError, TypeError, ValueError):
            logging.exception(
                'Could not load saved Activity-on-Demand provider'
            )
            return None

    def _run_job_inner(self, job):
        if job.cancel_requested:
            self._mark_cancelled(job)
            return

        job.mark_started()
        self._set_progress(
            job,
            STATUS_PLANNING,
            STATUS_PLANNING,
            0.0,
            'Starting generation',
        )

        try:
            with self._lock:
                provider = self._job_providers.get(job.job_id)
            if job.parent_revision_id:
                result = self._run_refinement_job(job, provider)
            else:
                result = generate_activity(
                    job.spec,
                    output_root=job.output_root or None,
                    provider=provider,
                    provider_name=job.provider_name,
                    use_rag=job.use_rag,
                    progress_cb=lambda stage, fraction, message, metadata=None:
                        self._pipeline_progress(
                            job,
                            stage,
                            fraction,
                            message,
                            metadata,
                        ),
                    pace=True,
                    package_bundle=False,
                )
        except JobCancelled:
            self._mark_cancelled(job)
            return
        except Exception as error:
            logging.exception('Activity-on-Demand job failed')
            self._mark_failed(job, error)
            return

        if job.cancel_requested:
            self._mark_cancelled(job)
            return

        with self._lock:
            job.finish(result)
            revision = AODRevision.create(
                job.job_id,
                job.user_prompt or job.spec.prompt,
                job.result_summary,
                parent_revision_id=job.parent_revision_id,
            )
            job.result_summary['session_id'] = job.session_id
            job.result_summary['revision_id'] = revision.revision_id
            revision.result_summary = dict(job.result_summary)
            self._store.save(job)
        self._record_finished_revision(job, revision)
        self._notify(job)

    def _pipeline_progress(self, job, stage, fraction, message,
                           metadata=None):
        if job.cancel_requested:
            raise JobCancelled()

        status = _status_for_pipeline_stage(stage)
        self._set_progress(job, status, stage, fraction, message, metadata)

    def _run_refinement_job(self, job, provider):
        """Run a refinement using SEARCH/REPLACE + full-regen fallback.

        For LLM providers, tries cheap SEARCH/REPLACE blocks before
        falling back to full regen.  For local-template, falls back
        to the standard generation pipeline.
        """
        if job.provider_name in ('local', 'local-template') and \
                provider is None:
            return generate_activity(
                job.spec,
                output_root=job.output_root or None,
                provider=None,
                provider_name='local-template',
                use_rag=job.use_rag,
                progress_cb=lambda stage, fraction, message, metadata=None:
                    self._pipeline_progress(
                        job, stage, fraction, message, metadata),
                pace=True,
                package_bundle=False,
            )

        from jarabe.model.aodpipeline import refine_activity
        from jarabe.model.aodpipeline import PipelineError

        session = self._session_store.load(job.session_id)
        if session is None:
            raise PipelineError(
                'Could not find the session for refinement.'
            )

        parent_revision = None
        for rev in session.revisions:
            if rev.revision_id == job.parent_revision_id:
                parent_revision = rev
                break
        if parent_revision is None:
            raise PipelineError(
                'Could not find the parent revision for refinement.'
            )

        summary = parent_revision.result_summary or {}
        project_path = summary.get('project_path', '')
        if not project_path:
            raise PipelineError(
                'Parent revision has no project path.'
            )

        source_path = os.path.join(project_path, 'activity.py')
        try:
            with open(source_path, encoding='utf-8') as f:
                current_source = f.read()
        except OSError:
            raise PipelineError(
                'Could not read the current activity.py for refinement.'
            )

        plan_path = os.path.join(project_path, 'aod_plan.json')
        try:
            with open(plan_path, encoding='utf-8') as f:
                current_plan = json.load(f)
        except (OSError, ValueError):
            current_plan = {}

        return refine_activity(
            job.spec,
            current_source,
            current_plan,
            job.output_root or None,
            provider=provider,
            provider_name=job.provider_name,
            progress_cb=lambda stage, fraction, message, metadata=None:
                self._pipeline_progress(
                    job, stage, fraction, message, metadata),
            pace=True,
            package_bundle=False,
        )

    def _set_progress(self, job, status, stage, progress, message,
                      metadata=None):
        with self._lock:
            job.update_progress(status, stage, progress, message)
            if isinstance(metadata, dict):
                draft_source = metadata.get('draft_activity_source')
                if isinstance(draft_source, str) and draft_source:
                    job.draft_activity_source = draft_source
            self._store.save(job)
        self._notify(job)

    def _mark_failed(self, job, error):
        with self._lock:
            job.fail(error)
            self._store.save(job)
        self._record_failed_message(job)
        self._notify(job)

    def _mark_cancelled(self, job):
        with self._lock:
            job.cancel()
            self._store.save(job)
        self._notify(job)

    def _notify(self, job):
        with self._lock:
            callbacks = list(self._callbacks.get(job.job_id, ()))

        for callback in callbacks:
            try:
                callback(job)
            except Exception:
                logging.exception('Activity-on-Demand callback failed')

    def _record_finished_revision(self, job, revision):
        if not job.session_id:
            return

        self._session_store.append_revision(job.session_id, revision)
        summary = job.result_summary
        provider = summary.get('provider', job.provider_name)
        model = summary.get('model', '')
        if model:
            provider = '%s / %s' % (provider, model)

        message = AODMessage.create(
            ROLE_ASSISTANT,
            ('Generated "%(name)s" with %(provider)s. '
             'This revision is ready to preview, refine, export, or '
             'install.') % {
                 'name': summary.get('activity_name', job.spec.name),
                 'provider': provider,
             },
            message_type=TYPE_RESULT,
            job_id=job.job_id,
            revision_id=revision.revision_id,
        )
        self._session_store.append_message(job.session_id, message)

    def _record_failed_message(self, job):
        if not job.session_id:
            return

        message = AODMessage.create(
            ROLE_ASSISTANT,
            'Generation failed: %s' % job.error,
            message_type=TYPE_ERROR,
            job_id=job.job_id,
        )
        self._session_store.append_message(job.session_id, message)


def _status_for_pipeline_stage(stage):
    statuses = {
        'planning': STATUS_PLANNING,
        'grounding': STATUS_GROUNDING,
        'provider': STATUS_PROVIDER,
        'generating': STATUS_GENERATING,
        'validating': STATUS_VALIDATING,
        'packaging': STATUS_PACKAGING,
        'ready': STATUS_PACKAGING,
    }
    return statuses.get(stage, STATUS_GENERATING)


_service = None
_service_lock = threading.Lock()


def get_service():
    global _service
    with _service_lock:
        if _service is None:
            _service = AODService()
        return _service
