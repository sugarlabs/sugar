# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import tempfile

from sugar3 import env


_PROVIDER_VARIABLES = {
    'gemini': {
        'key': 'GEMINI_API_KEY',
        'model': 'AOD_GEMINI_MODEL',
        'endpoint': 'AOD_GEMINI_ENDPOINT',
        'storage': 'AOD_GEMINI_KEY_STORAGE',
    },
    'openai': {
        'key': 'OPENAI_API_KEY',
        'model': 'AOD_OPENAI_MODEL',
        'endpoint': 'AOD_OPENAI_ENDPOINT',
        'storage': 'AOD_OPENAI_KEY_STORAGE',
    },
    'openrouter': {
        'key': 'OPENROUTER_API_KEY',
        'model': 'AOD_OPENROUTER_MODEL',
        'endpoint': 'AOD_OPENROUTER_ENDPOINT',
        'storage': 'AOD_OPENROUTER_KEY_STORAGE',
    },
    'deepseek': {
        'key': 'DEEPSEEK_API_KEY',
        'model': 'AOD_DEEPSEEK_MODEL',
        'endpoint': 'AOD_DEEPSEEK_ENDPOINT',
        'storage': 'AOD_DEEPSEEK_KEY_STORAGE',
    },
    'qwen': {
        'key': 'QWEN_API_KEY',
        'model': 'AOD_QWEN_MODEL',
        'endpoint': 'AOD_QWEN_ENDPOINT',
        'storage': 'AOD_QWEN_KEY_STORAGE',
    },
    'moonshot': {
        'key': 'MOONSHOT_API_KEY',
        'model': 'AOD_MOONSHOT_MODEL',
        'endpoint': 'AOD_MOONSHOT_ENDPOINT',
        'storage': 'AOD_MOONSHOT_KEY_STORAGE',
    },
    'opencode': {
        'key': 'OPENCODE_API_KEY',
        'model': 'AOD_OPENCODE_MODEL',
        'endpoint': 'AOD_OPENCODE_ENDPOINT',
        'storage': 'AOD_OPENCODE_KEY_STORAGE',
    },
    'opencode-go': {
        'key': 'OPENCODE_API_KEY',
        'model': 'AOD_OPENCODE_GO_MODEL',
        'endpoint': 'AOD_OPENCODE_GO_ENDPOINT',
        'storage': 'AOD_OPENCODE_GO_KEY_STORAGE',
    },
    'freemodel': {
        'key': 'FREEMODEL_API_KEY',
        'model': 'AOD_FREEMODEL_MODEL',
        'endpoint': 'AOD_FREEMODEL_ENDPOINT',
        'storage': 'AOD_FREEMODEL_KEY_STORAGE',
    },
    'claude': {
        'key': 'ANTHROPIC_API_KEY',
        'model': 'AOD_CLAUDE_MODEL',
        'endpoint': 'AOD_CLAUDE_ENDPOINT',
        'storage': 'AOD_CLAUDE_KEY_STORAGE',
    },
    'ollama': {
        'model': 'AOD_OLLAMA_MODEL',
        'endpoint': 'AOD_OLLAMA_ENDPOINT',
    },
}

_DEFAULT_PROVIDER_VARIABLE = 'AOD_DEFAULT_PROVIDER'
_ALLOWED_VARIABLES = {_DEFAULT_PROVIDER_VARIABLE}
for _variables in _PROVIDER_VARIABLES.values():
    _ALLOWED_VARIABLES.update(_variables.values())


class CredentialStoreError(Exception):
    pass


class AODCredentialStore:
    """Store provider settings without exposing keys to generated projects."""

    def __init__(self, root_path=None, secret_backend=None):
        self._root_path = root_path or env.get_profile_path('aod')
        self._path = os.path.join(self._root_path, 'providers.env')
        if secret_backend is False:
            self._secret_backend = None
        elif secret_backend == 'auto':
            self._secret_backend = _create_secret_backend()
        elif secret_backend is None:
            self._secret_backend = None
        else:
            self._secret_backend = secret_backend

    @property
    def path(self):
        return self._path

    def save_provider(self, provider_name, api_key=None, model=None,
                      endpoint=None):
        variables = self._variables_for(provider_name)
        values = self._read_values()
        storage = values.get(variables.get('storage', ''), '')

        self._set_optional(values, variables.get('model'), model)
        self._set_optional(values, variables.get('endpoint'), endpoint)
        values[_DEFAULT_PROVIDER_VARIABLE] = provider_name

        if api_key and variables.get('key'):
            storage = self._store_api_key(provider_name, api_key, values)
            values[variables['storage']] = storage

        self._write_values(values)
        return storage

    def load_provider(self, provider_name):
        variables = self._variables_for(provider_name)
        values = self._read_values()
        storage = values.get(variables.get('storage', ''), '')
        api_key = ''

        if variables.get('key'):
            if storage == 'keyring' and self._secret_backend is not None:
                try:
                    api_key = self._secret_backend.lookup(provider_name) or ''
                except Exception:
                    api_key = ''
            if not api_key:
                api_key = values.get(variables['key'], '')

        return {
            'api_key': api_key,
            'model': values.get(variables.get('model', ''), ''),
            'endpoint': values.get(variables.get('endpoint', ''), ''),
            'storage': storage,
        }

    def provider_status(self, provider_name):
        variables = self._variables_for(provider_name)
        values = self._read_values()
        storage = values.get(variables.get('storage', ''), '')
        has_key = bool(
            storage == 'keyring' or values.get(
                variables.get('key', ''),
                '',
            )
        )
        return {
            'has_api_key': has_key,
            'storage': storage,
            'model': values.get(variables.get('model', ''), ''),
            'endpoint': values.get(variables.get('endpoint', ''), ''),
        }

    def remove_api_key(self, provider_name):
        variables = self._variables_for(provider_name)
        if not variables.get('key'):
            return False

        values = self._read_values()
        removed = False
        if self._secret_backend is not None:
            try:
                removed = bool(
                    self._secret_backend.clear(provider_name)
                ) or removed
            except Exception:
                pass

        if values.pop(variables['key'], None) is not None:
            removed = True
        if values.pop(variables['storage'], None) is not None:
            removed = True
        self._write_values(values)
        return removed

    def get_default_provider_name(self):
        values = self._read_values()
        provider_name = values.get(_DEFAULT_PROVIDER_VARIABLE, '')
        if provider_name not in _PROVIDER_VARIABLES:
            return ''

        status = self.provider_status(provider_name)
        if provider_name == 'ollama' or status['has_api_key']:
            return provider_name
        return ''

    def _store_api_key(self, provider_name, api_key, values):
        variables = self._variables_for(provider_name)
        if self._secret_backend is not None:
            try:
                if not self._secret_backend.store(provider_name, api_key):
                    raise CredentialStoreError(
                        'The system keyring did not store the API key.'
                    )
                values.pop(variables['key'], None)
                return 'keyring'
            except Exception:
                pass

        values[variables['key']] = api_key
        return 'profile-file'

    def _variables_for(self, provider_name):
        try:
            return _PROVIDER_VARIABLES[provider_name]
        except KeyError:
            raise CredentialStoreError(
                'Provider settings cannot be saved for %s.' % provider_name
            )

    def _read_values(self):
        if not os.path.exists(self._path):
            return {}

        try:
            os.chmod(self._path, 0o600)
            with open(self._path, encoding='utf-8') as source:
                lines = source.readlines()
        except OSError as error:
            raise CredentialStoreError(
                'Could not read provider settings: %s' % error
            )

        values = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            name, encoded = line.split('=', 1)
            if name not in _ALLOWED_VARIABLES:
                continue
            try:
                value = json.loads(encoded)
            except (TypeError, ValueError):
                continue
            if isinstance(value, str):
                values[name] = value
        return values

    def _write_values(self, values):
        values = {
            name: value
            for name, value in values.items()
            if name in _ALLOWED_VARIABLES and isinstance(value, str) and value
        }

        try:
            os.makedirs(self._root_path, mode=0o700, exist_ok=True)
            os.chmod(self._root_path, 0o700)
            descriptor, temporary_path = tempfile.mkstemp(
                prefix='.providers-',
                dir=self._root_path,
                text=True,
            )
            try:
                os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
                    output.write(
                        '# Sugar Activity-on-Demand provider settings\n'
                    )
                    output.write(
                        '# This file is private to the current OS user.\n'
                    )
                    for name in sorted(values):
                        output.write(
                            '%s=%s\n' % (name, json.dumps(values[name]))
                        )
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary_path, self._path)
                os.chmod(self._path, 0o600)
            except Exception:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
                raise
        except OSError as error:
            raise CredentialStoreError(
                'Could not save provider settings: %s' % error
            )

    def _set_optional(self, values, name, value):
        if not name:
            return
        if value:
            values[name] = value
        else:
            values.pop(name, None)


class _LibSecretBackend:

    def __init__(self):
        import gi
        gi.require_version('Secret', '1')
        from gi.repository import Secret

        self._secret = Secret
        self._profile_path = env.get_profile_path()
        self._schema = Secret.Schema.new(
            'org.sugarlabs.ActivityOnDemand.Provider',
            Secret.SchemaFlags.NONE,
            {
                'provider': Secret.SchemaAttributeType.STRING,
                'profile': Secret.SchemaAttributeType.STRING,
            },
        )

    def store(self, provider_name, api_key):
        return self._secret.password_store_sync(
            self._schema,
            self._attributes(provider_name),
            self._secret.COLLECTION_DEFAULT,
            'Sugar Activity-on-Demand %s API key' % provider_name,
            api_key,
            None,
        )

    def lookup(self, provider_name):
        return self._secret.password_lookup_sync(
            self._schema,
            self._attributes(provider_name),
            None,
        )

    def clear(self, provider_name):
        return self._secret.password_clear_sync(
            self._schema,
            self._attributes(provider_name),
            None,
        )

    def _attributes(self, provider_name):
        return {
            'provider': provider_name,
            'profile': self._profile_path,
        }


def _create_secret_backend():
    try:
        return _LibSecretBackend()
    except Exception:
        return None
