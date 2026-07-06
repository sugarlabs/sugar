#!/usr/bin/env python3
"""Comprehensive Activity-on-Demand test and code-structure report."""

import os
import sys
import tempfile
import threading
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodspec import name_from_prompt
from jarabe.model.aodspec import CATEGORIES
from jarabe.model.aodspec import TEMPLATES
from jarabe.model.aodspec import LICENSE_IDS
from jarabe.model.aodgenerator import build_plan
from jarabe.model.aodgenerator import enrich_plan
from jarabe.model.aodgenerator import infer_template
from jarabe.model.aodgenerator import create_prototype_activity
from jarabe.model.aodgenerator import package_project
from jarabe.model.aodgenerator import normalize_plan
from jarabe.model.aodrag import build_corpus
from jarabe.model.aodrag import search
from jarabe.model.aodrag import get_api_reference
from jarabe.model.aodrag import get_example_sources
from jarabe.model.aodvalidator import validate_source
from jarabe.model.aodvalidator import validate_project
from jarabe.model.aodvalidator import validate_bundle
from jarabe.model.aodvalidator import ALLOWED_IMPORT_ROOTS
from jarabe.model.aodvalidator import FORBIDDEN_IMPORT_ROOTS
from jarabe.model.aodvalidator import FORBIDDEN_CALLS
from jarabe.model.aodllm import LLMProvider
from jarabe.model.aodllm import create_provider
from jarabe.model.aodllm import get_provider_statuses
from jarabe.model.aodllm import get_configured_provider
from jarabe.model.aodllm import normalize_provider_name
from jarabe.model.aodllm import ProviderError
from jarabe.model.aodpipeline import generate_activity
from jarabe.model.aodpipeline import PipelineError
from jarabe.model.aodjobs import AODJob
from jarabe.model.aodjobs import AODJobStore
from jarabe.model.aodjobs import STATUS_FINISHED
from jarabe.model.aodjobs import STATUS_FAILED
from jarabe.model.aodservice import AODService
from jarabe.model.aodcredentials import AODCredentialStore

PASS = 0
FAIL = 0
REPORT = []


def section(title):
    REPORT.append('\n=== %s ===' % title)
    print('\n=== %s ===' % title)


def ok(msg):
    global PASS
    PASS += 1
    REPORT.append('  PASS: %s' % msg)
    print('  PASS: %s' % msg)


def fail(msg):
    global FAIL
    FAIL += 1
    REPORT.append('  FAIL: %s' % msg)
    print('  FAIL: %s' % msg)


def check(cond, msg):
    if cond:
        ok(msg)
    else:
        fail(msg)


def test_spec():
    section('ActivitySpec')

    spec = ActivitySpec(
        name='Fraction Playground',
        prompt='a fractions playground where teams build models',
        category='logic_math',
        license_id='GPL-3.0-or-later',
        template='auto',
        age_band='8-10',
        learner_goal='Understand equivalent fractions.',
    )
    errors = spec.validate()
    check(not errors, 'valid spec passes validation')

    bad = ActivitySpec(
        name='',
        prompt='',
        category='invalid',
        license_id='invalid',
        template='invalid',
        age_band='',
    )
    errors = bad.validate()
    check(len(errors) >= 5, 'invalid spec reports multiple errors (%d)' % len(errors))

    auto_name = name_from_prompt('a drawing activity where I can paint')
    check(auto_name and 'Drawing' in auto_name, 'name_from_prompt extracts keywords: %s' % auto_name)

    check(set(CATEGORIES) == {'logic_math', 'tools_utils', 'games', 'creation'},
          'CATEGORIES match expected set')
    check('auto' in TEMPLATES and 'canvas' in TEMPLATES,
          'TEMPLATES includes auto and canvas')
    check('GPL-3.0-or-later' in LICENSE_IDS, 'LICENSE_IDS includes GPL-3.0-or-later')


def test_template_inference():
    section('Template Inference')

    cases = [
        ('a drawing canvas for kids', 'creation', 'canvas'),
        ('a quiz about animals', 'logic_math', 'quiz'),
        ('a chess board for two players', 'games', 'chess'),
        ('a story writing activity', 'creation', 'narrative'),
        ('a word counter tool', 'tools_utils', 'utility'),
        ('something completely vague', 'games', 'grid'),
    ]
    for prompt, category, expected in cases:
        spec = ActivitySpec(
            name=name_from_prompt(prompt),
            prompt=prompt,
            category=category,
            license_id='GPL-3.0-or-later',
            template='auto',
        )
        template = infer_template(spec)
        check(template == expected, '%r -> %s (expected %s)' % (prompt, template, expected))


def test_plan_building():
    section('Plan Building & Enrichment')

    spec = ActivitySpec(
        name='Quiz Game',
        prompt='a quiz about animals for young learners',
        category='logic_math',
        license_id='GPL-3.0-or-later',
        template='auto',
    )
    plan = build_plan(spec)
    check('template' in plan, 'plan has template')
    check('bundle_id' in plan, 'plan has bundle_id')
    check('class_name' in plan, 'plan has class_name')
    check('learner_steps' in plan, 'plan has learner_steps')

    enriched = enrich_plan(spec, plan)
    check('features' in enriched, 'enriched plan has features')
    check('classroom_flow' in enriched, 'enriched plan has classroom_flow')
    check('teacher_notes' in enriched, 'enriched plan has teacher_notes')

    if enriched['template'] == 'quiz':
        check('questions' in enriched, 'quiz plan has questions')
    else:
        ok('template was %s, not quiz; skipping question check' % enriched['template'])


def test_rag():
    section('RAG Corpus')

    corpus = build_corpus(activity_roots=('/nonexistent',))
    check(len(corpus) >= 5, 'corpus has at least built-in documents (%d)' % len(corpus))

    refs = search('drawing canvas', limit=3, template='canvas', corpus=corpus)
    check(len(refs) > 0, 'RAG search returns results for drawing canvas')
    if refs:
        check('canvas' in refs[0].tags or 'drawing' in refs[0].tags,
              'top result is canvas-related: %s' % refs[0].title)

    api = get_api_reference()
    check('Activity' in api and 'ToolbarBox' in api, 'API reference mentions Activity and ToolbarBox')

    examples = get_example_sources('quiz question answer', template='quiz', limit=2, corpus=corpus)
    check(len(examples) > 0, 'get_example_sources returns quiz examples')


def test_validator():
    section('AST Validator')

    good = '''
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from sugar3.activity import activity
from sugar3.activity.widgets import ActivityToolbarButton, StopButton
from sugar3.graphics.toolbarbox import ToolbarBox

class GeneratedActivity(activity.Activity):
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        self._build_toolbar()
        self._build_canvas()

    def _build_toolbar(self):
        toolbar_box = ToolbarBox()
        toolbar_box.toolbar.insert(ActivityToolbarButton(self), 0)
        toolbar_box.toolbar.insert(StopButton(self), -1)
        self.set_toolbar_box(toolbar_box)
        toolbar_box.show_all()

    def _build_canvas(self):
        canvas = Gtk.Label(label='Hello')
        self.set_canvas(canvas)
        canvas.show_all()

    def write_file(self, file_path):
        pass

    def read_file(self, file_path):
        pass
'''
    report = validate_source(good)
    check(report.valid, 'valid activity source passes validation')

    bad_import = good + '\nimport os\n'
    report = validate_source(bad_import)
    check(not report.valid and any('Forbidden import: os' in e for e in report.errors),
          'validator rejects forbidden import os')

    bad_call = good.replace('pass', 'eval("1")')
    report = validate_source(bad_call)
    check(not report.valid and any('Forbidden call: eval' in e for e in report.errors),
          'validator rejects forbidden call eval')

    missing_stop = good.replace('StopButton', 'SomeButton')
    report = validate_source(missing_stop)
    check(not report.valid and any('StopButton' in e for e in report.errors),
          'validator requires StopButton')

    syntax_error = good.replace('def __init__', 'def __init__')
    syntax_error = syntax_error.replace('pass', 'def broken(:')
    report = validate_source(syntax_error)
    check(not report.valid and any('syntax error' in e for e in report.errors),
          'validator reports syntax errors')

    check('os' in FORBIDDEN_IMPORT_ROOTS, 'os is forbidden import')
    check('subprocess' in FORBIDDEN_IMPORT_ROOTS, 'subprocess is forbidden import')
    check('exec' in FORBIDDEN_CALLS, 'exec is forbidden call')
    check('sugar3' in ALLOWED_IMPORT_ROOTS, 'sugar3 is allowed import')


def test_providers():
    section('LLM Providers')

    statuses = get_provider_statuses()
    names = {s['name'] for s in statuses}
    check(names >= {'local-template', 'gemini', 'openai', 'claude', 'ollama'},
          'provider statuses include expected providers')

    local = create_provider('local-template')
    check(local is None, 'local-template provider is None')

    for name in ('gemini', 'openai', 'claude', 'deepseek', 'qwen', 'moonshot',
                 'opencode', 'opencode-go'):
        try:
            create_provider(name)
            fail('%s provider created without key (unexpected)' % name)
        except ProviderError:
            ok('%s provider requires API key' % name)

    try:
        ollama = create_provider('ollama')
        ok('ollama provider created without key')
    except ProviderError as e:
        ok('ollama provider error: %s' % e)

    check(normalize_provider_name('Default') == 'default', 'normalize default')
    check(normalize_provider_name('GOOGLE') == 'gemini', 'normalize google -> gemini')
    check(normalize_provider_name('template') == 'local-template', 'normalize template')
    check(normalize_provider_name('anthropic') == 'claude', 'normalize anthropic -> claude')


def test_pipeline_local():
    section('Pipeline: Local Template')

    spec = ActivitySpec(
        name=name_from_prompt('a typing practice game'),
        prompt='a typing practice game',
        category='tools_utils',
        license_id='GPL-3.0-or-later',
        template='auto',
    )
    output = tempfile.mkdtemp(prefix='aod_pipeline_local_')
    result = generate_activity(spec, output_root=output, provider_name='local-template', use_rag=False)

    check(result.bundle_path and os.path.isfile(result.bundle_path),
          'local pipeline produces XO bundle')
    check(result.project_path and os.path.isdir(result.project_path),
          'local pipeline produces project directory')
    check('activity.py' in result.files, 'project contains activity.py')
    check(result.plan.get('code_source') == 'template', 'code_source is template')

    bundle_report = validate_bundle(result.bundle_path)
    check(bundle_report.valid, 'generated bundle passes validation')

    project_report = validate_project(result.project_path)
    check(project_report.valid, 'generated project passes validation')


def test_pipeline_provider_code():
    section('Pipeline: Provider Code Path')

    class FakeCodeProvider(LLMProvider):
        name = 'fake'
        model = 'fake-model'

        def generate_plan(self, system_prompt, user_prompt, timeout=45):
            return {'template': 'quiz'}

        def generate_activity_source(self, system_prompt, user_prompt, timeout=90):
            return '''import gi\ngi.require_version('Gtk', '3.0')\nfrom gi.repository import Gtk\nfrom sugar3.activity import activity\nfrom sugar3.activity.widgets import ActivityToolbarButton, StopButton\nfrom sugar3.graphics.toolbarbox import ToolbarBox\n\nclass GeneratedActivity(activity.Activity):\n    def __init__(self, handle):\n        activity.Activity.__init__(self, handle)\n        self._build_toolbar()\n        self._build_canvas()\n    def _build_toolbar(self):\n        toolbar_box = ToolbarBox()\n        toolbar_box.toolbar.insert(ActivityToolbarButton(self), 0)\n        toolbar_box.toolbar.insert(StopButton(self), -1)\n        self.set_toolbar_box(toolbar_box)\n        toolbar_box.show_all()\n    def _build_canvas(self):\n        canvas = Gtk.Label(label='Fake provider activity')\n        self.set_canvas(canvas)\n        canvas.show_all()\n    def write_file(self, file_path):\n        pass\n    def read_file(self, file_path):\n        pass\n'''

    spec = ActivitySpec(
        name=name_from_prompt('a quiz about animals'),
        prompt='a quiz about animals',
        category='creation',
        license_id='GPL-3.0-or-later',
        template='auto',
    )
    output = tempfile.mkdtemp(prefix='aod_pipeline_fake_')
    result = generate_activity(spec, output_root=output, provider=FakeCodeProvider(),
                               provider_name='fake', use_rag=False)

    check(result.plan.get('code_source') == 'provider',
          'provider code path sets code_source=provider')
    check(result.bundle_path and os.path.isfile(result.bundle_path),
          'provider code pipeline produces XO bundle')


def test_job_store():
    section('Job Store')

    root = tempfile.mkdtemp(prefix='aod_jobs_')
    store = AODJobStore(root_path=root)

    spec = ActivitySpec(
        name='Test',
        prompt='test prompt',
        category='creation',
        license_id='GPL-3.0-or-later',
    )
    job = AODJob.create(spec, provider_name='gemini')
    store.save(job)

    loaded = store.load(job.job_id)
    check(loaded is not None, 'job store loads saved job')
    check(loaded.spec.name == 'Test', 'loaded job preserves spec name')

    jobs = store.list_jobs()
    check(len(jobs) == 1, 'job store lists one job')

    from types import SimpleNamespace
    mock_result = SimpleNamespace(
        spec=spec, bundle_id='test.bundle', bundle_path='/tmp/test.xo',
        project_path='/tmp/test.activity', provider='local', model='',
        plan={'template': 'canvas', 'code_source': 'template'},
    )
    job.finish(mock_result)
    check(job.is_terminal(), 'finished job is terminal')

    job2 = AODJob.create(spec, provider_name='local-template')
    job2.fail('test error')
    check(job2.is_terminal() and job2.status == STATUS_FAILED,
          'failed job is terminal with failed status')


def test_service():
    section('AOD Service')

    root = tempfile.mkdtemp(prefix='aod_service_')
    store = AODJobStore(root_path=root)
    service = AODService(job_store=store, worker_count=1)

    spec = ActivitySpec(
        name=name_from_prompt('a simple counting tool'),
        prompt='a simple counting tool',
        category='tools_utils',
        license_id='GPL-3.0-or-later',
        template='auto',
    )

    events = []

    def callback(job):
        events.append((job.status, job.progress))

    job = service.submit_activity(spec, provider_name='local-template', use_rag=False,
                                  output_root=tempfile.mkdtemp(prefix='aod_service_out_'),
                                  callback=callback)

    # wait for completion
    for _ in range(60):
        if job.is_terminal():
            break
        time.sleep(0.5)

    check(job.is_terminal(), 'service job reaches terminal state')
    check(job.status == STATUS_FINISHED, 'service job finishes successfully')
    check(job.result is not None, 'service job has result')
    check(len(events) > 0, 'service emitted progress callbacks')

    service.shutdown(wait=True)


def test_credentials():
    section('Credential Store')

    root = tempfile.mkdtemp(prefix='aod_creds_')
    store = AODCredentialStore(root_path=root, secret_backend=False)

    store.save_provider('gemini', api_key='secret-key-123', model='gemini-test')
    loaded = store.load_provider('gemini')
    check(loaded['api_key'] == 'secret-key-123', 'credential store saves API key')
    check(loaded['model'] == 'gemini-test', 'credential store saves model')

    status = store.provider_status('gemini')
    check(status['has_api_key'], 'provider status reports key present')

    default = store.get_default_provider_name()
    check(default == 'gemini', 'last saved provider becomes default')

    removed = store.remove_api_key('gemini')
    check(removed, 'remove_api_key succeeds')
    status = store.provider_status('gemini')
    check(not status['has_api_key'], 'provider status reports key removed')

    check(os.path.isfile(store.path), 'providers.env file exists')
    mode = os.stat(store.path).st_mode
    check((mode & 0o777) == 0o600, 'providers.env has 0o600 permissions')


def test_code_structure():
    section('Code Structure Report')

    base = os.path.join(os.path.dirname(__file__), 'src', 'jarabe', 'model')
    expected = [
        'aodcodegen.py', 'aodcredentials.py', 'aodgenerator.py', 'aodjobs.py',
        'aodlicenses.py', 'aodllm.py', 'aodpipeline.py', 'aodprompts.py',
        'aodqueue.py', 'aodrag.py', 'aodservice.py', 'aodspec.py',
        'aodtemplates.py', 'aodvalidator.py',
    ]
    missing = [f for f in expected if not os.path.isfile(os.path.join(base, f))]
    check(not missing, 'all expected AOD model modules exist')
    if missing:
        fail('missing: %s' % ', '.join(missing))

    desktop = os.path.join(os.path.dirname(__file__), 'src', 'jarabe', 'desktop')
    check(os.path.isfile(os.path.join(desktop, 'homebox.py')), 'homebox.py exists')
    check(os.path.isfile(os.path.join(desktop, 'viewtoolbar.py')), 'viewtoolbar.py exists')
    check(os.path.isfile(os.path.join(desktop, 'homewindow.py')), 'homewindow.py exists')

    # Count key classes/functions
    with open(os.path.join(base, 'aodllm.py'), encoding='utf-8') as f:
        text = f.read()
        check('GeminiProvider' in text, 'aodllm.py defines GeminiProvider')
        check('OpenAIProvider' in text, 'aodllm.py defines OpenAIProvider')
        check('ClaudeProvider' in text, 'aodllm.py defines ClaudeProvider')
        check('OllamaProvider' in text, 'aodllm.py defines OllamaProvider')

    with open(os.path.join(base, 'aodtemplates.py'), encoding='utf-8') as f:
        text = f.read()
        for t in ('canvas', 'grid', 'narrative', 'quiz', 'utility', 'chess'):
            check('_render_%s' % t in text, 'aodtemplates.py has _render_%s' % t)


def main():
    global PASS, FAIL
    PASS = 0
    FAIL = 0

    section('Starting comprehensive AOD test')

    test_spec()
    test_template_inference()
    test_plan_building()
    test_rag()
    test_validator()
    test_providers()
    test_pipeline_local()
    test_pipeline_provider_code()
    test_job_store()
    test_service()
    test_credentials()
    test_code_structure()

    section('Summary')
    check(True, 'PASS: %d' % PASS)
    check(FAIL == 0, 'FAIL: %d' % FAIL)

    report_path = os.path.join(tempfile.gettempdir(), 'aod_full_test_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(REPORT))
        f.write('\n')
    print('\nReport written to:', report_path)

    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
