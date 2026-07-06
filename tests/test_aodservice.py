# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import shutil
import tempfile
import time
import unittest
import zipfile

from jarabe.model.aodcredentials import AODCredentialStore
from jarabe.model.aodgenerator import enrich_plan
from jarabe.model.aodpipeline import package_generation_result
from jarabe.model.aodjobs import AODJobStore
from jarabe.model.aodjobs import STATUS_FAILED
from jarabe.model.aodjobs import STATUS_FINISHED
from jarabe.model.aodsessions import AODSessionStore
from jarabe.model.aodsessions import ROLE_ASSISTANT
from jarabe.model.aodsessions import ROLE_USER
from jarabe.model.aodsessions import TYPE_RESULT
from jarabe.model.aodservice import AODService
from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodtemplates import render_activity_source


class TestAodService(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='aod-service-test-')
        self.project_root = os.path.join(self.root, 'projects')
        self.job_root = os.path.join(self.root, 'jobs')
        self.session_root = os.path.join(self.root, 'sessions')
        self.store = AODJobStore(self.job_root)
        self.session_store = AODSessionStore(self.session_root)
        self.secret_backend = _MemorySecretBackend()
        self.credential_store = AODCredentialStore(
            os.path.join(self.root, 'credentials'),
            secret_backend=self.secret_backend,
        )
        self.service = AODService(
            self.store,
            worker_count=1,
            credential_store=self.credential_store,
            session_store=self.session_store,
        )

    def tearDown(self):
        self.service.shutdown()
        shutil.rmtree(self.root)

    def test_submit_activity_runs_job_and_persists_summary(self):
        events = []
        spec = ActivitySpec(
            'Queue Demo',
            'Create a quiz about queues.',
            'logic_math',
            'MIT',
            template='quiz',
        )

        job = self.service.submit_activity(
            spec,
            provider_name='local-template',
            output_root=self.project_root,
            callback=lambda updated: events.append(updated.status),
        )
        finished = self._wait_for_terminal(job.job_id)

        self.assertEqual(STATUS_FINISHED, finished.status)
        self.assertTrue(os.path.isdir(finished.result.project_path))
        self.assertEqual('', finished.result.bundle_path)
        self.assertIn(STATUS_FINISHED, events)

        persisted = self.store.load(job.job_id)
        self.assertEqual(STATUS_FINISHED, persisted.status)
        self.assertEqual(
            finished.result.bundle_id,
            persisted.result_summary['bundle_id'],
        )
        session = self.service.get_session(finished.session_id)
        self.assertIsNotNone(session)
        self.assertEqual(finished.result_summary['revision_id'],
                         session.active_revision_id)
        self.assertEqual(1, len(session.revisions))
        self.assertEqual(ROLE_USER, session.messages[0].role)
        self.assertTrue(any(
            message.role == ROLE_ASSISTANT and
            message.message_type == TYPE_RESULT and
            message.revision_id == session.active_revision_id
            for message in session.messages
        ))

    def test_unwatch_removes_bound_method_callback(self):
        observer = _Observer()
        self.service.watch('job-id', observer.callback)
        self.service.unwatch('job-id', observer.callback)
        self.assertNotIn('job-id', self.service._callbacks)

    def test_finished_job_restores_result_after_service_restart(self):
        spec = ActivitySpec(
            'Restore Demo',
            'Create a writing activity.',
            'creation',
            'MIT',
            template='narrative',
        )
        job = self.service.submit_activity(
            spec,
            provider_name='local-template',
            output_root=self.project_root,
        )
        finished = self._wait_for_terminal(job.job_id)
        self.assertEqual(STATUS_FINISHED, finished.status)

        self.service.shutdown()
        self.service = AODService(
            self.store,
            worker_count=1,
            credential_store=self.credential_store,
            session_store=self.session_store,
        )
        restored = self.service.get_job(job.job_id)

        self.assertEqual(STATUS_FINISHED, restored.status)
        self.assertIsNotNone(restored.result)
        self.assertEqual(
            finished.result.bundle_id,
            restored.result.bundle_id,
        )
        self.assertIn('activity.py', restored.result.files)

    def test_missing_artifacts_mark_restored_job_failed(self):
        spec = ActivitySpec(
            'Missing Demo',
            'Create a simple quiz.',
            'logic_math',
            'MIT',
            template='quiz',
        )
        job = self.service.submit_activity(
            spec,
            provider_name='local-template',
            output_root=self.project_root,
        )
        finished = self._wait_for_terminal(job.job_id)
        shutil.rmtree(finished.result.project_path)

        self.service.shutdown()
        self.service = AODService(
            self.store,
            worker_count=1,
            credential_store=self.credential_store,
            session_store=self.session_store,
        )
        restored = self.service.get_job(job.job_id)

        self.assertEqual(STATUS_FAILED, restored.status)
        self.assertIsNone(restored.result)
        self.assertIn('no longer available', restored.error)

    def test_runtime_provider_runs_without_persisting_its_secret(self):
        secret = 'aod-session-secret-must-not-be-saved'
        provider = _RuntimeProvider(secret)
        self.service.register_provider(provider)
        spec = ActivitySpec(
            'Runtime Provider Demo',
            'Create a teamwork quiz.',
            'logic_math',
            'MIT',
            template='quiz',
        )

        job = self.service.submit_activity(
            spec,
            provider_name='openai',
            use_rag=False,
            output_root=self.project_root,
        )
        finished = self._wait_for_terminal(job.job_id)

        self.assertEqual(STATUS_FINISHED, finished.status)
        self.assertEqual('openai', finished.result.provider)
        self.assertEqual('runtime-test', finished.result.model)
        self.assertFalse(
            self.service.has_runtime_provider('not-configured')
        )

        job_path = os.path.join(self.job_root, job.job_id + '.json')
        with open(job_path, encoding='utf-8') as job_file:
            persisted_job = job_file.read()
        self.assertNotIn(secret, persisted_job)
        for contents in finished.result.files.values():
            self.assertNotIn(secret, contents)
        package_generation_result(finished.result)
        with zipfile.ZipFile(finished.result.bundle_path) as bundle:
            for filename in bundle.namelist():
                self.assertNotIn(
                    secret.encode('utf-8'),
                    bundle.read(filename),
                )

    def test_runtime_provider_is_reported_as_configured(self):
        self.service.register_provider(_RuntimeProvider('session-secret'))

        statuses = {
            status['name']: status
            for status in self.service.provider_statuses()
        }
        self.assertTrue(statuses['openai']['configured'])
        self.assertEqual('runtime-test', statuses['openai']['model'])

    def test_saved_provider_settings_load_after_service_restart(self):
        secret = 'saved-service-secret'
        provider = self.service.configure_provider(
            'openai',
            api_key=secret,
            model='saved-model',
            endpoint='https://example.test/v1/chat/completions',
            persist=True,
        )
        self.assertEqual('saved-model', provider.model)

        self.service.shutdown()
        self.service = AODService(
            self.store,
            worker_count=1,
            credential_store=self.credential_store,
            session_store=self.session_store,
        )
        restored = self.service.configure_provider('openai')

        self.assertEqual('saved-model', restored.model)
        self.assertEqual(secret, restored._api_key)
        self.assertEqual('openai', self.service.preferred_provider_name())

    def test_remove_saved_provider_key_clears_runtime_provider(self):
        self.service.configure_provider(
            'gemini',
            api_key='remove-service-secret',
            persist=True,
        )
        self.assertTrue(self.service.has_runtime_provider('gemini'))

        self.assertTrue(self.service.remove_provider_api_key('gemini'))
        self.assertFalse(self.service.has_runtime_provider('gemini'))
        status = self.service.provider_credential_status('gemini')
        self.assertFalse(status['has_api_key'])

    def test_refinement_job_appends_revision_to_existing_session(self):
        first = ActivitySpec(
            'Draw Together',
            'Create an activity where two learners draw together.',
            'creation',
            'MIT',
            template='canvas',
        )
        first_job = self.service.submit_activity(
            first,
            provider_name='local-template',
            output_root=self.project_root,
            user_prompt=first.prompt,
        )
        first_finished = self._wait_for_terminal(first_job.job_id)
        self.assertEqual(STATUS_FINISHED, first_finished.status)

        second = ActivitySpec(
            'Draw Together',
            'Refine the existing activity. Add a switch-student button.',
            'creation',
            'MIT',
            template='canvas',
        )
        second_job = self.service.submit_activity(
            second,
            provider_name='local-template',
            output_root=self.project_root,
            session_id=first_finished.session_id,
            parent_revision_id=first_finished.result_summary['revision_id'],
            user_prompt='Add a switch-student button.',
        )
        second_finished = self._wait_for_terminal(second_job.job_id)
        self.assertEqual(STATUS_FINISHED, second_finished.status)

        session = self.service.get_session(first_finished.session_id)
        self.assertEqual(2, len(session.revisions))
        self.assertEqual(
            first_finished.result_summary['revision_id'],
            session.revisions[1].parent_revision_id,
        )
        self.assertEqual(
            second_finished.result_summary['revision_id'],
            session.active_revision_id,
        )

    def _wait_for_terminal(self, job_id):
        deadline = time.time() + 10
        while time.time() < deadline:
            job = self.service.get_job(job_id)
            if job is not None and job.is_terminal():
                return job
            time.sleep(0.05)
        self.fail('Timed out waiting for AOD job to finish.')


class _Observer:

    def callback(self, job):
        pass


class _RuntimeProvider:
    name = 'openai'
    label = 'OpenAI'
    model = 'runtime-test'

    def __init__(self, api_key):
        self._api_key = api_key

    def generate_plan(self, system_prompt, user_prompt, timeout=45):
        return {
            'template': 'quiz',
            'summary': 'A runtime-provider quiz.',
            'learner_goal': 'Practice teamwork.',
            'learner_steps': ['Choose', 'Discuss', 'Share'],
            'word_bank': ['team', 'answer'],
        }

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=90):
        spec = ActivitySpec(
            'Runtime Provider Demo',
            'Create a teamwork quiz.',
            'logic_math',
            'MIT',
            template='quiz',
        )
        return render_activity_source(
            spec,
            enrich_plan(spec, self.generate_plan('', '')),
        )


class _MemorySecretBackend:

    def __init__(self):
        self.values = {}

    def store(self, provider_name, api_key):
        self.values[provider_name] = api_key
        return True

    def lookup(self, provider_name):
        return self.values.get(provider_name)

    def clear(self, provider_name):
        return self.values.pop(provider_name, None) is not None
