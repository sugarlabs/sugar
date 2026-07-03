# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import unittest
from unittest import mock

from jarabe.model.aodllm import ClaudeProvider
from jarabe.model.aodllm import FreeModelProvider
from jarabe.model.aodllm import GeminiProvider
from jarabe.model.aodllm import OpenAICompatibleProvider
from jarabe.model.aodllm import OpenAIProvider
from jarabe.model.aodllm import OllamaProvider
from jarabe.model.aodllm import ProviderError
from jarabe.model.aodllm import create_provider
from jarabe.model.aodllm import get_configured_provider
from jarabe.model.aodllm import get_default_provider_name
from jarabe.model.aodllm import get_local_provider_name
from jarabe.model.aodllm import get_provider_statuses


class TestAodLLMProviders(unittest.TestCase):

    def test_transient_http_error_is_retried(self):
        import io
        import urllib.error

        from jarabe.model import aodllm

        response = mock.Mock()
        rate_limited = urllib.error.HTTPError(
            'https://api.example', 429, 'Too Many Requests', {},
            io.BytesIO(b''))

        with mock.patch('urllib.request.urlopen',
                        side_effect=[rate_limited, response]) as opener:
            with mock.patch('time.sleep') as sleeper:
                result = aodllm._urlopen_with_retry(
                    mock.Mock(), 30, 'Test')

        self.assertIs(response, result)
        self.assertEqual(2, opener.call_count)
        sleeper.assert_called_once()

    def test_network_error_is_retried(self):
        from jarabe.model import aodllm

        response = mock.Mock()
        with mock.patch('urllib.request.urlopen',
                        side_effect=[OSError('reset'), response]) as opener:
            with mock.patch('time.sleep'):
                result = aodllm._urlopen_with_retry(
                    mock.Mock(), 30, 'Test')

        self.assertIs(response, result)
        self.assertEqual(2, opener.call_count)

    def test_auth_error_is_not_retried(self):
        import io
        import urllib.error

        from jarabe.model import aodllm

        unauthorized = urllib.error.HTTPError(
            'https://api.example', 401, 'Unauthorized', {},
            io.BytesIO(b''))

        with mock.patch('urllib.request.urlopen',
                        side_effect=unauthorized) as opener:
            with mock.patch('time.sleep') as sleeper:
                with self.assertRaises(urllib.error.HTTPError):
                    aodllm._urlopen_with_retry(mock.Mock(), 30, 'Test')

        self.assertEqual(1, opener.call_count)
        sleeper.assert_not_called()

    def test_local_template_provider_returns_none(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual('local-template', get_default_provider_name())
            self.assertIsNone(get_configured_provider('local-template'))

    def test_default_provider_prefers_configured_openai(self):
        env = {
            'OPENAI_API_KEY': 'test-key',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual('openai', get_default_provider_name())
            self.assertIsInstance(
                get_configured_provider('default'),
                OpenAIProvider,
            )

    def test_local_provider_prefers_configured_ollama(self):
        env = {
            'AOD_OLLAMA_MODEL': 'test-model',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual('ollama', get_local_provider_name())

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual('local-template', get_local_provider_name())

    def test_provider_statuses_include_local_and_clouds(self):
        statuses = get_provider_statuses()
        names = [status['name'] for status in statuses]
        self.assertIn('local-template', names)
        self.assertIn('gemini', names)
        self.assertIn('openai', names)
        self.assertIn('openrouter', names)
        self.assertIn('claude', names)
        self.assertIn('ollama', names)

    def test_create_freemodel_provider_uses_responses_defaults(self):
        provider = create_provider(
            'freemodel',
            api_key='freemodel-key',
        )

        self.assertIsInstance(provider, FreeModelProvider)
        self.assertEqual('freemodel', provider.name)
        self.assertEqual('FreeModel', provider.label)
        self.assertEqual('freemodel-key', provider._api_key)
        self.assertEqual('gpt-5.5', provider.model)
        self.assertEqual(
            'https://api.freemodel.dev/v1/responses',
            provider._endpoint,
        )

    def test_freemodel_responses_request_and_output_text(self):
        provider = create_provider(
            'freemodel',
            api_key='freemodel-key',
            model='gpt-5.5',
            endpoint='https://api.freemodel.dev',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'output_text': '{"template": "quiz"}',
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            plan = provider.generate_plan('system', 'user')
            request = opener.call_args[0][0]
            payload = json.loads(request.data.decode('utf-8'))

        self.assertEqual('quiz', plan['template'])
        self.assertEqual(
            'https://api.freemodel.dev/v1/responses',
            request.full_url,
        )
        self.assertEqual('gpt-5.5', payload['model'])
        self.assertEqual('system', payload['instructions'])
        self.assertEqual('user', payload['input'])
        self.assertEqual({'effort': 'xhigh'}, payload['reasoning'])

    def test_freemodel_codegen_uses_larger_output_budget(self):
        provider = create_provider(
            'freemodel',
            api_key='freemodel-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'output': [{
                'content': [{
                    'text': json.dumps({
                        'activity_py': (
                            'from sugar3.activity import activity\n\n'
                            'class GeneratedActivity(activity.Activity):\n'
                            '    pass\n'
                        ),
                    }),
                }],
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            source = provider.generate_activity_source('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        self.assertIn('GeneratedActivity', source)
        self.assertEqual(16000, payload['max_output_tokens'])
        self.assertEqual({'effort': 'high'}, payload['reasoning'])

    def test_create_provider_uses_runtime_key_model_and_endpoint(self):
        provider = create_provider(
            'anthropic',
            api_key='session-key',
            model='claude-test',
            endpoint='https://example.test/messages',
        )

        self.assertIsInstance(provider, ClaudeProvider)
        self.assertEqual('claude-test', provider.model)
        self.assertEqual(
            'https://example.test/messages',
            provider._endpoint,
        )

    def test_create_ollama_provider_does_not_require_api_key(self):
        provider = create_provider(
            'ollama',
            model='local-test',
            endpoint='http://127.0.0.1:11434/api/generate',
        )

        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual('local-test', provider.model)

    def test_create_unknown_provider_fails(self):
        with self.assertRaises(ProviderError):
            create_provider('unknown-provider', api_key='session-key')

    def test_gemini_request_includes_safety_settings(self):
        provider = GeminiProvider(api_key='test-key')
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'candidates': [{
                'content': {
                    'parts': [{'text': '{"template": "quiz"}'}],
                },
                'finishReason': 'STOP',
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            provider.generate_plan('system', 'user')
            payload = json.loads(opener.call_args[0][0].data.decode('utf-8'))

        self.assertIn('safetySettings', payload)
        categories = {
            setting['category']
            for setting in payload['safetySettings']
        }
        self.assertIn('HARM_CATEGORY_DANGEROUS_CONTENT', categories)
        self.assertIn('HARM_CATEGORY_HATE_SPEECH', categories)
        self.assertIn('HARM_CATEGORY_HARASSMENT', categories)
        self.assertIn('HARM_CATEGORY_SEXUALLY_EXPLICIT', categories)
        for setting in payload['safetySettings']:
            self.assertEqual('BLOCK_ONLY_HIGH', setting['threshold'])

    def test_gemini_blocked_response_raises_clear_error(self):
        provider = GeminiProvider(api_key='test-key')
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'candidates': [{
                'content': {'parts': []},
                'finishReason': 'SAFETY',
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ProviderError) as context:
                provider.generate_plan('system', 'user')

        self.assertIn('blocked', str(context.exception))

    def test_create_deepseek_provider_uses_openai_compatible_defaults(self):
        provider = create_provider(
            'deepseek',
            api_key='deepseek-key',
            model='deepseek-reasoner',
        )

        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual('deepseek', provider.name)
        self.assertEqual('DeepSeek', provider.label)
        self.assertEqual('deepseek-key', provider._api_key)
        self.assertEqual('deepseek-reasoner', provider.model)
        self.assertEqual(
            'https://api.deepseek.com/v1/chat/completions',
            provider._endpoint,
        )

    def test_create_qwen_provider_from_environment(self):
        env = {
            'QWEN_API_KEY': 'qwen-key',
            'AOD_QWEN_MODEL': 'qwen-max',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            provider = create_provider('qwen')

        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual('qwen', provider.name)
        self.assertEqual('qwen-max', provider.model)
        self.assertEqual('qwen-key', provider._api_key)

    def test_create_openrouter_provider_uses_claude_opus_defaults(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )

        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual('openrouter', provider.name)
        self.assertEqual('OpenRouter', provider.label)
        self.assertEqual('openrouter-key', provider._api_key)
        self.assertEqual('anthropic/claude-opus-4.8', provider.model)
        self.assertEqual(
            'https://openrouter.ai/api/v1/chat/completions',
            provider._endpoint,
        )

    def test_openrouter_request_uses_default_model_and_headers(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': '{"template": "quiz"}',
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            plan = provider.generate_plan('system', 'user')
            request = opener.call_args[0][0]
            payload = json.loads(request.data.decode('utf-8'))

        self.assertEqual('quiz', plan['template'])
        self.assertEqual(
            'https://openrouter.ai/api/v1/chat/completions',
            request.full_url,
        )
        self.assertEqual('anthropic/claude-opus-4.8', payload['model'])
        self.assertEqual('Sugar Activity on Demand',
                         request.get_header('X-title'))

    def test_openrouter_request_accepts_structured_text_parts(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': [{
                        'type': 'text',
                        'text': '{"template": "canvas"}',
                    }],
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response):
            plan = provider.generate_plan('system', 'user')

        self.assertEqual('canvas', plan['template'])

    def test_openrouter_request_reports_missing_text_content(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': None,
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ProviderError) as context:
                provider.generate_plan('system', 'user')

        self.assertIn('text content', str(context.exception))

    def test_openrouter_request_reports_top_level_error(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'error': {
                'code': 402,
                'message': 'Insufficient credits',
            },
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ProviderError) as context:
                provider.generate_plan('system', 'user')

        self.assertIn('OpenRouter request failed', str(context.exception))
        self.assertIn('Insufficient credits', str(context.exception))

    def test_openrouter_request_reports_length_finish_reason(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'finish_reason': 'length',
                'message': {
                    'content': '',
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ProviderError) as context:
                provider.generate_plan('system', 'user')

        self.assertIn('finish_reason=length', str(context.exception))
        self.assertIn('activity.py', str(context.exception))

    def test_openrouter_request_reports_tool_call_only_response(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': None,
                    'tool_calls': [{'id': 'call-1'}],
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ProviderError) as context:
                provider.generate_plan('system', 'user')

        self.assertIn('tool calls', str(context.exception))

    def test_openrouter_codegen_accepts_fenced_activity_source(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': (
                        'Here is activity.py:\n'
                        '```python\n%s```'
                    ) % _simple_activity_source(),
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            source = provider.generate_activity_source('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        self.assertIn('GeneratedActivity', source)
        self.assertNotIn('```', source)
        self.assertNotIn('response_format', payload)
        # The default OpenRouter model uses the fast codegen budget plus
        # minimal reasoning to avoid long thinking delays before activity.py.
        self.assertEqual(16384, payload['max_tokens'])
        self.assertEqual({'effort': 'minimal'}, payload['reasoning'])

    def test_openrouter_plan_call_is_not_affected_by_reasoning_budget(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {'content': '{"template": "quiz"}'},
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            provider.generate_plan('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        # Plan requests keep the default temperature and are uncapped and
        # must not gain reasoning-effort parameters: only codegen budgets
        # reasoning so the plan JSON gets delivered reliably.
        self.assertNotIn('reasoning', payload)
        self.assertNotIn('max_tokens', payload)

    def test_openrouter_codegen_budget_overridable_by_environment(self):
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
            model='moonshotai/kimi-k2.6',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'activity_py': _simple_activity_source(),
                    }),
                },
            }],
        }).encode('utf-8')

        env = {
            'AOD_OPENROUTER_CODEGEN_MAX_TOKENS': '32000',
            'AOD_OPENROUTER_CODEGEN_REASONING_EFFORT': 'disabled',
        }
        with mock.patch.dict(os.environ, env), \
                mock.patch('urllib.request.urlopen',
                           return_value=response) as opener:
            provider.generate_activity_source('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        self.assertEqual(32000, payload['max_tokens'])
        # "disabled" degrades to the minimal accepted effort rather than
        # sending enabled:false, which mandatory-reasoning Kimi models
        # would reject.
        self.assertEqual({'effort': 'minimal'}, payload['reasoning'])

    def test_openrouter_codegen_reasoning_only_for_kimi_models(self):
        # A non-Kimi OpenRouter model keeps a tighter codegen budget
        # and gets minimal reasoning effort to reduce thinking overhead
        # (OpenRouter defaults to "medium" for many models).
        provider = create_provider(
            'openrouter',
            api_key='openrouter-key',
            model='meta-llama/llama-3.1-70b-instruct',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'activity_py': _simple_activity_source(),
                    }),
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            provider.generate_activity_source('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        self.assertEqual(16384, payload['max_tokens'])
        self.assertEqual({'effort': 'minimal'}, payload['reasoning'])

    def test_create_moonshot_provider_from_environment(self):
        env = {
            'MOONSHOT_API_KEY': 'moonshot-key',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            provider = create_provider('moonshot')

        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual('moonshot', provider.name)
        self.assertEqual('moonshot-v1-8k', provider.model)
        self.assertEqual('moonshot-key', provider._api_key)

    def test_provider_statuses_include_chinese_models(self):
        env = {
            'DEEPSEEK_API_KEY': 'deepseek-key',
            'QWEN_API_KEY': 'qwen-key',
            'MOONSHOT_API_KEY': 'moonshot-key',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            statuses = {
                status['name']: status
                for status in get_provider_statuses()
            }

        self.assertTrue(statuses['deepseek']['configured'])
        self.assertTrue(statuses['qwen']['configured'])
        self.assertTrue(statuses['moonshot']['configured'])

    def test_codex_alias_resolves_to_openai(self):
        provider = create_provider('codex', api_key='openai-key')

        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual('openai', provider.name)

    def test_create_opencode_provider_uses_zen_defaults(self):
        provider = create_provider(
            'opencode',
            api_key='opencode-key',
            model='claude-opus-4-8',
        )

        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual('opencode', provider.name)
        self.assertEqual('OpenCode Zen', provider.label)
        self.assertEqual('opencode-key', provider._api_key)
        self.assertEqual('claude-opus-4-8', provider.model)
        self.assertEqual(
            'https://opencode.ai/zen/v1/chat/completions',
            provider._endpoint,
        )

    def test_create_opencode_go_provider_from_environment(self):
        env = {
            'OPENCODE_API_KEY': 'opencode-key',
            'AOD_OPENCODE_GO_MODEL': 'minimax-m3',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            provider = create_provider('opencode-go')

        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual('opencode-go', provider.name)
        self.assertEqual('OpenCode Go', provider.label)
        self.assertEqual('minimax-m3', provider.model)
        self.assertEqual('opencode-key', provider._api_key)
        self.assertEqual(
            'https://opencode.ai/zen/go/v1/chat/completions',
            provider._endpoint,
        )

    def test_opencode_go_default_model_is_kimi_k27_code(self):
        env = {
            'OPENCODE_API_KEY': 'opencode-key',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            provider = create_provider('opencode-go')

        self.assertEqual('kimi-k2.7-code', provider.model)

    def test_opencode_go_kimi_k27_code_uses_required_temperature(self):
        provider = create_provider(
            'opencode-go',
            api_key='opencode-key',
            model='kimi-k2.7-code',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': '{"template": "quiz"}',
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            provider.generate_plan('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        self.assertEqual(1.0, payload['temperature'])

    def test_opencode_go_codegen_uses_larger_token_budget(self):
        provider = create_provider(
            'opencode-go',
            api_key='opencode-key',
            model='kimi-k2.7-code',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'activity_py': (
                            'from sugar3.activity import activity\n\n'
                            'class GeneratedActivity(activity.Activity):\n'
                            '    pass\n'
                        ),
                    }),
                },
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            source = provider.generate_activity_source('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        self.assertIn('GeneratedActivity', source)
        self.assertEqual(16384, payload['max_tokens'])
        self.assertEqual(1.0, payload['temperature'])

    def test_claude_codegen_uses_larger_token_budget(self):
        provider = create_provider(
            'claude',
            api_key='claude-key',
            model='claude-test',
        )
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        response.read.return_value = json.dumps({
            'content': [{
                'type': 'text',
                'text': json.dumps({
                    'activity_py': (
                        'from sugar3.activity import activity\n\n'
                        'class GeneratedActivity(activity.Activity):\n'
                        '    pass\n'
                    ),
                }),
            }],
        }).encode('utf-8')

        with mock.patch('urllib.request.urlopen', return_value=response) \
                as opener:
            source = provider.generate_activity_source('system', 'user')
            payload = json.loads(
                opener.call_args[0][0].data.decode('utf-8')
            )

        self.assertIn('GeneratedActivity', source)
        self.assertEqual(16384, payload['max_tokens'])


def _simple_activity_source():
    return (
        'from sugar3.activity import activity\n\n'
        'class GeneratedActivity(activity.Activity):\n'
        '    pass\n'
    )
