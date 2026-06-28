# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""SEARCH/REPLACE refinement for generated Sugar activities.

Instead of regenerating the entire activity.py on every refinement,
this module asks the model to return only the changed regions as
SEARCH/REPLACE blocks.  This cuts output tokens from ~12k to ~1k per
refinement, making classroom iteration 10-20x cheaper and faster.

If any SEARCH block does not match the current source (the model
hallucinated a line, or the change is too large for a small diff),
the caller falls back to full regeneration.
"""

import re


SEARCH_MARKER = '<<<<<<< SEARCH'
DIVIDER_MARKER = '======='
REPLACE_MARKER = '>>>>>>> REPLACE'


def build_refine_system_prompt():
    """System prompt for SEARCH/REPLACE refinement.

    This is a separate prompt from the codegen system prompt because
    the task is fundamentally different: the model is editing existing
    code, not writing new code from scratch.
    """
    return (
        'You are Sugar Activity on Demand, editing an existing Sugar '
        'activity.\n\n'
        'The user will give you the current activity.py and a refinement '
        'request.  Return ONLY the changes as SEARCH/REPLACE blocks in '
        'this exact format:\n\n'
        '<<<<<<< SEARCH\n'
        '<exact lines from the current source to find>\n'
        '=======\n'
        '<replacement lines>\n'
        '>>>>>>> REPLACE\n\n'
        'Rules:\n'
        '- The SEARCH section must be copied EXACTLY from the current '
        'source, including indentation and whitespace.  Do not paraphrase '
        'or reformat.\n'
        '- The REPLACE section is the new code that replaces the SEARCH '
        'section.\n'
        '- You may output multiple SEARCH/REPLACE blocks.  Separate them '
        'with a blank line.\n'
        '- Keep each SEARCH block as small as possible while still being '
        'unique in the file.  3-10 lines is ideal.\n'
        '- Do NOT output the entire file.  Do NOT output anything except '
        'SEARCH/REPLACE blocks.  No explanations, no markdown, no code '
        'fences.\n'
        '- If the refinement requires adding new methods or large new '
        'sections, use a SEARCH block that matches an anchor line (like '
        'a method definition or the end of a class) and include the new '
        'code in the REPLACE section.\n'
        '- If the refinement is too large to express as SEARCH/REPLACE '
        'blocks (e.g. rewriting most of the file), output exactly:\n'
        'FULLREGEN\n'
        '...and nothing else.  The system will fall back to full '
        'regeneration.\n'
        '- Preserve all Sugar Activity patterns: ToolbarBox, StopButton, '
        'set_canvas, read_file/write_file, Journal persistence.\n'
        '- Keep the same class name GeneratedActivity.\n'
        '- Use only classroom-safe imports.  No networking, subprocesses, '
        'or filesystem access.\n'
    )


def build_refine_user_prompt(current_source, refinement_request,
                             plan_context=''):
    """User prompt for SEARCH/REPLACE refinement.

    Sends the full current source so the model can copy exact lines for
    SEARCH blocks.  The plan context is optional and kept small.
    """
    parts = [
        'Refine this Sugar activity.py according to the request below.\n',
        'Current activity.py (%d lines):\n' % current_source.count('\n'),
        current_source.rstrip(),
        '\n\n---\n\nRefinement request:\n',
        refinement_request,
    ]
    if plan_context:
        parts.append('\n\nPlan context (for reference):\n')
        parts.append(plan_context)
    parts.append(
        '\n\n---\n\n'
        'Return SEARCH/REPLACE blocks for the changes.  Copy SEARCH '
        'lines EXACTLY from the source above.  If the change is too '
        'large, output FULLREGEN.'
    )
    return ''.join(parts)


def parse_search_replace(response):
    """Parse SEARCH/REPLACE blocks from a model response.

    Returns a list of (search, replace) tuples, or None if the model
    requested FULLREGEN, or raises ValueError if the response is
    malformed.
    """
    if not isinstance(response, str):
        raise ValueError('Refinement response must be text.')

    text = response.strip()

    if text.startswith('FULLREGEN') and SEARCH_MARKER not in text:
        return None

    blocks = []
    pos = 0
    _NL_DIVIDER = '\n' + DIVIDER_MARKER
    _NL_REPLACE = '\n' + REPLACE_MARKER

    while True:
        search_start = text.find(SEARCH_MARKER, pos)
        if search_start < 0:
            break

        after_search = search_start + len(SEARCH_MARKER)

        # Anchor to line boundary so '=======' inside source code is ignored.
        divider_nl = text.find(_NL_DIVIDER, after_search)
        if divider_nl < 0:
            raise ValueError(
                'Malformed SEARCH/REPLACE: missing ======= divider after '
                '<<<<<<< SEARCH at position %d.' % search_start
            )
        after_divider = divider_nl + len(_NL_DIVIDER)

        # Same anchoring for >>>>>>> REPLACE.
        replace_nl = text.find(_NL_REPLACE, after_divider)
        if replace_nl < 0:
            raise ValueError(
                'Malformed SEARCH/REPLACE: missing >>>>>>> REPLACE after '
                '======= divider at position %d.' % divider_nl
            )

        search_text = _strip_block_edges(text[after_search:divider_nl])
        replace_text = _strip_block_edges(text[after_divider:replace_nl])

        if not search_text:
            raise ValueError(
                'Malformed SEARCH/REPLACE: empty SEARCH section at '
                'position %d.' % search_start
            )

        blocks.append((search_text, replace_text))
        pos = replace_nl + len(_NL_REPLACE)

    if not blocks:
        if '<<<<<<<' not in text:
            raise ValueError(
                'Refinement response did not contain SEARCH/REPLACE '
                'blocks.  If the change is too large, output FULLREGEN.'
            )
        raise ValueError(
            'Refinement response contained SEARCH markers but no valid '
            'blocks were parsed.'
        )

    return blocks


def apply_patches(source, patches):
    """Apply SEARCH/REPLACE patches to source code.

    Returns (patched_source, applied_count, failed_count).  Each patch
    is a (search, replace) tuple.  Matching is whitespace-tolerant: we
    normalize trailing whitespace per line but preserve leading
    indentation.  If any patch fails to match, it is skipped and
    counted in failed_count.

    The caller should check failed_count and fall back to full regen
    if any patches failed.
    """
    lines = source.split('\n')
    applied = 0
    failed = 0

    for search_text, replace_text in patches:
        search_lines = search_text.split('\n')
        while search_lines and search_lines[-1] == '':
            search_lines.pop()
        if not search_lines:
            failed += 1
            continue

        match_index = _find_block(lines, search_lines)
        if match_index < 0:
            failed += 1
            continue

        replace_lines = replace_text.split('\n') if replace_text else []

        start = match_index
        end = match_index + len(search_lines)

        lines = lines[:start] + replace_lines + lines[end:]
        applied += 1

    patched = '\n'.join(lines)
    if not patched.endswith('\n'):
        patched += '\n'
    return patched, applied, failed


def _find_block(lines, search_lines):
    """Find the index of a search block in lines.

    Uses whitespace-tolerant matching: trailing whitespace is ignored,
    but leading indentation is preserved.  Returns the line index of
    the first match, or -1 if not found.
    """
    normalized_search = [_normalize_line(line) for line in search_lines]
    if not normalized_search:
        return -1

    normalized_lines = [_normalize_line(line) for line in lines]

    for start in range(len(normalized_lines) - len(normalized_search) + 1):
        if normalized_lines[start:start + len(normalized_search)] == \
                normalized_search:
            return start
    return -1


def _normalize_line(line):
    """Normalize a line for whitespace-tolerant matching.

    Strips trailing whitespace but preserves leading indentation.
    """
    return line.rstrip()


def _strip_block_edges(text):
    """Remove leading/trailing newlines from a block's content."""
    stripped = text.strip('\n')
    if stripped.startswith('```'):
        first_nl = stripped.find('\n')
        if first_nl >= 0:
            stripped = stripped[first_nl + 1:]
    if stripped.endswith('```'):
        last_fence = stripped.rfind('```')
        if last_fence >= 0:
            stripped = stripped[:last_fence]
    return stripped.rstrip('\n')
