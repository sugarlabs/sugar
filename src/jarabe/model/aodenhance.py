# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Expand a learner's short idea into a clear activity brief.

Learner prompts are often a handful of words ("space racer 2d game"),
which forces the planner and code generator to guess gameplay,
controls, UI, and the learning goal.  This module asks the configured
provider for a compact plain-text brief that keeps the learner's
intent, and degrades to the original prompt on any failure — an
enhancement problem must never break generation.
"""

import logging
import re

from jarabe.model.aodspec import MAX_PROMPT_LENGTH

_ENHANCE_TIMEOUT = 120

# Prompts already this detailed are left alone by auto-enhancement.
_AUTO_MAX_WORDS = 40
_AUTO_MAX_CHARS = 400

_MIN_USEFUL_RESULT = 20


def build_enhance_system_prompt():
    return (
        "You turn a learner's short activity idea into a clear brief "
        'for generating a Sugar (GTK3) learning activity.\n'
        "Keep the learner's intent and vocabulary — clarify it, do not "
        'replace it.\n'
        'Return PLAIN TEXT only, at most 180 words: one sentence '
        'stating what the activity is, then short lines covering:\n'
        '- gameplay / interaction (what the learner actually does)\n'
        '- the main screen regions and controls\n'
        '- the win or completion rule\n'
        '- what the learner practices or learns\n'
        '- what gets saved to the Journal\n'
        'No markdown headers, no code, no questions, no preamble like '
        '"Here is". Write it as the activity request itself.'
    )


def build_enhance_user_prompt(prompt, spec=None):
    context = ''
    if spec is not None:
        context = (
            '\nLearning category: %s\nAge band: %s'
            % (spec.category, spec.age_band)
        )
    return 'Learner idea: %s%s' % (prompt, context)


def needs_enhancement(prompt):
    """Whether auto-enhancement should run for this prompt.

    Detailed prompts (long, or already expanded with the Enhance
    button) are used as-is.
    """
    text = (prompt or '').strip()
    if not text:
        return False
    return len(text.split()) < _AUTO_MAX_WORDS and \
        len(text) < _AUTO_MAX_CHARS


def enhance_prompt(provider, prompt, spec=None, timeout=_ENHANCE_TIMEOUT):
    """Return (prompt_text, enhanced) — fail-soft, never raises.

    On success the returned text is the cleaned brief and enhanced is
    True; on any failure the original prompt comes back unchanged with
    enhanced False.
    """
    original = (prompt or '').strip()
    if not original or provider is None:
        return original, False

    try:
        response = provider.generate_text(
            build_enhance_system_prompt(),
            build_enhance_user_prompt(original, spec),
            timeout=timeout,
        )
    except Exception as error:
        logging.warning('Prompt enhancement failed: %s', error)
        return original, False

    cleaned = _clean(response)
    if len(cleaned) < _MIN_USEFUL_RESULT:
        logging.warning('Prompt enhancement returned too little text')
        return original, False
    return cleaned, True


def _clean(text):
    if not isinstance(text, str):
        return ''
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```[a-zA-Z0-9_-]*\n?', '', cleaned)
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and \
            cleaned[0] in ('"', "'"):
        cleaned = cleaned[1:-1].strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    if len(cleaned) > MAX_PROMPT_LENGTH:
        cleaned = cleaned[:MAX_PROMPT_LENGTH].rstrip()
    return cleaned
