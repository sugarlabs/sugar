# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from jarabe.model.aodprompts import extract_json_object
from jarabe.model.aodcodegen import extract_activity_source
from jarabe.model.aodcodegen import extract_activity_source_from_response


class ProviderError(Exception):
    pass


def _env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


_CODEGEN_MAX_TOKENS = _env_int('AOD_CODEGEN_MAX_TOKENS', 16384)
_FREEMODEL_CODEGEN_MAX_OUTPUT_TOKENS = 16000
_PROVIDER_PLAN_TIMEOUT = _env_int('AOD_PROVIDER_PLAN_TIMEOUT', 120)
_PROVIDER_CODEGEN_TIMEOUT = _env_int('AOD_PROVIDER_CODEGEN_TIMEOUT', 300)
_GEMINI_CODEGEN_MAX_OUTPUT_TOKENS = _env_int(
    'AOD_GEMINI_CODEGEN_MAX_OUTPUT_TOKENS',
    9000,
)

# Kimi K2.x on OpenRouter is a reasoning model with reasoning enabled by
# default (reasoning.default_enabled=true, mandatory=false).  Reasoning
# tokens count against the completion budget, so the default 9000-token
# codegen cap is exhausted by chain-of-thought before activity.py is
# written, yielding finish_reason=length / empty content.  For code
# generation we therefore bound the reasoning effort and give the model a
# larger completion budget so bounded reasoning plus a complete Sugar
# activity.py both fit.  See OpenAICompatibleProvider._is_reasoning_codegen.
_OPENROUTER_REASONING_CODEGEN_MAX_TOKENS = 32000
_OPENROUTER_FAST_CODEGEN_MAX_TOKENS = 16384
_OPENROUTER_REASONING_CODEGEN_EFFORT = 'minimal'
# Special effort values that map to disabling reasoning entirely.  These are
# only safe for non-mandatory reasoning models; mandatory reasoning models
# reject disable, so if we can't tell, we fall back to a minimal effort.
_REASONING_DISABLE_VALUES = ('none', 'false', 'off', 'disabled')
_REASONING_SAFE_MINIMAL_EFFORT = 'minimal'


class LLMProvider:
    name = 'provider'
    model = ''
    label = 'Provider'

    def generate_plan(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_PLAN_TIMEOUT):
        raise NotImplementedError

    def generate_text(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_CODEGEN_TIMEOUT,
                      stream_callback=None):
        """Return raw model text without any extraction or parsing.

        Used by the refinement pipeline for SEARCH/REPLACE blocks,
        where the response is NOT a complete activity.py and must not
        be run through extract_activity_source().
        """
        raise NotImplementedError(
            '%s does not support raw text generation.' % self.label
        )

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=_PROVIDER_CODEGEN_TIMEOUT,
                                 stream_callback=None):
        """Return a complete generated activity.py source string.

        stream_callback, if provided, is called with the growing partial
        text as the provider emits tokens. Providers that do not support
        streaming may ignore it; the final returned source is always the
        complete activity.py.
        """
        return extract_activity_source(
            self.generate_plan(system_prompt, user_prompt, timeout=timeout)
        )


class GeminiProvider(LLMProvider):
    name = 'gemini'
    label = 'Gemini'

    # Google Generative Language API safety settings.  BLOCK_ONLY_HIGH keeps
    # the planner permissive for educational prompts while still refusing
    # content that the API classifies as highly harmful.
    _SAFETY_SETTINGS = [
        {
            'category': 'HARM_CATEGORY_DANGEROUS_CONTENT',
            'threshold': 'BLOCK_ONLY_HIGH',
        },
        {
            'category': 'HARM_CATEGORY_HATE_SPEECH',
            'threshold': 'BLOCK_ONLY_HIGH',
        },
        {
            'category': 'HARM_CATEGORY_HARASSMENT',
            'threshold': 'BLOCK_ONLY_HIGH',
        },
        {
            'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
            'threshold': 'BLOCK_ONLY_HIGH',
        },
    ]

    def __init__(self, api_key=None, model=None, endpoint=None):
        self._api_key = api_key or os.environ.get('GEMINI_API_KEY', '')
        self.model = model or os.environ.get(
            'AOD_GEMINI_MODEL',
            'gemini-2.5-flash',
        )
        self._endpoint = endpoint or (
            'https://generativelanguage.googleapis.com/v1beta/models'
        )
        if not self._api_key:
            raise ProviderError('Gemini API key is not configured.')

    def generate_plan(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_PLAN_TIMEOUT):
        return self._generate_json(system_prompt, user_prompt, timeout)

    def generate_text(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_CODEGEN_TIMEOUT,
                      stream_callback=None):
        if stream_callback is not None:
            return self._stream_content(
                system_prompt, user_prompt, timeout,
                max_output_tokens=_GEMINI_CODEGEN_MAX_OUTPUT_TOKENS,
                stream_callback=stream_callback,
            )
        return self._generate_content(
            system_prompt, user_prompt, timeout,
            max_output_tokens=_GEMINI_CODEGEN_MAX_OUTPUT_TOKENS,
            response_json=False,
        )

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=_PROVIDER_CODEGEN_TIMEOUT,
                                 stream_callback=None,
                                 max_output_tokens=None):
        tokens = max_output_tokens or _GEMINI_CODEGEN_MAX_OUTPUT_TOKENS
        if stream_callback is not None:
            text = self._stream_content(
                system_prompt, user_prompt, timeout,
                max_output_tokens=tokens,
                stream_callback=stream_callback,
            )
        else:
            text = self._generate_content(
                system_prompt, user_prompt, timeout,
                max_output_tokens=tokens,
                response_json=False,
            )
        return extract_activity_source_from_response(text)

    def _generate_json(self, system_prompt, user_prompt, timeout,
                       max_output_tokens=None):
        return extract_json_object(
            self._generate_content(
                system_prompt,
                user_prompt,
                timeout,
                max_output_tokens=max_output_tokens,
                response_json=True,
            )
        )

    def _generate_content(self, system_prompt, user_prompt, timeout,
                          max_output_tokens=None, response_json=True):
        model = urllib.parse.quote(self.model, safe='')
        key = urllib.parse.quote(self._api_key, safe='')
        url = '%s/%s:generateContent?key=%s' % (
            self._endpoint.rstrip('/'),
            model,
            key,
        )
        generation_config = {
            'temperature': 0.3,
        }
        if response_json:
            generation_config['responseMimeType'] = 'application/json'
        if max_output_tokens is not None:
            generation_config['maxOutputTokens'] = max_output_tokens
        payload = {
            'systemInstruction': {
                'parts': [{'text': system_prompt}],
            },
            'contents': [{
                'role': 'user',
                'parts': [{'text': user_prompt}],
            }],
            'generationConfig': generation_config,
            'safetySettings': self._SAFETY_SETTINGS,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_data = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise ProviderError(
                'Gemini request failed with HTTP %d: %s'
                % (error.code, detail)
            )
        except (OSError, ValueError) as error:
            raise ProviderError('Gemini request failed: %s' % error)

        try:
            candidate = response_data['candidates'][0]
            finish_reason = candidate.get('finishReason', '')
            if finish_reason and finish_reason != 'STOP':
                raise ProviderError(
                    'Gemini response was blocked: %s' % finish_reason
                )
            parts = candidate['content']['parts']
            text = ''.join(part.get('text', '') for part in parts)
        except (KeyError, IndexError, TypeError):
            raise ProviderError(
                'Gemini response did not contain a result.'
            )
        if not text:
            raise ProviderError('Gemini returned an empty response.')
        return text

    def _stream_content(self, system_prompt, user_prompt, timeout,
                        max_output_tokens=None, stream_callback=None):
        """Call Gemini's streaming endpoint and feed tokens to stream_callback.

        Uses :streamGenerateContent?alt=sse instead of :generateContent
        so tokens arrive as they're generated rather than all at once.
        """
        model = urllib.parse.quote(self.model, safe='')
        key = urllib.parse.quote(self._api_key, safe='')
        url = '%s/%s:streamGenerateContent?alt=sse&key=%s' % (
            self._endpoint.rstrip('/'),
            model,
            key,
        )
        generation_config = {
            'temperature': 0.3,
        }
        if max_output_tokens is not None:
            generation_config['maxOutputTokens'] = max_output_tokens
        payload = {
            'systemInstruction': {
                'parts': [{'text': system_prompt}],
            },
            'contents': [{
                'role': 'user',
                'parts': [{'text': user_prompt}],
            }],
            'generationConfig': generation_config,
            'safetySettings': self._SAFETY_SETTINGS,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        accumulated = ''
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                buf = ''
                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    buf += chunk.decode('utf-8', errors='replace')
                    while '\n' in buf:
                        line, buf = buf.split('\n', 1)
                        line = line.rstrip('\r')
                        if not line or not line.startswith('data:'):
                            continue
                        data = line[5:].strip()
                        if data == '[DONE]':
                            break
                        try:
                            event = json.loads(data)
                        except (json.JSONDecodeError, ValueError):
                            continue
                        try:
                            candidate = event['candidates'][0]
                            parts = candidate['content']['parts']
                            # Gemini sends the full accumulated text in each
                            # chunk, not just the delta — use it directly.
                            text = ''.join(
                                part.get('text', '') for part in parts
                            )
                        except (KeyError, IndexError):
                            continue
                        if not text:
                            continue
                        accumulated = text
                        if stream_callback is not None:
                            try:
                                stream_callback(accumulated)
                            except Exception:
                                logging.debug(
                                    'stream_callback raised; ignoring',
                                    exc_info=True)
                    else:
                        continue
                    break
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise ProviderError(
                'Gemini streaming request failed with HTTP %d: %s'
                % (error.code, detail)
            )
        except (OSError, ValueError) as error:
            raise ProviderError('Gemini streaming request failed: %s' % error)

        if not accumulated:
            raise ProviderError('Gemini streaming returned an empty response.')
        return accumulated


class OpenAIProvider(LLMProvider):
    name = 'openai'
    label = 'OpenAI'

    def __init__(self, api_key=None, model=None, endpoint=None):
        self._api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.model = model or os.environ.get(
            'AOD_OPENAI_MODEL',
            'gpt-4.1-mini',
        )
        self._endpoint = endpoint or os.environ.get(
            'AOD_OPENAI_ENDPOINT',
            'https://api.openai.com/v1/chat/completions',
        )
        self._user_agent = 'SugarActivityOnDemand/1.0'
        if not self._api_key:
            raise ProviderError('OpenAI API key is not configured.')

    def generate_plan(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_PLAN_TIMEOUT):
        return self._generate_json(system_prompt, user_prompt, timeout)

    def generate_text(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_CODEGEN_TIMEOUT,
                      stream_callback=None, max_output_tokens=None):
        tokens = max_output_tokens or _CODEGEN_MAX_TOKENS
        if stream_callback is not None:
            return self._stream_text(
                system_prompt, user_prompt, timeout,
                max_tokens=tokens,
                stream_callback=stream_callback,
            )
        return self._generate_text(
            system_prompt, user_prompt, timeout,
            max_tokens=tokens, json_response=False,
        )

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=_PROVIDER_CODEGEN_TIMEOUT,
                                 stream_callback=None, max_output_tokens=None):
        text = self.generate_text(
            system_prompt, user_prompt, timeout,
            stream_callback=stream_callback,
            max_output_tokens=max_output_tokens,
        )
        return extract_activity_source_from_response(text)

    def _generate_json(self, system_prompt, user_prompt, timeout,
                       max_tokens=None):
        return extract_json_object(
            self._generate_text(
                system_prompt,
                user_prompt,
                timeout,
                max_tokens=max_tokens,
                json_response=True,
            )
        )

    def _stream_text(self, system_prompt, user_prompt, timeout,
                     max_tokens, stream_callback):
        """Stream a chat-completion response token-by-token via SSE.

        Returns the full accumulated text once the stream ends; on the
        way, calls stream_callback(running_text) for each delta chunk so
        callers can surface a live preview. Provider errors raise
        ProviderError just like the non-streaming path.
        """
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': self._generation_temperature(),
            'stream': True,
        }
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        payload.update(
            self._extra_generation_params(max_tokens, json_response=False)
        )
        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers=self._request_headers(),
            method='POST',
        )
        parts = []
        try:
            with urllib.request.urlopen(
                    request, timeout=timeout) as response:
                for raw_line in response:
                    line = raw_line.decode(
                        'utf-8', errors='replace').rstrip('\r\n')
                    if not line or not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if data == '[DONE]':
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    try:
                        delta = event['choices'][0].get('delta') or {}
                    except (KeyError, IndexError, TypeError):
                        continue
                    content = delta.get('content')
                    if not isinstance(content, str) or not content:
                        continue
                    parts.append(content)
                    try:
                        stream_callback(''.join(parts))
                    except Exception:
                        # Streaming is a UX nicety; a failing UI callback
                        # must not abort generation.
                        pass
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise ProviderError(
                '%s stream failed with HTTP %d: %s'
                % (self._request_label(), error.code, detail)
            )
        except (OSError, ValueError) as error:
            raise ProviderError(
                '%s stream failed: %s' % (self._request_label(), error)
            )
        return ''.join(parts)

    def _generate_text(self, system_prompt, user_prompt, timeout,
                       max_tokens=None, json_response=True):
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': self._generation_temperature(),
        }
        if json_response:
            payload['response_format'] = {'type': 'json_object'}
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        payload.update(self._extra_generation_params(max_tokens,
                                                     json_response))
        response_data = _post_json(
            self._endpoint,
            payload,
            self._request_headers(),
            timeout,
            self._request_label(),
        )
        text = _chat_completion_message_text(
            response_data,
            self._request_label(),
        )
        return text

    def _extra_generation_params(self, max_tokens, json_response):
        """Return extra chat-completion payload fields for a request.

        Subclasses can override this to inject provider/model specific
        parameters (for example reasoning-effort control or a larger
        completion budget) without rebuilding the whole payload.
        """
        return {}

    def _generation_temperature(self):
        return 0.3

    def _request_headers(self):
        return {
            'Authorization': 'Bearer %s' % self._api_key,
            'Content-Type': 'application/json',
            'User-Agent': self._user_agent,
        }

    def _request_label(self):
        return self.label


class OpenAICompatibleProvider(OpenAIProvider):
    """OpenAI-compatible endpoints for DeepSeek, Qwen, Moonshot, etc."""

    _CONFIG = {
        'deepseek': {
            'label': 'DeepSeek',
            'key_env': 'DEEPSEEK_API_KEY',
            'model_env': 'AOD_DEEPSEEK_MODEL',
            'endpoint_env': 'AOD_DEEPSEEK_ENDPOINT',
            'default_model': 'deepseek-chat',
            'default_endpoint': 'https://api.deepseek.com/v1/chat/completions',
        },
        'qwen': {
            'label': 'Qwen',
            'key_env': 'QWEN_API_KEY',
            'model_env': 'AOD_QWEN_MODEL',
            'endpoint_env': 'AOD_QWEN_ENDPOINT',
            'default_model': 'qwen-turbo',
            'default_endpoint': (
                'https://dashscope.aliyuncs.com/'
                'compatible-mode/v1/chat/completions'
            ),
        },
        'openrouter': {
            'label': 'OpenRouter',
            'key_env': 'OPENROUTER_API_KEY',
            'model_env': 'AOD_OPENROUTER_MODEL',
            'endpoint_env': 'AOD_OPENROUTER_ENDPOINT',
            'default_model': 'anthropic/claude-opus-4.8',
            'default_endpoint': (
                'https://openrouter.ai/api/v1/chat/completions'
            ),
        },
        'moonshot': {
            'label': 'Moonshot',
            'key_env': 'MOONSHOT_API_KEY',
            'model_env': 'AOD_MOONSHOT_MODEL',
            'endpoint_env': 'AOD_MOONSHOT_ENDPOINT',
            'default_model': 'moonshot-v1-8k',
            'default_endpoint': 'https://api.moonshot.cn/v1/chat/completions',
        },
        'opencode': {
            'label': 'OpenCode Zen',
            'key_env': 'OPENCODE_API_KEY',
            'model_env': 'AOD_OPENCODE_MODEL',
            'endpoint_env': 'AOD_OPENCODE_ENDPOINT',
            'default_model': 'claude-sonnet-4-6',
            'default_endpoint': 'https://opencode.ai/zen/v1/chat/completions',
        },
        'opencode-go': {
            'label': 'OpenCode Go',
            'key_env': 'OPENCODE_API_KEY',
            'model_env': 'AOD_OPENCODE_GO_MODEL',
            'endpoint_env': 'AOD_OPENCODE_GO_ENDPOINT',
            # Kimi K2.7 Code is the code-tuned variant and reliably
            # produces complete activity.py sources. Kimi K2.6 is a
            # reasoning model that often exhausts its output budget on
            # chain-of-thought before writing the activity; it remains
            # selectable via the model field.
            'default_model': 'kimi-k2.7-code',
            'default_endpoint': (
                'https://opencode.ai/zen/go/v1/chat/completions'
            ),
        },
    }

    def __init__(self, api_key=None, model=None, endpoint=None,
                 provider_name='openai-compatible'):
        config = self._CONFIG.get(provider_name, {})
        self._provider_name = provider_name
        self.name = provider_name
        self.label = config.get('label', provider_name.capitalize())
        self._api_key = api_key or os.environ.get(
            config.get('key_env', 'OPENAI_API_KEY'), ''
        )
        self.model = model or os.environ.get(
            config.get('model_env', 'AOD_OPENAI_MODEL'),
            config.get('default_model', 'gpt-4.1-mini'),
        )
        self._endpoint = endpoint or os.environ.get(
            config.get('endpoint_env', 'AOD_OPENAI_ENDPOINT'),
            config.get(
                'default_endpoint',
                'https://api.openai.com/v1/chat/completions',
            ),
        )
        self._user_agent = 'SugarActivityOnDemand/1.0'
        # OpenCode's API is fronted by Cloudflare and requires an
        # OpenCode-identifying User-Agent to avoid a 1010 block.
        if provider_name in ('opencode', 'opencode-go'):
            self._user_agent = 'OpenCode-AI-SDK/1.0'
        if not self._api_key:
            raise ProviderError('%s API key is not configured.' % self.label)

    def _generation_temperature(self):
        if self._provider_name == 'opencode-go' and \
                self.model == 'kimi-k2.7-code':
            return 1.0
        return OpenAIProvider._generation_temperature(self)

    def _request_headers(self):
        headers = OpenAIProvider._request_headers(self)
        if self._provider_name == 'openrouter':
            headers['HTTP-Referer'] = 'https://www.sugarlabs.org/'
            headers['X-Title'] = 'Sugar Activity on Demand'
        return headers

    def _extra_generation_params(self, max_tokens, json_response):
        params = {}
        # For codegen (non-JSON) calls on OpenRouter, set minimal reasoning.
        # OpenRouter defaults to extra thinking for many models, which adds
        # a long delay before the first useful activity.py token. Minimal
        # reasoning favors fast, visible codegen.
        if not json_response and self._provider_name == 'openrouter':
            effort = os.environ.get(
                'AOD_OPENROUTER_CODEGEN_REASONING_EFFORT',
                _OPENROUTER_REASONING_CODEGEN_EFFORT,
            )
            if effort:
                effort = effort.strip()
                if effort.lower() in _REASONING_DISABLE_VALUES:
                    effort = _REASONING_SAFE_MINIMAL_EFFORT
                params['reasoning'] = {'effort': effort}
            if not self._is_reasoning_codegen(json_response):
                params['max_tokens'] = _env_int(
                    'AOD_OPENROUTER_FAST_CODEGEN_MAX_TOKENS',
                    _OPENROUTER_FAST_CODEGEN_MAX_TOKENS,
                )
                return params

        # The activity-codegen call uses json_response=False with a
        # bounded max_tokens.  Plan calls (json_response=True) leave
        # max_tokens uncapped, so reasoning has room and we do not need
        # to intervene there.
        if not self._is_reasoning_codegen(json_response):
            return params

        budget = max_tokens or 0
        budget = max(
            budget,
            _env_int('AOD_OPENROUTER_CODEGEN_MAX_TOKENS',
                     _OPENROUTER_REASONING_CODEGEN_MAX_TOKENS),
        )
        params['max_tokens'] = budget
        return params

    def _is_reasoning_codegen(self, json_response):
        """True for a reasoning-capable Kimi model on OpenRouter during
        activity-codegen (non-JSON) calls, where the default reasoning
        budget would otherwise starve the generated activity.py."""
        if json_response:
            return False
        if self._provider_name != 'openrouter':
            return False
        model = (self.model or '').lower().lstrip('~')
        return model.startswith('moonshotai/kimi')


class FreeModelProvider(LLMProvider):
    name = 'freemodel'
    label = 'FreeModel'

    def __init__(self, api_key=None, model=None, endpoint=None):
        self._api_key = api_key or os.environ.get('FREEMODEL_API_KEY', '')
        self.model = model or os.environ.get(
            'AOD_FREEMODEL_MODEL',
            'gpt-5.5',
        )
        self._endpoint = _responses_endpoint(
            endpoint or os.environ.get(
                'AOD_FREEMODEL_ENDPOINT',
                'https://api.freemodel.dev',
            )
        )
        self._reasoning_effort = os.environ.get(
            'AOD_FREEMODEL_REASONING_EFFORT',
            'xhigh',
        )
        self._codegen_reasoning_effort = os.environ.get(
            'AOD_FREEMODEL_CODEGEN_REASONING_EFFORT',
            'high',
        )
        if not self._api_key:
            raise ProviderError('FreeModel API key is not configured.')

    def generate_plan(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_PLAN_TIMEOUT):
        return self._generate_json(system_prompt, user_prompt, timeout)

    def generate_text(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_CODEGEN_TIMEOUT,
                      stream_callback=None, max_output_tokens=None):
        text = self._generate_responses_text(
            system_prompt, user_prompt, timeout,
            max_output_tokens=(
                max_output_tokens or _FREEMODEL_CODEGEN_MAX_OUTPUT_TOKENS),
            reasoning_effort=self._codegen_reasoning_effort,
        )
        if stream_callback is not None:
            try:
                stream_callback(text)
            except Exception:
                pass
        return text

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=_PROVIDER_CODEGEN_TIMEOUT,
                                 stream_callback=None, max_output_tokens=None):
        text = self.generate_text(
            system_prompt, user_prompt, timeout,
            stream_callback=stream_callback,
            max_output_tokens=max_output_tokens,
        )
        return extract_activity_source_from_response(text)

    def _generate_json(self, system_prompt, user_prompt, timeout,
                       max_output_tokens=None, reasoning_effort=None):
        return extract_json_object(
            self._generate_responses_text(
                system_prompt,
                user_prompt,
                timeout,
                max_output_tokens=max_output_tokens,
                reasoning_effort=reasoning_effort,
            )
        )

    def _generate_responses_text(self, system_prompt, user_prompt, timeout,
                                 max_output_tokens=None, reasoning_effort=None):
        payload = {
            'model': self.model,
            'instructions': system_prompt,
            'input': user_prompt,
        }
        effort = reasoning_effort
        if effort is None:
            effort = self._reasoning_effort
        if effort:
            payload['reasoning'] = {'effort': effort}
        if max_output_tokens is not None:
            payload['max_output_tokens'] = max_output_tokens

        response_data = _post_json(
            self._endpoint,
            payload,
            {
                'Authorization': 'Bearer %s' % self._api_key,
                'Content-Type': 'application/json',
            },
            timeout,
            'FreeModel',
        )
        return _responses_text(response_data)


class ClaudeProvider(LLMProvider):
    name = 'claude'
    label = 'Claude'

    def __init__(self, api_key=None, model=None, endpoint=None):
        self._api_key = api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        self.model = model or os.environ.get(
            'AOD_CLAUDE_MODEL',
            'claude-3-5-haiku-latest',
        )
        self._endpoint = endpoint or os.environ.get(
            'AOD_CLAUDE_ENDPOINT',
            'https://api.anthropic.com/v1/messages',
        )
        if not self._api_key:
            raise ProviderError('Claude API key is not configured.')

    def generate_plan(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_PLAN_TIMEOUT):
        return self._generate_json(
            system_prompt,
            user_prompt,
            timeout,
            max_tokens=1600,
        )

    def generate_text(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_CODEGEN_TIMEOUT,
                      stream_callback=None, max_output_tokens=None):
        text = self._generate_text(
            system_prompt, user_prompt, timeout,
            max_tokens=max_output_tokens or _CODEGEN_MAX_TOKENS,
        )
        if stream_callback is not None:
            try:
                stream_callback(text)
            except Exception:
                pass
        return text

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=_PROVIDER_CODEGEN_TIMEOUT,
                                 stream_callback=None, max_output_tokens=None):
        text = self.generate_text(
            system_prompt, user_prompt, timeout,
            stream_callback=stream_callback,
            max_output_tokens=max_output_tokens,
        )
        return extract_activity_source_from_response(text)

    def _generate_json(self, system_prompt, user_prompt, timeout,
                       max_tokens):
        return extract_json_object(
            self._generate_text(system_prompt, user_prompt, timeout,
                                max_tokens=max_tokens)
        )

    def _generate_text(self, system_prompt, user_prompt, timeout,
                       max_tokens):
        payload = {
            'model': self.model,
            'max_tokens': max_tokens,
            'temperature': 0.3,
            'system': system_prompt,
            'messages': [
                {'role': 'user', 'content': user_prompt},
            ],
        }
        response_data = _post_json(
            self._endpoint,
            payload,
            {
                'anthropic-version': os.environ.get(
                    'AOD_CLAUDE_VERSION',
                    '2023-06-01',
                ),
                'x-api-key': self._api_key,
                'Content-Type': 'application/json',
            },
            timeout,
            'Claude',
        )
        try:
            parts = response_data['content']
            text = ''.join(
                part.get('text', '') for part in parts
                if part.get('type') == 'text'
            )
        except (KeyError, TypeError):
            raise ProviderError('Claude response did not contain a result.')
        return text


class OllamaProvider(LLMProvider):
    name = 'ollama'
    label = 'Ollama'

    def __init__(self, model=None, endpoint=None):
        self.model = model or os.environ.get(
            'AOD_OLLAMA_MODEL',
            'llama3.1',
        )
        base_url = os.environ.get(
            'AOD_OLLAMA_URL',
            os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'),
        )
        self._endpoint = endpoint or os.environ.get(
            'AOD_OLLAMA_ENDPOINT',
            '%s/api/generate' % base_url.rstrip('/'),
        )

    def generate_plan(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_PLAN_TIMEOUT):
        return self._generate_json(system_prompt, user_prompt, timeout)

    def generate_text(self, system_prompt, user_prompt,
                      timeout=_PROVIDER_CODEGEN_TIMEOUT,
                      stream_callback=None, max_output_tokens=None):
        text = self._generate_text(
            system_prompt, user_prompt, timeout,
            num_predict=max_output_tokens or _CODEGEN_MAX_TOKENS,
        )
        if stream_callback is not None:
            try:
                stream_callback(text)
            except Exception:
                pass
        return text

    def generate_activity_source(self, system_prompt, user_prompt,
                                 timeout=_PROVIDER_CODEGEN_TIMEOUT,
                                 stream_callback=None, max_output_tokens=None):
        text = self.generate_text(
            system_prompt, user_prompt, timeout,
            stream_callback=stream_callback,
            max_output_tokens=max_output_tokens,
        )
        return extract_activity_source_from_response(text)

    def _generate_json(self, system_prompt, user_prompt, timeout,
                       num_predict=None):
        return extract_json_object(
            self._generate_text(
                system_prompt,
                user_prompt,
                timeout,
                num_predict=num_predict,
                json_mode=True,
            )
        )

    def _generate_text(self, system_prompt, user_prompt, timeout,
                       num_predict=None, json_mode=False):
        options = {
            'temperature': 0.3,
        }
        if num_predict is not None:
            options['num_predict'] = num_predict
        payload = {
            'model': self.model,
            'prompt': '%s\n\n%s' % (system_prompt, user_prompt),
            'stream': False,
            'options': options,
        }
        if json_mode:
            payload['format'] = 'json'
        response_data = _post_json(
            self._endpoint,
            payload,
            {'Content-Type': 'application/json'},
            timeout,
            'Ollama',
        )
        try:
            text = response_data['response']
        except (KeyError, TypeError):
            raise ProviderError('Ollama response did not contain a result.')
        return text


def _responses_endpoint(endpoint):
    endpoint = (endpoint or 'https://api.freemodel.dev').strip().rstrip('/')
    if endpoint.endswith('/responses'):
        return endpoint
    if endpoint.endswith('/v1'):
        return endpoint + '/responses'
    return endpoint + '/v1/responses'


def _responses_text(response_data):
    direct_text = response_data.get('output_text')
    if isinstance(direct_text, str) and direct_text:
        return direct_text

    blocks = []
    output = response_data.get('output')
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            text = item.get('text')
            if isinstance(text, str):
                blocks.append(text)
            content = item.get('content')
            if isinstance(content, str):
                blocks.append(content)
            elif isinstance(content, list):
                for content_item in content:
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get('text')
                    if isinstance(text, str):
                        blocks.append(text)

    if blocks:
        return ''.join(blocks)

    raise ProviderError('FreeModel response did not contain a result.')


def _chat_completion_message_text(response_data, label):
    try:
        choices = response_data['choices']
        choice = choices[0]
    except (KeyError, IndexError, TypeError):
        raise ProviderError('%s response did not contain a result.' % label)

    if not isinstance(choice, dict):
        raise ProviderError('%s response did not contain a result.' % label)

    message = choice.get('message') or choice.get('delta') or {}
    if not isinstance(message, dict):
        raise ProviderError('%s response did not contain a result.' % label)

    text = _content_to_text(message.get('content')).strip()
    if text:
        return text

    refusal = (
        _content_to_text(message.get('refusal')).strip() or
        _content_refusal_text(message.get('content')).strip()
    )
    if refusal:
        raise ProviderError(
            '%s refused the request: %s' % (label, refusal[:300])
        )

    tool_calls = message.get('tool_calls') or choice.get('tool_calls')
    if tool_calls:
        raise ProviderError(
            '%s returned tool calls instead of activity text. Select a '
            'text/code chat model for generation.' % label
        )

    finish_reason = (
        choice.get('finish_reason') or choice.get('finishReason') or ''
    )
    if finish_reason:
        raise ProviderError(
            _chat_finish_reason_error(label, finish_reason, message)
        )

    reasoning = (
        _content_to_text(message.get('reasoning_content')).strip() or
        _content_to_text(message.get('reasoning')).strip()
    )
    if reasoning:
        raise ProviderError(
            '%s returned reasoning but no final activity text. Try rerunning '
            'with a smaller prompt or a text/code model that returns normal '
            'assistant content.' % label
        )

    raise ProviderError(
        '%s returned an empty assistant message with no activity text content.'
        % label
    )


def _content_refusal_text(value):
    if isinstance(value, list):
        blocks = []
        for item in value:
            if isinstance(item, dict):
                blocks.append(_content_to_text(item.get('refusal')))
        return ''.join(blocks)
    if isinstance(value, dict):
        return _content_to_text(value.get('refusal'))
    return ''


def _chat_finish_reason_error(label, finish_reason, message):
    reason = str(finish_reason)
    if reason == 'length':
        return (
            '%s stopped before returning activity.py '
            '(finish_reason=length). Try a smaller activity prompt or a '
            'model with a larger output budget.' % label
        )
    if reason in ('content_filter', 'safety'):
        return (
            '%s blocked the activity response '
            '(finish_reason=%s). Try a classroom-safe wording or a different '
            'model.' % (label, reason)
        )
    if reason == 'tool_calls':
        return (
            '%s returned tool calls instead of activity text. Select a '
            'text/code chat model for generation.' % label
        )

    detail = _content_to_text(message.get('reasoning_content')).strip()
    if detail:
        return (
            '%s returned no final activity text '
            '(finish_reason=%s) after reasoning. Try rerunning with a smaller '
            'prompt or a different OpenRouter route/model.'
            % (label, reason)
        )
    return (
        '%s returned no activity text (finish_reason=%s). Try rerunning or '
        'switching to a text/code model such as '
        'anthropic/claude-opus-4.8.'
        % (label, reason)
    )


def _raise_response_error(response_data, label):
    if not isinstance(response_data, dict):
        return
    error = response_data.get('error')
    if not error:
        return

    if isinstance(error, dict):
        message = _content_to_text(error.get('message')).strip()
        if not message:
            message = _content_to_text(error.get('detail')).strip()
        code = error.get('code') or error.get('type')
        if code and message:
            message = '%s: %s' % (code, message)
        elif code:
            message = str(code)
        if not message:
            try:
                message = json.dumps(error, sort_keys=True)[:500]
            except (TypeError, ValueError):
                message = str(error)[:500]
    else:
        message = str(error)[:500]

    raise ProviderError('%s request failed: %s' % (label, message))


def _content_to_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ''.join(_content_to_text(item) for item in value)
    if isinstance(value, dict):
        blocks = []
        for key in ('text', 'content', 'output_text', 'value'):
            text = _content_to_text(value.get(key))
            if text:
                blocks.append(text)
        parts = value.get('parts')
        if isinstance(parts, list):
            blocks.append(_content_to_text(parts))
        return ''.join(blocks)
    return ''


def _post_json(url, payload, headers, timeout, label):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace')[:500]
        raise ProviderError(
            '%s request failed with HTTP %d: %s'
            % (label, error.code, detail)
        )
    except (OSError, ValueError) as error:
        raise ProviderError('%s request failed: %s' % (label, error))
    _raise_response_error(response_data, label)
    return response_data


_PROVIDER_FACTORIES = {
    'gemini': GeminiProvider,
    'openai': OpenAIProvider,
    'openrouter': OpenAICompatibleProvider,
    'deepseek': OpenAICompatibleProvider,
    'qwen': OpenAICompatibleProvider,
    'moonshot': OpenAICompatibleProvider,
    'opencode': OpenAICompatibleProvider,
    'opencode-go': OpenAICompatibleProvider,
    'freemodel': FreeModelProvider,
    'claude': ClaudeProvider,
    'ollama': OllamaProvider,
}


def normalize_provider_name(provider_name):
    name = (provider_name or 'default').strip().lower()
    aliases = {
        'anthropic': 'claude',
        'codex': 'openai',
        'default': 'default',
        'deepseek': 'deepseek',
        'freemodel': 'freemodel',
        'gemini': 'gemini',
        'google': 'gemini',
        'local': 'local-template',
        'local-template': 'local-template',
        'moonshot': 'moonshot',
        'none': 'local-template',
        'offline': 'local-template',
        'ollama': 'ollama',
        'opencode': 'opencode',
        'opencode-go': 'opencode-go',
        'openai': 'openai',
        'openrouter': 'openrouter',
        'qwen': 'qwen',
        'template': 'local-template',
    }
    return aliases.get(name, name)


def create_provider(provider_name, api_key=None, model=None, endpoint=None):
    """Create a provider from runtime settings without persisting secrets."""
    requested = normalize_provider_name(provider_name)
    if requested == 'default':
        requested = get_default_provider_name()
    if requested == 'local-template':
        return None

    factory = _PROVIDER_FACTORIES.get(requested)
    if factory is None:
        raise ProviderError('Unknown LLM provider: %s' % requested)

    settings = {}
    if model:
        settings['model'] = model
    if endpoint:
        settings['endpoint'] = endpoint
    if requested != 'ollama' and api_key:
        settings['api_key'] = api_key
    if issubclass(factory, OpenAICompatibleProvider):
        settings['provider_name'] = requested
    return factory(**settings)


def get_default_provider_name():
    requested = normalize_provider_name(
        os.environ.get('AOD_LLM_PROVIDER', 'default')
    )
    if requested != 'default':
        return requested

    for name in ('gemini', 'openai', 'openrouter', 'claude', 'deepseek',
                 'qwen', 'moonshot', 'opencode', 'opencode-go',
                 'freemodel'):
        if _is_cloud_provider_configured(name):
            return name
    if os.environ.get('AOD_OLLAMA_MODEL') or \
            os.environ.get('AOD_OLLAMA_URL') or \
            os.environ.get('OLLAMA_HOST'):
        return 'ollama'
    return 'local-template'


def get_local_provider_name():
    if _is_provider_configured('ollama'):
        return 'ollama'
    return 'local-template'


def get_configured_provider(provider_name='default'):
    return create_provider(provider_name)


def get_provider_statuses():
    """Return provider availability for preferences and diagnostics."""
    statuses = [{
        'name': 'local-template',
        'label': 'Local template planner',
        'available': True,
        'configured': True,
        'model': 'template',
        'reason': '',
    }]

    for name in ('gemini', 'openai', 'openrouter', 'deepseek', 'qwen',
                 'moonshot', 'opencode', 'opencode-go', 'freemodel',
                 'claude', 'ollama'):
        configured = _is_provider_configured(name)
        statuses.append({
            'name': name,
            'label': _provider_label(name),
            'available': configured,
            'configured': configured,
            'model': _provider_model(name),
            'reason': '' if configured else _provider_missing_reason(name),
        })
    return statuses


def _is_provider_configured(name):
    if name == 'ollama':
        provider = normalize_provider_name(
            os.environ.get('AOD_LLM_PROVIDER', '')
        )
        return any((
            os.environ.get('AOD_OLLAMA_MODEL'),
            os.environ.get('AOD_OLLAMA_URL'),
            os.environ.get('OLLAMA_HOST'),
            provider == 'ollama',
        ))
    return _is_cloud_provider_configured(name)


def _is_cloud_provider_configured(name):
    key_name = _provider_key_env(name)
    return bool(key_name and os.environ.get(key_name))


def _provider_label(name):
    if name in OpenAICompatibleProvider._CONFIG:
        return OpenAICompatibleProvider._CONFIG[name]['label']
    return _PROVIDER_FACTORIES[name].label


def _provider_key_env(name):
    if name in OpenAICompatibleProvider._CONFIG:
        return OpenAICompatibleProvider._CONFIG[name]['key_env']
    key_by_name = {
        'freemodel': 'FREEMODEL_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'claude': 'ANTHROPIC_API_KEY',
    }
    return key_by_name.get(name)


def _provider_model(name):
    model_env = {
        'gemini': ('AOD_GEMINI_MODEL', 'gemini-2.5-flash'),
        'openai': ('AOD_OPENAI_MODEL', 'gpt-4.1-mini'),
        'openrouter': (
            'AOD_OPENROUTER_MODEL',
            'anthropic/claude-opus-4.8',
        ),
        'deepseek': ('AOD_DEEPSEEK_MODEL', 'deepseek-chat'),
        'qwen': ('AOD_QWEN_MODEL', 'qwen-turbo'),
        'moonshot': ('AOD_MOONSHOT_MODEL', 'moonshot-v1-8k'),
        'opencode': ('AOD_OPENCODE_MODEL', 'claude-sonnet-4-6'),
        'opencode-go': ('AOD_OPENCODE_GO_MODEL', 'kimi-k2.7-code'),
        'freemodel': ('AOD_FREEMODEL_MODEL', 'gpt-5.5'),
        'claude': ('AOD_CLAUDE_MODEL', 'claude-3-5-haiku-latest'),
        'ollama': ('AOD_OLLAMA_MODEL', 'llama3.1'),
    }
    env_name, default = model_env[name]
    return os.environ.get(env_name, default)


def _provider_missing_reason(name):
    if name == 'ollama':
        return 'Set AOD_LLM_PROVIDER=ollama or AOD_OLLAMA_MODEL.'
    return 'Set %s.' % _provider_key_env(name)
