# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json

from jarabe.model.aodprompts import extract_json_object
from jarabe.model.aodrag import get_api_reference
from jarabe.model.aodvalidator import ALLOWED_IMPORT_ROOTS
from jarabe.model.aodvalidator import FORBIDDEN_CALLS
from jarabe.model.aodvalidator import FORBIDDEN_IMPORT_ROOTS
from jarabe.model.aodvalidator import _module_available


_CODE_SIZE_INSTRUCTIONS = {
    'compact': (
        'Length: Write a focused, complete activity in roughly 300–500 lines. '
        'Implement the core interaction fully but skip decorative extras. '
        'Every line must be functional — no placeholders or stubs.'
    ),
    'standard': (
        'Length: Write all necessary code to fully realize the request. '
        'For complex activities (board games, simulators) this typically '
        'requires 800–1200 lines. Prioritize completeness over brevity; '
        'do not abbreviate or stop early.'
    ),
    'full': (
        'Length: Write the most complete, polished version possible with no '
        'token limit. Include rich toolbar actions, keyboard shortcuts, '
        'multiple screens/modes, full Journal persistence, edge-case '
        'handling, and detailed visual polish. 1500+ lines is expected for '
        'anything non-trivial. Do not stop until the activity is production-ready.'
    ),
}


def _rendering_guidance():
    """Backend guidance for the system prompt, matched to this system.

    pygame/sugargame are only offered when the runtime actually has
    them; otherwise the model is steered to cairo so generated code can
    always preview and launch on this machine.
    """
    if _module_available('pygame') and _module_available('sugargame'):
        return (
            '## Rendering approach — cairo vs pygame/sugargame\n'
            'Choose the right rendering backend for the request:\n'
            '- **GTK3 + cairo (default)**: Use for most activities — '
            'board games, drawing apps, quizzes, writing tools, '
            'simulations. Gtk.DrawingArea with a cairo draw callback is '
            'idiomatic Sugar and integrates cleanly with GTK events. '
            'Prefer this unless the request is clearly game-loop '
            'driven.\n'
            '- **pygame via sugargame**: Use ONLY when the request '
            'explicitly asks for a pygame game or when the activity '
            'needs a continuous game loop (e.g. real-time arcade, '
            'physics simulation, animation-heavy game). When using '
            'pygame, wrap the activity with sugargame.canvas.Canvas and '
            'run pygame.display.set_mode inside the Sugar handle. '
            'Import sugargame.canvas and pygame. Still inherit from '
            'sugar3.activity.activity.Activity. Still use the Sugar '
            'toolbar and Journal persistence.\n'
            'When in doubt, use cairo + GTK3. Only choose sugargame '
            'when the learner prompt clearly describes gameplay that '
            'needs a frame loop.\n\n'
        )
    return (
        '## Rendering approach — GTK3 + cairo only\n'
        'The pygame/sugargame libraries are NOT installed on this '
        'system, so never import them. Build every activity — '
        'including arcade-style and real-time games — with GTK3 + '
        'cairo: draw in a Gtk.DrawingArea draw callback, drive the '
        'frame loop with GLib.timeout_add (about 33 ms per frame), '
        'and handle controls with GTK key-press-event handlers.\n\n'
    )


def build_codegen_system_prompt(spec, plan, references=(), code_size='standard'):
    """Build the provider prompt for a complete Sugar activity.py file."""
    return (
        'You are Sugar Activity on Demand, a code generator for Sugar '
        'activities.\n\n'
        'Return the complete activity.py source inside a single Python '
        'code fence and nothing else:\n'
        '```python\n<complete Python source for activity.py>\n```\n\n'
        'Do not wrap the source in JSON. Do not add explanation, notes, '
        'or any text before or after the fence. Every output token is '
        'precious, so spend them on the Python code, not on JSON escaping '
        'or commentary.\n\n'
        'The generated source must be a complete Sugar GTK3 activity '
        'that follows the same patterns as real installed Sugar '
        'activities.\n\n'
        'SUGAR ACTIVITY STRUCTURE (follow exactly):\n'
        '1. Start with a copyright header and SPDX line:\n'
        '   # Copyright (C) 2026 Sugar Labs\n'
        '   # SPDX-License-Identifier: GPL-3.0-or-later\n'
        '2. Import gi and require versions BEFORE importing GTK:\n'
        '   import gi\n'
        '   gi.require_version("Gtk", "3.0")\n'
        '   gi.require_version("Gdk", "3.0")\n'
        '3. Use gettext for any user-visible strings:\n'
        '   from gettext import gettext as _\n'
        '4. Set up logging:\n'
        '   import logging\n'
        '   _logger = logging.getLogger("GeneratedActivity")\n'
        '5. Import sugar3 modules FIRST before any Gtk imports:\n'
        '   from sugar3.activity import activity\n'
        '   from sugar3.graphics.toolbarbox import ToolbarBox\n'
        '   from sugar3.activity.widgets import ActivityToolbarButton\n'
        '   from sugar3.activity.widgets import StopButton\n'
        '   Always prefer sugar3 / sugar-toolkit-gtk3 APIs over raw Gtk '
        'equivalents. Use sugar3.graphics.style for colors, fonts, and icon '
        'sizes. Use sugar3.graphics.toolbutton.ToolButton for toolbar items. '
        'Use sugar3.graphics.alert for in-activity notifications. Fall back '
        'to plain GTK3 only when no Sugar wrapper exists.\n'
        '6. Class must be named GeneratedActivity(activity.Activity)\n'
        '7. In __init__:\n'
        '   - Call activity.Activity.__init__(self, handle)\n'
        '   - Create ToolbarBox with ActivityToolbarButton and StopButton. '
        'Insert every item using '
        'toolbar_box.toolbar.insert(item, position). ToolbarBox does NOT have '
        'an add_toolbar_button() method.\n'
        '   - Call self.set_toolbar_box(toolbar_box)\n'
        '   - Build the canvas with Gtk widgets\n'
        '   - Call self.set_canvas(canvas)\n'
        '   - Call self.show_all()\n'
        '   - For Gtk.Adjustment ranges, call set_lower() and set_upper(); '
        'Gtk.Adjustment does NOT have set_bounds().\n'
        '8. Implement read_file(self, file_path) and '
        'write_file(self, file_path)\n'
        '   for Journal persistence using json.\n\n'
        + _rendering_guidance() +
        'Hard requirements:\n'
        '- Build the specific activity described by activity_kind, '
        'interaction_model, ui_regions, learner_steps, and the learner '
        'prompt. Do not copy a canned local template.\n'
        '- The RAG references below show how real Sugar activities are '
        'assembled. Follow the Sugar lifecycle and GTK patterns from those '
        'references, but create new code for this request.\n'
        '- Treat the plan.template value only as a reference family for '
        'metadata; the generated UI and behavior must follow the learner '
        'request.\n'
        '- The visible activity must include the controls and work area '
        'needed for the learner prompt. If the prompt asks for two learners, '
        'include separate learner/team state and a turn or collaboration '
        'workflow. If it asks for drawing, implement pointer events and '
        'actual drawing state, not a static sample image.\n'
        '- This activity.py is the generated product. Do not return a '
        'preview card, explanation-only mockup, tiny demo, TODO, or '
        'placeholder. A teacher should be able to install it and have '
        'learners use the requested activity immediately.\n'
        '- Make the canvas/work area fill the activity window naturally with '
        'Gtk containers that expand. Avoid small centered toy panels unless '
        'the requested activity is intentionally compact.\n'
        '- Boards, grids, and play areas must scale with the window: '
        'compute cell/tile sizes from the allocated space (a size-allocate '
        'callback or an expanding Gtk.DrawingArea that redraws from its '
        'allocation), never hardcoded small pixel sizes. On a large screen '
        'the play area should use most of the window, centered, with '
        'square cells staying square.\n'
        '- If the structured request includes "Current activity.py excerpt", '
        'this is a refinement. Preserve working behavior from that source '
        'and apply the requested change directly in the regenerated source.\n'
        '- Use only classroom-safe local state. No networking, subprocesses, '
        'or arbitrary filesystem access.\n'
        '- Keep the UI useful on 1024x768 screens.\n'
        '- Make the activity interactive enough for learners to try directly '
        'after installing it from the preview.\n'
        '- Include the prompt-specific domain objects and actions. Examples: '
        'drawing prompts need DrawingArea pointer events and saved strokes; '
        'two-student prompts need visible learner roles and collaboration or '
        'turn-taking state; board games need actual board state, scoring or '
        'move rules; quiz prompts need input, feedback, and saved progress.\n'
        '\n## Quality bar — what "full-fledged" means\n'
        'You are the Sugar equivalent of v0/Lovable: when a learner '
        'describes an idea, you ship a finished activity, not a stub. '
        'Every output must clear ALL of these:\n'
        '- A real, finished UI: titled sections, sensible spacing, '
        'descriptive button labels with tooltips, status hints, and '
        'visible feedback for every action. Not a three-button debug '
        'panel.\n'
        '- Multiple interaction modes / screens when the request implies '
        'them. Use Gtk.Stack with named pages for flows like setup → play '
        '→ result, or question → feedback → review. Use Gtk.Notebook or '
        'a sidebar for tool/option grouping.\n'
        '- Real domain logic. Chess enforces legal moves and detects '
        'check. A quiz tracks score and retains answers. A drawing app '
        'stores stroke geometry and supports brush size + color + undo. '
        '"Looks like the thing" is the floor, not the ceiling.\n'
        '- Polished GTK3: Gtk.Box/Gtk.Grid layouts that expand, '
        'Gtk.Frame for grouping, Pango markup for emphasis '
        '(<b>...</b>, <span foreground="...">...</span>), '
        'Gtk.CssProvider for visual styling when it helps. Use '
        'sugar3.graphics.style for fonts/colors consistent with Sugar.\n'
        '- Proper Journal persistence via JSON: write_file serializes '
        'every piece of meaningful state (positions, scores, drawings, '
        'history). read_file restores it and rebuilds the visible UI.\n'
        '- Rich toolbar: ActivityToolbarButton, Gtk.SeparatorToolItem, '
        'StopButton, plus at least 2–4 custom Gtk.ToolButton actions '
        'relevant to the activity (New/Reset, Undo, Save Snapshot, '
        'Hint, Change Tool/Color, etc.) with icon_name and tooltip_text '
        'set.\n'
        '- Keyboard shortcuts for common actions (Ctrl+N new, Ctrl+Z '
        'undo, etc.) via Gtk.AccelGroup or key-press-event when relevant.\n'
        '- No TODO, no "placeholder", no "Add your code here", no demo '
        'strings. Every label and action is final classroom-ready text.\n'
        '- %(length_instruction)s\n'
        '\n## Examples of richness expected per request type\n'
        '- Drawing: tool palette (pen/eraser), color picker (≥6 colors), '
        'brush-size slider, undo/redo stack, clear-canvas action, save-'
        'as-PNG-to-Journal, stroke geometry persistence. Not just a '
        'DrawingArea with one black pen.\n'
        '- Quiz: question pool of 5+ items, randomized order, typed or '
        'multiple-choice answers, per-question feedback, running score, '
        'final review screen, restart action, Journal-saved progress.\n'
        '- Board game (chess/carrom/etc.): full board widget with '
        'visible coordinates, piece/coin rendering, turn indicator, '
        'move log panel, legal-move enforcement, captured-pieces tray, '
        'reset and save actions.\n'
        '- Writing/narrative: titled text area with starter prompt, '
        'word/character counter live-updating, save-draft + load-draft '
        'actions, a reflection prompt sidebar, optional formatting '
        'buttons.\n'
        '- Two-learner / partner: explicit Student A / Student B '
        'labels, visible "active turn" indicator, switch-turn button, '
        'per-learner score or contribution tally, swap-roles action.\n\n'
        'Allowed import roots: %(allowed)s\n'
        'Forbidden import roots: %(forbidden_imports)s\n'
        'Forbidden calls: %(forbidden_calls)s\n\n'
        'Sugar Activity API reference:\n%(api_reference)s\n\n'
        'Retrieved Sugar references:\n%(references)s'
    ) % {
        'allowed': ', '.join(sorted(ALLOWED_IMPORT_ROOTS)),
        'forbidden_imports': ', '.join(sorted(FORBIDDEN_IMPORT_ROOTS)),
        'forbidden_calls': ', '.join(sorted(FORBIDDEN_CALLS)),
        'api_reference': get_api_reference(),
        'references': _format_references(references) or
        'No extra references were retrieved.',
        'length_instruction': _CODE_SIZE_INSTRUCTIONS.get(
            code_size, _CODE_SIZE_INSTRUCTIONS['standard']),
    }


def build_codegen_user_prompt(spec, plan, validation_feedback=''):
    """Describe the requested activity source to the provider."""
    feedback_block = ''
    if validation_feedback:
        feedback_block = (
            '\n\nPrevious generated source failed validation. Fix these '
            'issues and return a corrected complete activity.py:\n%s'
            % validation_feedback
        )
    return (
        'Create activity.py for this Sugar activity request.\n\n'
        'Generate the real learner activity now. The output must be complete '
        'runnable GTK3/Sugar code, not a sketch, template note, preview '
        'description, static sample image, or generic local template. '
        'Before returning, self-check that the code implements the concrete '
        'nouns and verbs in the learner prompt.\n\n'
        'Structured request:\n%s\n\n'
        'Normalized plan JSON:\n%s%s'
    ) % (
        spec.to_prompt(),
        json.dumps(plan, indent=2, sort_keys=True),
        feedback_block,
    )


def extract_activity_source(value):
    """Extract Python source from provider JSON or a fenced code string."""
    source = ''
    if isinstance(value, dict):
        files = value.get('files')
        if isinstance(files, dict):
            source = files.get('activity.py') or files.get('activity_py') or ''
            if not source:
                for path, content in files.items():
                    if (isinstance(path, str)
                            and path.endswith('activity.py')
                            and isinstance(content, str)):
                        source = content
                        break
        elif isinstance(files, list):
            for item in files:
                if not isinstance(item, dict):
                    continue
                path = item.get('path') or item.get('name')
                if (isinstance(path, str)
                        and (path in ('activity.py', './activity.py')
                             or path.endswith('/activity.py'))):
                    source = item.get('content') or item.get('source') or ''
                    break
        if not source:
            for key in ('activity_py', 'activity.py', 'source', 'code'):
                candidate = value.get(key)
                if isinstance(candidate, str):
                    source = candidate
                    break
    elif isinstance(value, str):
        source = value
    else:
        raise ValueError('Provider code response must be text or JSON.')

    source = _strip_code_fence(source)
    if not source:
        raise ValueError('Provider code response did not include activity.py.')

    # A truncated JSON wrapper (e.g. {"activity_py": "...<cut off>) looks
    # like Python to a naive reader but is not valid Python.  Detect it
    # here so the caller gets a clear "truncated" message instead of a
    # confusing syntax error from ast.parse on the JSON text.
    stripped = source.lstrip()
    if stripped.startswith('{') or stripped.startswith('['):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            raise ValueError(
                'Model response was truncated: the JSON wrapping the '
                'activity source is incomplete. This usually means the '
                'model ran out of output tokens (finish_reason=length). '
                'Try a smaller prompt or a model with a larger output '
                'budget.'
            )
        if isinstance(parsed, dict):
            return extract_activity_source(parsed)

    if 'GeneratedActivity' not in source:
        raise ValueError(
            'Provider code response did not define GeneratedActivity.'
        )
    return source.rstrip() + '\n'


def extract_activity_source_from_response(text):
    """Extract activity.py from a raw codegen text response.

    Models may return the source inside a ```python fence or as a JSON
    object with an activity_py field.  Truncated JSON responses are
    detected and reported clearly instead of being misread as Python.
    Model error messages (e.g. "ERROR: Cannot read image.png") are
    detected so the caller sees the real provider error instead of a
    confusing "did not define GeneratedActivity" message.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Provider code response did not include activity.py.')

    stripped = text.strip()

    # Detect model-side error messages that are not code.  Some
    # OpenRouter models return errors like "ERROR: Cannot read
    # image.png (this model does not support image input)" instead of
    # activity source.  These short, non-Python messages should be
    # surfaced to the user, not fed to ast.parse.
    if (stripped.startswith('ERROR:')
            or stripped.startswith('Error:')
            or stripped.startswith('ERROR ')):
        raise ValueError(
            'Model returned an error instead of activity code: %s'
            % stripped[:300]
        )

    try:
        value = extract_json_object(text)
    except ValueError:
        value = text
    if isinstance(value, dict):
        try:
            return extract_activity_source(value)
        except ValueError:
            # The "JSON" was an explanation object, or a dict literal
            # inside the code misread as the response wrapper. Fall back
            # to reading the raw text as fenced/plain code.
            return extract_activity_source(text)
    return extract_activity_source(value)


def _strip_code_fence(source):
    source = (source or '').strip()
    if '```' not in source:
        return source

    blocks = _fenced_blocks(source)
    if blocks:
        for block in blocks:
            if 'GeneratedActivity' in block:
                return block
        return max(blocks, key=len)

    # Unterminated fence (usually a truncated stream): keep everything
    # after the opening fence line so the caller can report a clear
    # truncation/syntax problem instead of "no activity.py".
    fence_start = source.find('```')
    first_newline = source.find('\n', fence_start)
    if first_newline >= 0:
        return source[first_newline + 1:].strip()
    return ''


def _fenced_blocks(source):
    """Return the contents of all complete ``` fenced blocks."""
    blocks = []
    index = 0
    while True:
        start = source.find('```', index)
        if start < 0:
            break
        first_newline = source.find('\n', start)
        if first_newline < 0:
            break
        end = source.find('```', first_newline + 1)
        if end < 0:
            break
        block = source[first_newline + 1:end].strip()
        if block:
            blocks.append(block)
        index = end + 3
    return blocks


def _format_references(references):
    blocks = []
    for index, document in enumerate(references[:1], 1):
        text = ' '.join(getattr(document, 'text', '').split())
        title = getattr(document, 'title', 'Reference')
        blocks.append(
            'Reference %d - %s:\n%s' % (index, title, text[:4000])
        )
    return '\n\n'.join(blocks)
