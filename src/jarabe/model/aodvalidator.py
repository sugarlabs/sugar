# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import ast
import configparser
from dataclasses import dataclass
from dataclasses import field
import os
import re
import zipfile

from sugar3.bundle.helpers import bundle_from_archive
from sugar3.bundle.helpers import bundle_from_dir

from jarabe.model.aodspec import LICENSE_IDS


ALLOWED_IMPORT_ROOTS = {
    'cairo',
    'datetime',
    'gettext',
    'gi',
    'json',
    'logging',
    'math',
    'pygame',
    'random',
    'sugar3',
    'sugargame',
}

FORBIDDEN_IMPORT_ROOTS = {
    'ctypes',
    'http',
    'multiprocessing',
    'os',
    'pathlib',
    'requests',
    'shutil',
    'socket',
    'subprocess',
    'urllib',
}

FORBIDDEN_CALLS = {
    '__import__',
    'compile',
    'eval',
    'exec',
    'globals',
    'locals',
}


@dataclass
class ValidationReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def valid(self):
        return not self.errors

    def extend(self, report):
        self.errors.extend(report.errors)
        self.warnings.extend(report.warnings)


def validate_source(source):
    report = ValidationReport()
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        report.errors.append(
            'Python syntax error on line %s: %s'
            % (error.lineno, error.msg)
        )
        return report

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split('.')[0])

    for name in sorted(imports):
        if name in FORBIDDEN_IMPORT_ROOTS:
            report.errors.append('Forbidden import: %s' % name)
        elif name not in ALLOWED_IMPORT_ROOTS:
            report.errors.append('Import is not allowlisted: %s' % name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in FORBIDDEN_CALLS:
                report.errors.append('Forbidden call: %s' % call_name)

    activity_classes = [
        node for node in tree.body
        if all((
            isinstance(node, ast.ClassDef),
            any(_base_name(base).endswith('activity.Activity')
                for base in getattr(node, 'bases', ())),
        ))
    ]
    if len(activity_classes) != 1:
        report.errors.append(
            'Generated source must define exactly one Activity subclass.'
        )
        return report

    activity_class = activity_classes[0]
    methods = {
        node.name: node for node in activity_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for required in ('__init__', 'read_file', 'write_file'):
        if required not in methods:
            report.errors.append('Missing required method: %s' % required)

    calls = {
        _call_name(node.func) for node in ast.walk(activity_class)
        if isinstance(node, ast.Call)
    }
    for required_call in ('set_canvas', 'set_toolbar_box'):
        if not any(name.endswith(required_call) for name in calls):
            report.errors.append(
                'Generated activity must call %s().' % required_call
            )

    if 'StopButton' not in source:
        report.errors.append('Generated activity must include a StopButton.')
    if 'ToolbarBox' not in source:
        report.errors.append('Generated activity must include a ToolbarBox.')

    return report


def validate_activity_source_for_request(source, spec, plan=None):
    """Validate generated activity.py against the teacher's request.

    validate_source() checks the Sugar/Python safety contract.  This extra
    pass catches the common LLM failure mode where the source is technically
    valid but too generic to be the requested activity.
    """
    report = validate_source(source)
    if report.errors:
        return report

    request = _request_text(spec, plan)
    prompt = _spec_request_text(spec)
    prompt_words = _tokens(prompt)
    source_lower = source.lower()

    if len(source) < 1200:
        report.errors.append(
            'Generated activity is too small to be a full learner activity.'
        )

    if _has_any(prompt_words, (
            'draw', 'drawing', 'paint', 'painting', 'sketch', 'canvas',
            'color', 'colour')):
        _require_source_terms(
            report,
            source_lower,
            ('drawingarea',),
            'Drawing requests must use a Gtk.DrawingArea draw surface.',
        )
        _require_source_terms(
            report,
            source_lower,
            ('button-press-event', 'button_press_event',
             'motion-notify-event', 'motion_notify_event',
             'button-release-event', 'button_release_event',
             'eventmask', 'event_mask', 'add_events', 'add-events'),
            'Drawing requests must handle pointer events, not show a static '
            'sample image.',
        )
        _require_source_terms(
            report,
            source_lower,
            ('stroke', 'strokes', 'points', 'path', 'line', 'lines',
             'drawings', 'cairo'),
            'Drawing requests must store learner drawing state for Journal '
            'saving.',
        )

    if _has_any(prompt_words, (
            'two', 'pair', 'partner', 'partners', 'student', 'students',
            'team', 'teams', 'together', 'collaborative', 'collaboration')):
        _require_source_terms(
            report,
            source_lower,
            ('student', 'learner', 'team', 'partner', 'player'),
            'Two-learner requests must show learner/team roles in the '
            'activity.',
        )
        _require_source_terms(
            report,
            source_lower,
            ('turn', 'switch', 'active', 'partner', 'together',
             'collaborat'),
            'Two-learner requests must include a turn, role, or '
            'collaboration workflow.',
        )

    if 'carrom' in prompt_words:
        _require_source_terms(
            report,
            source_lower,
            ('striker', 'pocket', 'coin', 'queen'),
            'Carrom requests must model a board with striker, pockets, '
            'coins, or queen state.',
        )
        _require_source_terms(
            report,
            source_lower,
            ('score', 'turn', 'foul'),
            'Carrom requests must include scoring, turns, or fouls.',
        )

    if 'chess' in prompt_words:
        _require_source_terms(
            report,
            source_lower,
            ('king', 'queen', 'rook', 'bishop', 'knight', 'pawn'),
            'Chess requests must model chess pieces, not a generic grid.',
        )
        _require_source_terms(
            report,
            source_lower,
            ('8', 'grid', 'board', 'square'),
            'Chess requests must include a visible 8x8 board or board '
            'state.',
        )

    if _has_any(prompt_words, ('quiz', 'question', 'questions')):
        _require_source_terms(
            report,
            source_lower,
            ('question', 'answer', 'feedback', 'score'),
            'Quiz requests must include questions, answers, feedback, or '
            'score state.',
        )
        _require_source_terms(
            report,
            source_lower,
            ('entry', 'textview', 'button'),
            'Quiz requests must provide learner input controls.',
        )

    if re.search(r'\b(todo|lorem ipsum|placeholder only)\b',
                 source_lower):
        report.errors.append(
            'Generated activity still contains placeholder text.'
        )

    request_words = _tokens(request)
    overlap = request_words.intersection(_tokens(source))
    if request_words and len(overlap) < min(2, len(request_words)):
        report.warnings.append(
            'Generated source contains little vocabulary from the request.'
        )

    return report


def validate_project(project_path):
    report = ValidationReport()
    required_files = (
        'activity.py',
        'setup.py',
        'README.md',
        'LICENSE',
        'aod_plan.json',
        os.path.join('activity', 'activity.info'),
        os.path.join('activity', 'activity.svg'),
    )
    for relative_path in required_files:
        if not os.path.isfile(os.path.join(project_path, relative_path)):
            report.errors.append('Missing project file: %s' % relative_path)

    source_path = os.path.join(project_path, 'activity.py')
    if os.path.isfile(source_path):
        with open(source_path, encoding='utf-8') as source_file:
            report.extend(validate_source(source_file.read()))

    info_path = os.path.join(project_path, 'activity', 'activity.info')
    if os.path.isfile(info_path):
        report.extend(_validate_activity_info(info_path))

    if bundle_from_dir(project_path) is None:
        report.errors.append('Sugar cannot recognize the project directory.')

    return report


def validate_bundle(bundle_path):
    report = ValidationReport()
    if not os.path.isfile(bundle_path):
        report.errors.append('XO bundle does not exist.')
        return report

    try:
        bundle = bundle_from_archive(
            bundle_path,
            mime_type='application/vnd.olpc-sugar',
        )
        if bundle is None:
            report.errors.append('Sugar cannot recognize the XO bundle.')
            return report

        root = bundle.get_name().replace(' ', '') + '.activity/'
        with zipfile.ZipFile(bundle_path) as archive:
            names = archive.namelist()
        if not any(name.endswith('/activity/activity.info')
                   for name in names):
            report.errors.append(
                'XO bundle is missing activity/activity.info.'
            )
        if not any(name.endswith('/activity.py') for name in names):
            report.errors.append('XO bundle is missing activity.py.')
        if not all(name.startswith(root) for name in names):
            report.warnings.append(
                'XO root differs from the normalized activity name.'
            )
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        report.errors.append('Invalid XO bundle: %s' % error)

    return report


def _validate_activity_info(info_path):
    report = ValidationReport()
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(info_path, encoding='utf-8')
    except configparser.Error as error:
        report.errors.append('Invalid activity.info: %s' % error)
        return report

    if not parser.has_section('Activity'):
        report.errors.append('activity.info is missing [Activity].')
        return report

    required = (
        'name',
        'bundle_id',
        'icon',
        'exec',
        'activity_version',
        'license',
    )
    for key in required:
        if not parser.get('Activity', key, fallback='').strip():
            report.errors.append('activity.info is missing %s.' % key)

    license_id = parser.get('Activity', 'license', fallback='')
    if license_id not in LICENSE_IDS:
        report.errors.append(
            'activity.info has an unsupported license: %s' % license_id
        )

    exec_line = parser.get('Activity', 'exec', fallback='')
    if not exec_line.startswith('sugar-activity3 '):
        report.errors.append(
            'activity.info must launch with sugar-activity3.'
        )

    return report


def _request_text(spec, plan):
    parts = [_spec_request_text(spec)]
    if isinstance(plan, dict):
        for key in (
                'activity_kind',
                'summary',
                'learner_goal',
                'interaction_model',
                'state_schema'):
            value = plan.get(key)
            if isinstance(value, str):
                parts.append(value)
        for key in (
                'learner_steps',
                'ui_regions',
                'features',
                'classroom_flow'):
            values = plan.get(key)
            if isinstance(values, list):
                parts.extend(str(value) for value in values)
    return ' '.join(part for part in parts if part)


def _spec_request_text(spec):
    return ' '.join((
        getattr(spec, 'prompt', ''),
        getattr(spec, 'name', ''),
        getattr(spec, 'learner_goal', ''),
    ))


def _tokens(value):
    ignored = {
        'a', 'an', 'and', 'app', 'activity', 'can', 'create', 'for', 'make',
        'me', 'of', 'please', 'the', 'to', 'where', 'with',
    }
    return {
        token for token in re.findall(r'[a-z0-9]+', value.lower())
        if token not in ignored and len(token) > 2
    }


def _has_any(words, candidates):
    return bool(words.intersection(candidates))


def _require_source_terms(report, source_lower, terms, message):
    if not any(term in source_lower for term in terms):
        report.errors.append(message)


def _base_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return '%s.%s' % (_base_name(node.value), node.attr)
    return ''


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ''
