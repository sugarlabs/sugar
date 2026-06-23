# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import shutil
import stat
import tempfile
import unittest

from jarabe.model.aodcredentials import AODCredentialStore


class TestAodCredentialStore(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='aod-credentials-test-')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_keyring_storage_keeps_secret_out_of_profile_file(self):
        keyring = _MemorySecretBackend()
        store = AODCredentialStore(self.root, secret_backend=keyring)
        secret = 'keyring-secret-value'

        storage = store.save_provider(
            'openai',
            api_key=secret,
            model='test-model',
            endpoint='https://example.test/v1',
        )

        self.assertEqual('keyring', storage)
        self.assertEqual(secret, keyring.values['openai'])
        with open(store.path, encoding='utf-8') as source:
            saved_settings = source.read()
        self.assertNotIn(secret, saved_settings)
        self.assertEqual(
            stat.S_IRUSR | stat.S_IWUSR,
            stat.S_IMODE(os.stat(store.path).st_mode),
        )
        self.assertEqual(
            stat.S_IRWXU,
            stat.S_IMODE(os.stat(self.root).st_mode),
        )

        loaded = store.load_provider('openai')
        self.assertEqual(secret, loaded['api_key'])
        self.assertEqual('test-model', loaded['model'])
        self.assertEqual('keyring', loaded['storage'])

    def test_private_file_fallback_has_owner_only_permissions(self):
        store = AODCredentialStore(
            self.root,
            secret_backend=_FailingSecretBackend(),
        )
        secret = 'private-file-secret-value'

        storage = store.save_provider(
            'claude',
            api_key=secret,
            model='claude-test',
        )

        self.assertEqual('profile-file', storage)
        with open(store.path, encoding='utf-8') as source:
            saved_settings = source.read()
        self.assertIn(secret, saved_settings)
        self.assertEqual(
            stat.S_IRUSR | stat.S_IWUSR,
            stat.S_IMODE(os.stat(store.path).st_mode),
        )
        self.assertEqual(secret, store.load_provider('claude')['api_key'])

    def test_remove_api_key_clears_keyring_and_file_marker(self):
        keyring = _MemorySecretBackend()
        store = AODCredentialStore(self.root, secret_backend=keyring)
        store.save_provider('gemini', api_key='remove-me')

        self.assertTrue(store.remove_api_key('gemini'))
        self.assertNotIn('gemini', keyring.values)
        status = store.provider_status('gemini')
        self.assertFalse(status['has_api_key'])
        self.assertEqual('', store.load_provider('gemini')['api_key'])

    def test_last_saved_configured_provider_becomes_default(self):
        keyring = _MemorySecretBackend()
        store = AODCredentialStore(self.root, secret_backend=keyring)
        store.save_provider('openai', api_key='openai-key')
        store.save_provider('gemini', api_key='gemini-key')

        self.assertEqual('gemini', store.get_default_provider_name())


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


class _FailingSecretBackend:

    def store(self, provider_name, api_key):
        raise RuntimeError('No keyring service')

    def lookup(self, provider_name):
        raise RuntimeError('No keyring service')

    def clear(self, provider_name):
        raise RuntimeError('No keyring service')
