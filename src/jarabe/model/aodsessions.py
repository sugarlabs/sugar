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


ROLE_USER = 'user'
ROLE_ASSISTANT = 'assistant'

TYPE_PROMPT = 'prompt'
TYPE_STATUS = 'status'
TYPE_RESULT = 'result'
TYPE_ERROR = 'error'


@dataclass
class AODMessage:
    """One visible message in an Activity-on-Demand creation session."""

    message_id: str
    role: str
    content: str
    message_type: str = TYPE_STATUS
    job_id: str = ''
    revision_id: str = ''
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, role, content, message_type=TYPE_STATUS, job_id='',
               revision_id=''):
        return cls(
            message_id=uuid.uuid4().hex,
            role=role,
            content=content,
            message_type=message_type,
            job_id=job_id,
            revision_id=revision_id,
        )

    @classmethod
    def from_dict(cls, data):
        return cls(
            message_id=data.get('message_id', uuid.uuid4().hex),
            role=data.get('role', ROLE_ASSISTANT),
            content=data.get('content', ''),
            message_type=data.get('message_type', TYPE_STATUS),
            job_id=data.get('job_id', ''),
            revision_id=data.get('revision_id', ''),
            created_at=data.get('created_at', time.time()),
        )

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'role': self.role,
            'content': self.content,
            'message_type': self.message_type,
            'job_id': self.job_id,
            'revision_id': self.revision_id,
            'created_at': self.created_at,
        }


@dataclass
class AODRevision:
    """A generated, validated revision of a Sugar activity."""

    revision_id: str
    job_id: str
    prompt: str
    result_summary: dict
    parent_revision_id: str = ''
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, job_id, prompt, result_summary,
               parent_revision_id=''):
        return cls(
            revision_id=uuid.uuid4().hex,
            job_id=job_id,
            prompt=prompt,
            result_summary=dict(result_summary or {}),
            parent_revision_id=parent_revision_id or '',
        )

    @classmethod
    def from_dict(cls, data):
        return cls(
            revision_id=data.get('revision_id', uuid.uuid4().hex),
            job_id=data.get('job_id', ''),
            prompt=data.get('prompt', ''),
            result_summary=data.get('result_summary', {}),
            parent_revision_id=data.get('parent_revision_id', ''),
            created_at=data.get('created_at', time.time()),
        )

    def to_dict(self):
        return {
            'revision_id': self.revision_id,
            'job_id': self.job_id,
            'prompt': self.prompt,
            'result_summary': self.result_summary,
            'parent_revision_id': self.parent_revision_id,
            'created_at': self.created_at,
        }


@dataclass
class AODSession:
    """A prompt/refinement conversation around one generated activity."""

    session_id: str
    title: str
    spec: ActivitySpec
    messages: list = field(default_factory=list)
    revisions: list = field(default_factory=list)
    active_revision_id: str = ''
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, spec, title=''):
        spec = spec.normalized()
        return cls(
            session_id=uuid.uuid4().hex,
            title=title or spec.name,
            spec=spec,
        )

    @classmethod
    def from_dict(cls, data):
        return cls(
            session_id=data['session_id'],
            title=data.get('title', ''),
            spec=ActivitySpec.from_dict(data.get('spec', {})),
            messages=[
                AODMessage.from_dict(item)
                for item in data.get('messages', [])
            ],
            revisions=[
                AODRevision.from_dict(item)
                for item in data.get('revisions', [])
            ],
            active_revision_id=data.get('active_revision_id', ''),
            created_at=data.get('created_at', time.time()),
            updated_at=data.get('updated_at', time.time()),
        )

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'title': self.title,
            'spec': self.spec.to_dict(),
            'messages': [message.to_dict() for message in self.messages],
            'revisions': [
                revision.to_dict() for revision in self.revisions
            ],
            'active_revision_id': self.active_revision_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class AODSessionStore:
    """File-backed session store for AOD conversations and revisions."""

    def __init__(self, root_path=None):
        self._root_path = root_path or env.get_profile_path(
            os.path.join('aod', 'sessions')
        )
        self._lock = threading.RLock()
        os.makedirs(self._root_path, exist_ok=True)

    def create_session(self, spec, title=''):
        session = AODSession.create(spec, title=title)
        self.save(session)
        return session

    def save(self, session):
        session.updated_at = time.time()
        with self._lock:
            path = self._session_path(session.session_id)
            tmp_path = path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as output:
                json.dump(session.to_dict(), output, indent=2,
                          sort_keys=True)
                output.write('\n')
            os.replace(tmp_path, path)

    def load(self, session_id):
        with self._lock:
            path = self._session_path(session_id)
            if not os.path.exists(path):
                return None
            with open(path, encoding='utf-8') as source:
                return AODSession.from_dict(json.load(source))

    def list_sessions(self):
        with self._lock:
            sessions = []
            for filename in os.listdir(self._root_path):
                if not filename.endswith('.json'):
                    continue
                path = os.path.join(self._root_path, filename)
                try:
                    with open(path, encoding='utf-8') as source:
                        sessions.append(AODSession.from_dict(
                            json.load(source)))
                except (OSError, ValueError, KeyError, TypeError):
                    continue
            sessions.sort(key=lambda item: item.updated_at, reverse=True)
            return sessions

    def append_message(self, session_id, message):
        with self._lock:
            session = self.load(session_id)
            if session is None:
                return None
            session.messages.append(message)
            self.save(session)
            return session

    def append_revision(self, session_id, revision):
        with self._lock:
            session = self.load(session_id)
            if session is None:
                return None
            session.revisions.append(revision)
            session.active_revision_id = revision.revision_id
            self.save(session)
            return session

    def _session_path(self, session_id):
        safe_id = ''.join(
            char for char in session_id
            if char.isalnum() or char in ('-', '_')
        )
        return os.path.join(self._root_path, safe_id + '.json')
