# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
from dataclasses import field
import json
import os
import threading
import time
import uuid

from sugar3 import env

from jarabe.model.aodspec import ActivitySpec


STATUS_QUEUED = 'queued'
STATUS_PLANNING = 'planning'
STATUS_GROUNDING = 'grounding'
STATUS_PROVIDER = 'provider'
STATUS_GENERATING = 'generating'
STATUS_VALIDATING = 'validating'
STATUS_PACKAGING = 'packaging'
STATUS_FINISHED = 'finished'
STATUS_FAILED = 'failed'
STATUS_CANCELLED = 'cancelled'

TERMINAL_STATUSES = (
    STATUS_FINISHED,
    STATUS_FAILED,
    STATUS_CANCELLED,
)


@dataclass
class AODJob:
    """A persistent Activity-on-Demand generation job."""

    job_id: str
    spec: ActivitySpec
    provider_name: str = 'default'
    use_rag: bool = True
    validate_code: bool = True
    output_root: str = ''
    session_id: str = ''
    parent_revision_id: str = ''
    user_prompt: str = ''
    enhance: bool = True
    enhanced_prompt: str = ''
    status: str = STATUS_QUEUED
    stage: str = STATUS_QUEUED
    progress: float = 0.0
    message: str = 'Queued'
    result_summary: dict = field(default_factory=dict)
    draft_activity_source: str = ''
    error: str = ''
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0
    cancel_requested: bool = False
    result: object = None

    @classmethod
    def create(cls, spec, provider_name='default', use_rag=True,
               validate_code=True, output_root=None, session_id='',
               parent_revision_id='', user_prompt='', enhance=True):
        return cls(
            job_id=uuid.uuid4().hex,
            spec=spec.normalized(),
            provider_name=provider_name,
            use_rag=use_rag,
            validate_code=validate_code,
            output_root=output_root or '',
            session_id=session_id or '',
            parent_revision_id=parent_revision_id or '',
            user_prompt=user_prompt or spec.prompt,
            enhance=bool(enhance),
        )

    @classmethod
    def from_dict(cls, data):
        job = cls(
            job_id=data['job_id'],
            spec=ActivitySpec.from_dict(data['spec']),
            provider_name=data.get('provider_name', 'default'),
            use_rag=data.get('use_rag', True),
            validate_code=data.get('validate_code', True),
            output_root=data.get('output_root', ''),
            session_id=data.get('session_id', ''),
            parent_revision_id=data.get('parent_revision_id', ''),
            user_prompt=data.get('user_prompt', ''),
            enhance=data.get('enhance', True),
            enhanced_prompt=data.get('enhanced_prompt', ''),
            status=data.get('status', STATUS_QUEUED),
            stage=data.get('stage', STATUS_QUEUED),
            progress=data.get('progress', 0.0),
            message=data.get('message', ''),
            result_summary=data.get('result_summary', {}),
            draft_activity_source=data.get('draft_activity_source', ''),
            error=data.get('error', ''),
            created_at=data.get('created_at', time.time()),
            updated_at=data.get('updated_at', time.time()),
            started_at=data.get('started_at', 0.0),
            finished_at=data.get('finished_at', 0.0),
            cancel_requested=data.get('cancel_requested', False),
        )
        return job

    def to_dict(self):
        return {
            'job_id': self.job_id,
            'spec': self.spec.to_dict(),
            'provider_name': self.provider_name,
            'use_rag': self.use_rag,
            'validate_code': self.validate_code,
            'output_root': self.output_root,
            'session_id': self.session_id,
            'parent_revision_id': self.parent_revision_id,
            'user_prompt': self.user_prompt,
            'enhance': self.enhance,
            'enhanced_prompt': self.enhanced_prompt,
            'status': self.status,
            'stage': self.stage,
            'progress': self.progress,
            'message': self.message,
            'result_summary': self.result_summary,
            'draft_activity_source': self.draft_activity_source,
            'error': self.error,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'started_at': self.started_at,
            'finished_at': self.finished_at,
            'cancel_requested': self.cancel_requested,
        }

    def is_terminal(self):
        return self.status in TERMINAL_STATUSES

    def mark_started(self):
        now = time.time()
        self.started_at = self.started_at or now
        self.updated_at = now

    def request_cancel(self):
        self.cancel_requested = True
        self.updated_at = time.time()

    def update_progress(self, status, stage, progress, message):
        if self.is_terminal():
            return
        self.status = status
        self.stage = stage
        self.progress = max(0.0, min(1.0, float(progress)))
        self.message = message
        self.updated_at = time.time()

    def finish(self, result):
        if self.is_terminal():
            return
        self.status = STATUS_FINISHED
        self.stage = STATUS_FINISHED
        self.progress = 1.0
        self.message = 'Activity project is ready'
        self.result = result
        self.result_summary = result_summary_from_generation(result)
        self.finished_at = time.time()
        self.updated_at = self.finished_at

    def fail(self, error):
        if self.is_terminal():
            return
        self.status = STATUS_FAILED
        self.stage = STATUS_FAILED
        self.error = str(error)
        self.message = str(error)
        self.finished_at = time.time()
        self.updated_at = self.finished_at

    def cancel(self):
        if self.is_terminal():
            return
        self.status = STATUS_CANCELLED
        self.stage = STATUS_CANCELLED
        self.error = ''
        self.message = 'Cancelled'
        self.finished_at = time.time()
        self.updated_at = self.finished_at


class AODJobStore:
    """File-backed job store used by the local service."""

    def __init__(self, root_path=None):
        self._root_path = root_path or env.get_profile_path(
            os.path.join('aod', 'jobs')
        )
        self._lock = threading.RLock()
        os.makedirs(self._root_path, exist_ok=True)

    def save(self, job):
        with self._lock:
            path = self._job_path(job.job_id)
            tmp_path = path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as output:
                json.dump(job.to_dict(), output, indent=2, sort_keys=True)
                output.write('\n')
            os.replace(tmp_path, path)

    def load(self, job_id):
        with self._lock:
            path = self._job_path(job_id)
            if not os.path.exists(path):
                return None
            with open(path, encoding='utf-8') as source:
                return AODJob.from_dict(json.load(source))

    def list_jobs(self):
        with self._lock:
            jobs = []
            for filename in os.listdir(self._root_path):
                if not filename.endswith('.json'):
                    continue
                path = os.path.join(self._root_path, filename)
                try:
                    with open(path, encoding='utf-8') as source:
                        jobs.append(AODJob.from_dict(json.load(source)))
                except (OSError, ValueError, KeyError, TypeError):
                    continue
            jobs.sort(key=lambda job: job.created_at, reverse=True)
            return jobs

    def _job_path(self, job_id):
        safe_id = ''.join(
            char for char in job_id
            if char.isalnum() or char in ('-', '_')
        )
        return os.path.join(self._root_path, safe_id + '.json')


def result_summary_from_generation(result):
    return {
        'activity_name': result.spec.name,
        'bundle_id': result.bundle_id,
        'bundle_path': result.bundle_path,
        'project_path': result.project_path,
        'provider': result.provider,
        'model': result.model,
        'template': result.plan.get('template', ''),
        'code_source': result.plan.get('code_source', 'template'),
    }
