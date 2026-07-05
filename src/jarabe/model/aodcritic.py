# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""One self-review round over freshly generated activity code.

The generated source already passed static validation and the runtime
gate, so it works — but working code can still be shallow: buttons
without handlers, win conditions that never fire, Journal methods that
save nothing real.  This module asks the model to review its own
output once and return either OK or minimal SEARCH/REPLACE fixes.

The critic is strictly fail-safe.  The unpatched source is already
validated and runtime-proven, so on any doubt — unparseable reply,
failed patch, patched code failing validation or the runtime gate —
the original is kept and generation continues as if the critic had
said OK.
"""

import logging
import os

from jarabe.model.aodrefine import apply_patches
from jarabe.model.aodrefine import parse_search_replace
from jarabe.model.aodruntime import run_runtime_check
from jarabe.model.aodvalidator import validate_activity_source_for_request


def build_critic_system_prompt():
    return (
        'You are Sugar Activity on Demand, reviewing a Sugar activity '
        'you just wrote before it is given to a learner.\n\n'
        'Check the code against this list:\n'
        '- Every button, entry, and control is connected to a handler '
        'that does something visible.\n'
        '- The win / success / feedback logic is actually reachable by '
        'playing the activity.\n'
        '- write_file saves the real activity state and read_file '
        'restores it, so closing and reopening resumes the activity.\n'
        '- The learner can tell what to do: instructions or labels are '
        'visible on screen.\n'
        '- No dead code, placeholder text, or TODO stubs remain.\n\n'
        'If the code passes the whole list, reply with exactly:\n'
        'OK\n'
        '...and nothing else.\n\n'
        'Otherwise return ONLY minimal fixes as SEARCH/REPLACE blocks '
        'in this exact format:\n\n'
        '<<<<<<< SEARCH\n'
        '<exact lines from the current source to find>\n'
        '=======\n'
        '<replacement lines>\n'
        '>>>>>>> REPLACE\n\n'
        'Rules:\n'
        '- The SEARCH section must be copied EXACTLY from the current '
        'source, including indentation and whitespace.\n'
        '- Keep each SEARCH block small but unique (3-10 lines).\n'
        '- Fix only real defects from the list above.  Do NOT restyle, '
        'rename, or rewrite working code.\n'
        '- FULLREGEN is not allowed here.  If you cannot express a fix '
        'as small SEARCH/REPLACE blocks, reply OK instead.\n'
        '- Preserve all Sugar Activity patterns: ToolbarBox, '
        'StopButton, set_canvas, read_file/write_file, Journal '
        'persistence.\n'
        '- Keep the same class name GeneratedActivity.\n'
        '- Use only classroom-safe imports.  No networking, '
        'subprocesses, or filesystem access.\n'
    )


def build_critic_user_prompt(spec, plan, source, warnings=None):
    parts = [
        'Review the activity.py you generated for this request.\n\n',
        'Activity: %s\n' % getattr(spec, 'name', ''),
        'Request: %s\n' % getattr(spec, 'prompt', ''),
    ]
    summary = plan.get('summary') if isinstance(plan, dict) else None
    if summary:
        parts.append('Planned summary: %s\n' % summary)
    if warnings:
        parts.append('\nThe validator raised these concerns:\n')
        parts.extend('- %s\n' % warning for warning in warnings)
    parts.append('\nCurrent activity.py (%d lines):\n' % source.count('\n'))
    parts.append(source.rstrip())
    parts.append(
        '\n\n---\n\n'
        'Reply with exactly OK if the code passes the checklist, or '
        'with minimal SEARCH/REPLACE blocks copied EXACTLY from the '
        'source above.'
    )
    return ''.join(parts)


def run_critic_round(provider, spec, plan, source, warnings=None):
    """Return the (possibly patched) source; never raises.

    Records the outcome in plan['critic']: 'ok' when the model found
    nothing to fix, 'patched:N' when N fixes were applied and the
    result re-passed validation and the runtime gate, 'skipped' in
    every other case.
    """
    plan['critic'] = 'skipped'

    if os.environ.get('AOD_CRITIC', 'on').lower() in (
            'off', '0', 'no', 'false'):
        return source
    generate_text = getattr(provider, 'generate_text', None)
    if not callable(generate_text):
        return source

    try:
        response = generate_text(
            build_critic_system_prompt(),
            build_critic_user_prompt(spec, plan, source, warnings),
        )
    except Exception as error:
        logging.warning('Critic call failed: %s', error)
        return source

    if not isinstance(response, str) or response.strip() == 'OK':
        plan['critic'] = 'ok'
        return source

    try:
        patches = parse_search_replace(response)
    except ValueError:
        logging.warning('Critic reply was not OK or valid patches')
        return source
    if patches is None:  # FULLREGEN — forbidden for the critic.
        return source

    patched, applied, failed = apply_patches(source, patches)
    if failed or not applied:
        logging.warning('Critic patches failed to apply (%d failed)', failed)
        return source

    report = validate_activity_source_for_request(patched, spec, plan)
    if not report.valid:
        logging.warning('Critic patch broke validation; keeping original')
        return source
    runtime_ok, _detail = run_runtime_check(
        patched, getattr(spec, 'name', 'Generated Activity'))
    if not runtime_ok:
        logging.warning('Critic patch broke the runtime gate; '
                        'keeping original')
        return source

    plan['critic'] = 'patched:%d' % applied
    return patched
