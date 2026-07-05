# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
import hashlib
import json
import os
import re
import time

from sugar3.activity import bundlebuilder

from jarabe.model.aodlicenses import get_license
from jarabe.model.aodtemplates import render_activity_source


@dataclass
class GenerationResult:
    spec: object
    plan: dict
    project_path: str
    bundle_path: str
    bundle_id: str
    files: dict
    provider: str = 'local'
    model: str = ''


def restore_generation_result(spec, summary):
    """Restore a completed result from its persisted artifact paths."""
    if not isinstance(summary, dict):
        return None

    project_path = summary.get('project_path', '')
    bundle_path = summary.get('bundle_path', '')
    if not os.path.isdir(project_path):
        return None
    if bundle_path and not os.path.isfile(bundle_path):
        bundle_path = ''

    plan_path = os.path.join(project_path, 'aod_plan.json')
    try:
        with open(plan_path, encoding='utf-8') as plan_file:
            plan = json.load(plan_file)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(plan, dict):
        return None

    bundle_id = summary.get('bundle_id') or plan.get('bundle_id', '')
    if not bundle_id:
        return None

    try:
        files = read_project_files(project_path)
    except OSError:
        return None

    return GenerationResult(
        spec=spec.normalized(),
        plan=plan,
        project_path=project_path,
        bundle_path=bundle_path,
        bundle_id=bundle_id,
        files=files,
        provider=summary.get('provider', plan.get('provider', 'local')),
        model=summary.get('model', plan.get('model', '')),
    )


def create_prototype_activity(spec, output_root, plan=None,
                              package_bundle=True, activity_source=None):
    """Generate a complete Sugar activity project and optional XO bundle."""
    errors = spec.validate()
    if errors:
        raise ValueError('\n'.join(errors))

    spec = spec.normalized()
    generation_plan = plan or build_plan(spec)
    generation_plan = enrich_plan(spec, generation_plan)
    project_path = assemble_project(
        spec,
        generation_plan,
        output_root,
        activity_source=activity_source,
    )

    bundle_path = ''
    if package_bundle:
        bundle_path = package_project(project_path)

    files = read_project_files(project_path)
    return GenerationResult(
        spec=spec,
        plan=generation_plan,
        project_path=project_path,
        bundle_path=bundle_path,
        bundle_id=generation_plan['bundle_id'],
        files=files,
    )


def infer_template(spec):
    if spec.template != 'auto':
        return spec.template

    prompt = spec.prompt.lower()
    words = set(re.findall(r'[a-z0-9]+', spec.prompt.lower()))
    scores = {
        'canvas': _keyword_score(words, {
            'art', 'canvas', 'comic', 'color', 'design', 'diagram', 'draw',
            'drawing', 'map', 'paint', 'picture', 'poster', 'shape', 'sketch',
            'atlas', 'city', 'compass', 'continent', 'country', 'discover',
            'earth', 'explore', 'explorer', 'geography', 'globe', 'landmark',
            'location', 'maps', 'navigate', 'navigation', 'ocean', 'osm',
            'openstreetmap', 'place', 'places', 'region', 'route', 'street',
            'streetmap', 'territory', 'travel', 'visualize', 'world',
        }) + _phrase_score(prompt, (
            'drawing canvas', 'paint a picture', 'open street map',
            'street map', 'world map', 'map of', 'mind map',
            'city map', 'explore the world', 'explore countries',
            'explore the map', 'geography activity', 'visualize',
        )),
        'narrative': _keyword_score(words, {
            'book', 'diary', 'journal', 'letter', 'narrative', 'poem',
            'reading', 'reflection', 'script', 'story', 'write', 'writing',
        }),
        'quiz': _keyword_score(words, {
            'answer', 'assessment', 'flashcard', 'practice', 'question',
            'quiz', 'spelling', 'test', 'trivia', 'vocabulary',
        }),
        'grid': _keyword_score(words, {
            'board', 'classify', 'game', 'grid', 'logic', 'match', 'maze',
            'pattern', 'puzzle', 'sort', 'table', 'tile',
        }) + _phrase_score(prompt, ('board game', 'pattern game')),
        'utility': _keyword_score(words, {
            'calculate', 'calculator', 'checklist', 'converter', 'counter',
            'list', 'measure', 'organize', 'planner', 'schedule', 'stopwatch',
            'tally', 'timer', 'tool', 'tracker', 'utility',
        }) + _phrase_score(prompt, ('word count', 'word counting')),
    }
    scores['carrom'] = _carrom_template_score(prompt, words)
    scores['chess'] = _chess_template_score(prompt, words)

    template_order = _category_template_order(spec.category)
    ranked = sorted(
        scores.items(),
        key=lambda item: (
            item[1],
            -template_order.index(item[0])
            if item[0] in template_order else -len(template_order),
        ),
        reverse=True,
    )
    template, score = ranked[0]
    if score:
        return template

    defaults = {
        'logic_math': 'quiz',
        'science': 'utility',
        'language': 'narrative',
        'tools_utils': 'utility',
        'games': 'grid',
        'creation': 'narrative',
    }
    return defaults.get(spec.category, 'narrative')


def build_plan(spec):
    template = infer_template(spec)
    subject = _subject_from_spec(spec)
    learner_goal = spec.learner_goal or (
        'Create, test, explain, and improve an idea about %s.'
        % spec.name.lower()
    )
    digest = hashlib.sha256(
        ('%s\0%s' % (spec.name, spec.prompt)).encode('utf-8')
    ).hexdigest()[:10]
    class_stem = _identifier(spec.name)
    bundle_id = 'org.sugarlabs.aod.%s%s' % (class_stem, digest)

    plan = {
        'name': spec.name,
        'summary': _summary_from_prompt(spec.prompt),
        'template': template,
        'category': spec.category,
        'age_band': spec.age_band,
        'learner_goal': learner_goal,
        'learner_steps': [
            'Make a first version.',
            'Test it and explain what happened.',
            'Change one part and share the new version.',
        ],
        'word_bank': _word_bank(spec.prompt),
        'bundle_id': bundle_id,
        'class_name': 'GeneratedActivity',
        'license': spec.license_id,
        'activity_version': int(time.time()),
    }

    if template == 'quiz':
        plan['questions'] = _quiz_questions(spec)
    elif template == 'chess':
        plan['summary'] = (
            'A two-student chess board for practicing legal moves, turn '
            'taking, move explanations, captures, and Journal saving.'
        )
        plan['learner_goal'] = (
            'Practice chess moves, turns, and explanation with a partner.'
        )
        plan['learner_steps'] = [
            'Choose a white piece and make a legal move.',
            'Let black answer with a legal move.',
            'Explain the move idea before the next turn.',
            'Reset or save the board when the game is done.',
        ]
        plan['word_bank'] = [
            'king', 'queen', 'rook', 'bishop', 'knight', 'pawn',
            'capture', 'check',
        ]
    elif template == 'carrom':
        plan['summary'] = (
            'A two-student carrom board for taking turns, aiming the '
            'striker, scoring pocketed coins, tracking fouls, and saving '
            'the match.'
        )
        plan['learner_goal'] = (
            'Practice turn taking, aim planning, scoring, and strategy '
            'explanation with a partner.'
        )
        plan['learner_steps'] = [
            'Student A chooses an aim point and explains the shot.',
            'Record pocketed coins, queen claims, or fouls.',
            'Switch turns so Student B plans the next shot.',
            'Compare scores and reset or save the match in the Journal.',
        ]
        plan['word_bank'] = [
            'striker', 'coin', 'queen', 'pocket', 'rebound', 'foul',
            'turn', 'score',
        ]
    elif template == 'canvas':
        plan['summary'] = (
            'A drawing canvas for learners to sketch, label, revise, and '
            'share ideas about %s.' % subject
        )
        plan['learner_goal'] = (
            'Create and explain a visual model or artifact about %s.'
            % subject
        )
        plan['learner_steps'] = [
            'Sketch the first idea on the canvas.',
            'Point to one part and explain what it means.',
            'Revise the drawing after a partner question.',
            'Save the final visual artifact to the Journal.',
        ]
    elif template == 'grid':
        plan['summary'] = (
            'An interactive grid for sorting, matching, or building patterns '
            'about %s.' % subject
        )
        plan['learner_goal'] = (
            'Use a grid pattern or classification to explain %s.' % subject
        )
        plan['learner_steps'] = [
            'Choose tiles that belong in the first pattern.',
            'Describe the rule or reason for each choice.',
            'Ask a partner to change one tile and explain why.',
            'Save the final grid to the Journal.',
        ]
    elif template == 'narrative':
        plan['starter_text'] = (
            '%s\n\nStart creating here.\n' % spec.prompt.strip()
        )
    elif template == 'utility':
        plan['utility_mode'] = _utility_mode(spec.prompt)
        plan['summary'] = _utility_summary(subject, plan['utility_mode'])
        plan['learner_goal'] = _utility_goal(subject, plan['utility_mode'])
        plan['learner_steps'] = _utility_steps(plan['utility_mode'])
    return plan


def enrich_plan(spec, plan, references=None):
    """Add local classroom design detail before rendering the project."""
    enriched = normalize_plan(spec, plan)
    references = references or ()
    template = enriched['template']
    subject = _subject_from_spec(spec)

    defaults = {
        'canvas': {
            'features': [
                'large drawing surface',
                'drag-to-draw interaction',
                'clear/reset action',
                'Journal-saved learner artifact',
            ],
            'classroom_flow': [
                'Sketch a first idea on the canvas.',
                'Explain what the drawing shows to a partner.',
                'Revise one part after feedback.',
                'Save the final artifact to the Journal.',
            ],
        },
        'chess': {
            'features': [
                'full 8x8 board',
                'white and black turn taking',
                'legal move feedback',
                'captures and move log',
                'Journal-saved board state',
            ],
            'classroom_flow': [
                'White chooses a legal first move.',
                'Black answers and explains the idea.',
                'Partners record one reason for each move.',
                'Reset, replay, or save the board when finished.',
            ],
        },
        'carrom': {
            'features': [
                'full carrom board with four pockets',
                'two-student turn taking',
                'striker aim marker',
                'coin, queen, and foul scoring',
                'Journal-saved match state',
            ],
            'classroom_flow': [
                'Student A picks an aim point and names the shot idea.',
                'Record the pocketed coin, queen, or foul outcome.',
                'Student B takes the next turn and explains the strategy.',
                'Review the shot log, then reset or save the match.',
            ],
        },
        'grid': {
            'features': [
                'toggleable pattern grid',
                'visible selected-square count',
                'quick reset by untoggling choices',
                'Journal-saved pattern state',
            ],
            'classroom_flow': [
                'Create a pattern on the grid.',
                'Describe the rule that creates the pattern.',
                'Ask a partner to extend or change the rule.',
                'Save the final pattern to the Journal.',
            ],
        },
        'narrative': {
            'features': [
                'large writing space',
                'starter prompt',
                'revision-friendly text',
                'Journal-saved writing draft',
            ],
            'classroom_flow': [
                'Read the starter prompt.',
                'Write a first response.',
                'Share one sentence with a partner.',
                'Revise and save the draft to the Journal.',
            ],
        },
        'quiz': {
            'features': [
                'short learner-friendly questions',
                'typed responses',
                'immediate feedback',
                'score tracking',
            ],
            'classroom_flow': [
                'Answer the first question in your own words.',
                'Use feedback to improve the next answer.',
                'Explain one strategy to a partner.',
                'Try again and compare the new score.',
            ],
        },
        'utility': {
            'features': [
                'focused input area',
                'immediate calculated result',
                'simple reusable workflow',
                'Journal-saved tool state',
            ],
            'classroom_flow': [
                'Enter or paste the material to explore.',
                'Read the result and check if it makes sense.',
                'Change one input and compare the result.',
                'Save the useful result to the Journal.',
            ],
        },
    }

    template_defaults = defaults[template]
    enriched['features'] = _unique_strings(
        enriched.get('features') or template_defaults['features'],
        8,
    )
    enriched['classroom_flow'] = _unique_strings(
        enriched.get('classroom_flow') or template_defaults['classroom_flow'],
        6,
    )
    enriched['teacher_notes'] = _unique_strings(
        enriched.get('teacher_notes') or [
            'Pair learners so one student controls and the other explains.',
            'Ask for one prediction before each action.',
            'Use the Journal entry as evidence of learning.',
        ],
        6,
    )
    enriched['assessment_prompts'] = _unique_strings(
        enriched.get('assessment_prompts') or [
            'What did you try first?',
            'What changed after feedback?',
            'What would you improve next?',
        ],
        6,
    )
    enriched['materials'] = _unique_strings(
        enriched.get('materials') or [
            'One XO or shared computer',
            'Partner discussion',
            'Journal for saved work',
        ],
        6,
    )
    if references:
        enriched['grounding_references'] = _unique_strings(
            [
                getattr(reference, 'title', '')
                for reference in references
                if getattr(reference, 'title', '')
            ],
            4,
        )
    elif 'grounding_references' not in enriched:
        enriched['grounding_references'] = []

    if template == 'quiz':
        enriched['questions'] = _enriched_quiz_questions(spec, enriched)
    elif template == 'chess':
        enriched['chess_show_move_log'] = _chess_should_show_move_log(
            spec,
            enriched,
        )
        if not enriched['chess_show_move_log']:
            enriched['features'] = _unique_strings([
                'clean chess board without move-history panel',
                'white and black turn taking',
                'legal move feedback',
                'Journal-saved board position',
            ] + enriched.get('features', []), 8)
            enriched['summary'] = (
                'A clean, two-player chess board for partners to play, '
                'discuss moves, and reason together without move history '
                'clutter.'
            )
    elif template == 'carrom':
        enriched['players'] = _unique_strings(
            enriched.get('players') or ['Student A', 'Student B'],
            2,
        )
    elif template == 'narrative' and not enriched.get('starter_text'):
        enriched['starter_text'] = (
            '%s\n\nI notice...\nI wonder...\nMy next revision is...\n'
            % spec.prompt.strip()
        )
    elif template == 'utility':
        enriched['utility_mode'] = _utility_mode_from_plan(spec, enriched)

    if not enriched.get('summary') or enriched['summary'] == spec.prompt:
        enriched['summary'] = (
            'A Sugar activity about %s with hands-on work, reflection, '
            'and Journal saving.' % subject
        )

    return enriched


def normalize_plan(spec, plan):
    normalized = build_plan(spec)
    if not isinstance(plan, dict):
        return normalized

    text_fields = (
        'activity_kind',
        'interaction_model',
        'summary',
        'learner_goal',
        'starter_text',
        'state_schema',
    )
    for field in text_fields:
        value = plan.get(field)
        if isinstance(value, str) and value.strip():
            normalized[field] = value.strip()

    template = plan.get('template')
    if template in (
            'canvas', 'carrom', 'chess', 'grid', 'narrative', 'quiz',
            'utility'):
        normalized['template'] = template

    steps = plan.get('learner_steps')
    if isinstance(steps, list):
        clean_steps = [
            str(step).strip() for step in steps
            if isinstance(step, str) and step.strip()
        ][:5]
        if clean_steps:
            normalized['learner_steps'] = clean_steps

    words = plan.get('word_bank')
    if isinstance(words, list):
        normalized['word_bank'] = _unique_strings(words, 8)

    for field, limit in (
            ('ui_regions', 8),
            ('features', 8),
            ('classroom_flow', 6),
            ('teacher_notes', 6),
            ('assessment_prompts', 6),
            ('materials', 6),
            ('grounding_references', 4)):
        values = plan.get(field)
        if isinstance(values, list):
            clean_values = _unique_strings(values, limit)
            if clean_values:
                normalized[field] = clean_values

    questions = plan.get('questions')
    if isinstance(questions, list):
        clean_questions = []
        for item in questions[:10]:
            if not isinstance(item, dict):
                continue
            question = item.get('question', '')
            answer = item.get('answer', '')
            if isinstance(question, str) and question.strip():
                clean_questions.append({
                    'question': question.strip()[:240],
                    'answer': str(answer).strip()[:120] or 'anything',
                })
        if clean_questions:
            normalized['questions'] = clean_questions

    for field in (
            'provider',
            'model',
            'provider_fallback_reason',
            'code_source',
            'codegen_provider',
            'codegen_model',
            'codegen_fallback_reason',
            'refine_method',
            'original_prompt',
            'enhanced_prompt'):
        value = plan.get(field)
        if isinstance(value, str) and value:
            normalized[field] = value

    if plan.get('bundle_id'):
        normalized['bundle_id'] = plan['bundle_id']

    attempts = plan.get('codegen_attempts')
    if isinstance(attempts, int):
        normalized['codegen_attempts'] = attempts

    for field in ('chess_show_move_log',):
        value = plan.get(field)
        if isinstance(value, bool):
            normalized[field] = value

    utility_mode = plan.get('utility_mode')
    if utility_mode in ('word_counter', 'counter', 'timer'):
        normalized['utility_mode'] = utility_mode

    return normalized


def assemble_project(spec, plan, output_root, activity_source=None):
    os.makedirs(output_root, exist_ok=True)
    project_path = _new_project_path(output_root, spec.name)
    activity_path = os.path.join(project_path, 'activity')
    os.makedirs(activity_path)

    license_info = get_license(spec.license_id)
    source = activity_source or render_activity_source(spec, plan)
    files = {
        'activity.py': source,
        'setup.py': _SETUP_SOURCE,
        'README.md': _render_readme(spec, plan),
        'LICENSE': license_info.get_text(),
        'aod_plan.json': json.dumps(plan, indent=2, sort_keys=True) + '\n',
        os.path.join('activity', 'activity.info'):
            _render_activity_info(spec, plan),
        os.path.join('activity', 'activity.svg'): _ACTIVITY_ICON,
    }

    for relative_path, content in files.items():
        path = os.path.join(project_path, relative_path)
        with open(path, 'w', encoding='utf-8') as output:
            output.write(content)

    return project_path


def package_project(project_path):
    dist_path = os.path.join(project_path, 'dist')
    os.makedirs(dist_path, exist_ok=True)
    config = bundlebuilder.Config(
        source_dir=project_path,
        dist_dir=dist_path,
    )
    bundlebuilder.cmd_dist_xo(config, None)
    return os.path.join(dist_path, config.xo_name)


def read_project_files(project_path):
    result = {}
    for root, directories, filenames in os.walk(project_path):
        directories[:] = [
            name for name in directories if name not in ('dist', '__pycache__')
        ]
        for filename in filenames:
            path = os.path.join(root, filename)
            relative_path = os.path.relpath(path, project_path)
            try:
                with open(path, encoding='utf-8') as source:
                    result[relative_path] = source.read()
            except UnicodeDecodeError:
                continue
    return result


_SPDX_RE = re.compile(r'^(\s*#\s*SPDX-License-Identifier:).*$', re.MULTILINE)


def _replace_spdx_identifier(source, license_id):
    """Rewrite the first SPDX header line to the given license id."""
    def substitute(match):
        return '%s %s' % (match.group(1), license_id)

    updated, count = _SPDX_RE.subn(substitute, source, count=1)
    return updated if count else source


def apply_license_to_project(project_path, spec, plan):
    """Rewrite the on-disk license artifacts to match ``spec.license_id``.

    Generation bakes a default license into the project. When the learner
    chooses a license at install or export time we regenerate the LICENSE
    file, the ``activity.info`` license field, and the ``activity.py`` SPDX
    header so the packaged bundle carries the selected license. Returns the
    refreshed project file mapping.
    """
    license_info = get_license(spec.license_id)

    license_path = os.path.join(project_path, 'LICENSE')
    with open(license_path, 'w', encoding='utf-8') as license_file:
        license_file.write(license_info.get_text())

    info_path = os.path.join(project_path, 'activity', 'activity.info')
    with open(info_path, 'w', encoding='utf-8') as info_file:
        info_file.write(_render_activity_info(spec, plan))

    source_path = os.path.join(project_path, 'activity.py')
    try:
        with open(source_path, encoding='utf-8') as source_file:
            source = source_file.read()
    except OSError:
        source = ''
    if source:
        updated = _replace_spdx_identifier(source, spec.license_id)
        if updated != source:
            with open(source_path, 'w', encoding='utf-8') as source_file:
                source_file.write(updated)

    return read_project_files(project_path)


def _render_activity_info(spec, plan):
    return (
        '[Activity]\n'
        'name = %(name)s\n'
        'bundle_id = %(bundle_id)s\n'
        'icon = activity\n'
        'exec = sugar-activity3 activity.GeneratedActivity\n'
        'activity_version = %(activity_version)s\n'
        'license = %(license)s\n'
        'max_participants = 1\n'
        'summary = %(summary)s\n'
        'tags = Education\n'
    ) % {
        'name': spec.name.replace('\n', ' '),
        'bundle_id': plan['bundle_id'],
        'license': spec.license_id,
        'summary': plan['summary'].replace('\n', ' '),
        'activity_version': plan['activity_version'],
    }


def _render_readme(spec, plan):
    steps = '\n'.join(
        '%d. %s' % (index, step)
        for index, step in enumerate(plan['learner_steps'], 1)
    )
    extra_sections = ''.join((
        _render_plan_section('Key features', plan.get('features')),
        _render_plan_section('Classroom flow', plan.get('classroom_flow')),
        _render_plan_section('Teacher notes', plan.get('teacher_notes')),
        _render_plan_section(
            'Assessment prompts',
            plan.get('assessment_prompts'),
        ),
        _render_plan_section('Materials', plan.get('materials')),
        _render_plan_section(
            'Grounded Sugar patterns',
            plan.get('grounding_references'),
        ),
    ))
    return (
        '# %(name)s\n\n'
        '%(summary)s\n\n'
        '## Learner goal\n\n'
        '%(goal)s\n\n'
        '## Suggested learning flow\n\n'
        '%(steps)s\n\n'
        '%(extra_sections)s'
        '## Generation details\n\n'
        '- Category: `%(category)s`\n'
        '- Template: `%(template)s`\n'
        '- Age band: `%(age_band)s`\n'
        '- License: `%(license)s`\n\n'
        'This project was generated by Sugar Activity on Demand and can be '
        'changed, tested, and shared as an XO bundle.\n'
    ) % {
        'name': spec.name,
        'summary': plan['summary'],
        'goal': plan['learner_goal'],
        'steps': steps,
        'extra_sections': extra_sections,
        'category': spec.category,
        'template': plan['template'],
        'age_band': spec.age_band,
        'license': spec.license_id,
    }


def _render_plan_section(title, values):
    if not values:
        return ''
    lines = [
        '- %s' % str(value).strip()
        for value in values
        if str(value).strip()
    ]
    if not lines:
        return ''
    return '## %s\n\n%s\n\n' % (title, '\n'.join(lines))


def _summary_from_prompt(prompt):
    summary = ' '.join(prompt.split())
    if len(summary) > 180:
        summary = summary[:177].rstrip() + '...'
    return summary


def _word_bank(prompt):
    words = re.findall(r'[A-Za-z][A-Za-z0-9-]+', prompt.lower())
    ignored = {
        'activity', 'and', 'build', 'create', 'for', 'make', 'that', 'the',
        'their', 'this', 'where', 'with',
    }
    return _unique_strings(
        [word for word in words if word not in ignored and len(word) > 2],
        8,
    )


def _keyword_score(words, keywords):
    return len(words.intersection(keywords))


def _phrase_score(prompt, phrases):
    return sum(1 for phrase in phrases if phrase in prompt)


def _category_template_order(category):
    orders = {
        'logic_math': [
            'quiz', 'grid', 'carrom', 'utility', 'canvas', 'narrative',
            'chess',
        ],
        'science': [
            'utility', 'canvas', 'grid', 'quiz', 'narrative', 'carrom',
            'chess',
        ],
        'language': [
            'narrative', 'quiz', 'canvas', 'grid', 'utility', 'carrom',
            'chess',
        ],
        'tools_utils': [
            'utility', 'grid', 'quiz', 'carrom', 'canvas', 'narrative',
            'chess',
        ],
        'games': [
            'carrom', 'chess', 'grid', 'quiz', 'canvas', 'narrative',
            'utility',
        ],
        'creation': [
            'canvas', 'narrative', 'grid', 'carrom', 'quiz', 'utility',
            'chess',
        ],
    }
    return orders.get(category, orders['logic_math'])


def _carrom_template_score(prompt, words):
    if 'carrom' in words:
        return 6
    if any(phrase in prompt for phrase in (
            'carrom board', 'carrom game', 'carrom activity')):
        return 6

    carrom_words = {
        'striker', 'pocket', 'pockets', 'coin', 'coins', 'queen',
        'rebound', 'flick', 'flicking', 'foul', 'fouls',
    }
    score = len(words.intersection(carrom_words))
    if score and {'board', 'game', 'score', 'scoring', 'turn', 'turns'} & words:
        return 2 + score
    return 0


def _chess_template_score(prompt, words):
    if 'chess' in words or 'checkmate' in words:
        return 5
    if any(phrase in prompt for phrase in (
            'chess board', 'chess game', 'chess puzzle', 'legal chess')):
        return 5

    pieces = {
        'king', 'queen', 'rook', 'bishop', 'knight', 'pawn',
    }
    piece_count = len(words.intersection(pieces))
    chess_actions = {
        'capture', 'castle', 'castling', 'check', 'move', 'moves',
        'opening',
    }
    if piece_count >= 2 and words.intersection(chess_actions):
        return 3 + piece_count
    return 0


def _utility_mode(prompt):
    words = set(re.findall(r'[a-z0-9]+', prompt.lower()))
    text = prompt.lower()
    if 'word count' in text or 'word counting' in text or \
            ({'word', 'words'} & words and {'count', 'counting'} & words):
        return 'word_counter'
    if {'timer', 'stopwatch'} & words or 'time tracker' in text:
        return 'timer'
    if {'counter', 'count', 'tally', 'scorekeeper'} & words:
        return 'counter'
    return 'word_counter'


def _utility_mode_from_plan(spec, plan):
    mode = plan.get('utility_mode')
    if mode in ('word_counter', 'counter', 'timer'):
        return mode
    return _utility_mode(spec.prompt)


def _utility_summary(subject, mode):
    if mode == 'timer':
        return (
            'A classroom timer for pacing, comparing, and reflecting on %s.'
            % subject
        )
    if mode == 'counter':
        return (
            'A simple counter for tallying observations and decisions about '
            '%s.' % subject
        )
    return (
        'A text tool that counts words and characters while learners inspect '
        '%s.' % subject
    )


def _utility_goal(subject, mode):
    if mode == 'timer':
        return 'Use elapsed time as evidence while working on %s.' % subject
    if mode == 'counter':
        return 'Track and explain counts or scores connected to %s.' % subject
    return 'Measure and revise text connected to %s.' % subject


def _utility_steps(mode):
    if mode == 'timer':
        return [
            'Start the timer before the activity round.',
            'Pause when the round ends.',
            'Compare elapsed time with the class goal.',
            'Reset or save the timing note in the Journal.',
        ]
    if mode == 'counter':
        return [
            'Press plus when an event or idea appears.',
            'Press minus to correct a tally.',
            'Explain what the count means.',
            'Reset or save the tally in the Journal.',
        ]
    return [
        'Enter or paste the text to inspect.',
        'Read the word and character counts.',
        'Revise the text and compare the new count.',
        'Save the useful version to the Journal.',
    ]


def _unique_strings(values, limit):
    result = []
    seen = set()
    for value in values:
        text = str(value).strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) == limit:
            break
    return result


def _quiz_questions(spec):
    subject = spec.name.lower()
    return [
        {
            'question': 'What is the main idea in %s?' % subject,
            'answer': 'anything',
        },
        {
            'question': 'Explain one example in your own words.',
            'answer': 'anything',
        },
        {
            'question': 'What would you test or change next?',
            'answer': 'anything',
        },
    ]


def _enriched_quiz_questions(spec, plan):
    questions = plan.get('questions') or []
    if len(questions) >= 4:
        return questions[:6]

    subject = _subject_from_spec(spec)
    words = plan.get('word_bank') or []
    focus = words[0] if words else subject
    generated = questions[:]
    generated.extend([
        {
            'question': 'What is one important idea about %s?' % subject,
            'answer': 'anything',
        },
        {
            'question': 'Give an example that uses %s.' % focus,
            'answer': 'anything',
        },
        {
            'question': 'How would you explain %s to a partner?' % subject,
            'answer': 'anything',
        },
        {
            'question': 'What would you change or test next?',
            'answer': 'anything',
        },
    ])

    cleaned = []
    seen = set()
    for item in generated:
        question = item.get('question', '').strip()
        if not question or question.lower() in seen:
            continue
        seen.add(question.lower())
        cleaned.append({
            'question': question,
            'answer': str(item.get('answer', 'anything')).strip() or
            'anything',
        })
        if len(cleaned) == 6:
            break
    return cleaned


def _chess_should_show_move_log(spec, plan):
    if isinstance(plan.get('chess_show_move_log'), bool):
        return plan['chess_show_move_log']

    prompt = spec.prompt.lower()
    remove_words = (
        'remove', 'hide', 'without', 'no ', 'don\'t', 'do not', 'disable',
        'clean',
    )
    tracking_words = (
        'move log', 'move history', 'history', 'tracking', 'track moves',
        'move tracking', 'move list', 'log panel',
    )
    if any(word in prompt for word in remove_words) and \
            any(word in prompt for word in tracking_words):
        return False
    return True


def _subject_from_spec(spec):
    words = _word_bank(spec.prompt)
    if words:
        return ' '.join(words[:3])
    return spec.name.lower()


def _identifier(name):
    words = re.findall(r'[A-Za-z0-9]+', name)
    identifier = ''.join(word.capitalize() for word in words)
    if not identifier:
        identifier = 'Generated'
    if identifier[0].isdigit():
        identifier = 'Activity' + identifier
    return identifier[:45]


def _new_project_path(output_root, name):
    base = _identifier(name) + '.activity'
    candidate = os.path.join(output_root, base)
    suffix = 2
    while os.path.exists(candidate):
        candidate = os.path.join(
            output_root,
            '%s%d.activity' % (_identifier(name), suffix),
        )
        suffix += 1
    os.makedirs(candidate)
    return candidate


_SETUP_SOURCE = """#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later

from sugar3.activity import bundlebuilder


if __name__ == '__main__':
    bundlebuilder.start()
"""

_ACTIVITY_ICON = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="55" height="55" viewBox="0 0 55 55">
  <circle cx="27.5" cy="27.5" r="21"
          fill="#ffffff" stroke="#000000" stroke-width="3.5"/>
  <path d="M17 29 L24 36 L39 19"
        fill="none" stroke="#000000" stroke-width="4"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""
