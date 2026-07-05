# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import unittest
from unittest import mock

from jarabe.model.aodgenerator import enrich_plan
from jarabe.model.aodruntime import run_runtime_check
from jarabe.model.aodtemplates import render_activity_source
from jarabe.model.aodspec import ActivitySpec

_HAVE_DISPLAY = bool(
    os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))


def _template_source():
    spec = ActivitySpec(
        'Runtime Probe',
        'Make a fractions quiz.',
        'logic_math',
        'MIT',
    )
    plan = enrich_plan(spec, {
        'template': 'quiz',
        'summary': 'Runtime check probe.',
        'learner_goal': 'Practice fractions.',
        'learner_steps': ['Try', 'Explain', 'Share'],
    })
    return render_activity_source(spec, plan)


class TestRuntimeCheck(unittest.TestCase):

    def test_disabled_by_env_is_skipped(self):
        with mock.patch.dict(os.environ, {'AOD_RUNTIME_CHECK': 'off'}):
            ok, detail = run_runtime_check('raise SystemExit(1)\n')
        self.assertTrue(ok)
        self.assertEqual('skipped: disabled', detail)

    def test_no_display_is_skipped(self):
        env = {key: value for key, value in os.environ.items()
               if key not in ('DISPLAY', 'WAYLAND_DISPLAY')}
        env['AOD_RUNTIME_CHECK'] = 'on'
        with mock.patch.dict(os.environ, env, clear=True):
            ok, detail = run_runtime_check('raise SystemExit(1)\n')
        self.assertTrue(ok)
        self.assertEqual('skipped: no display', detail)

    @unittest.skipUnless(_HAVE_DISPLAY, 'needs a display')
    def test_valid_template_source_passes(self):
        with mock.patch.dict(os.environ, {'AOD_RUNTIME_CHECK': 'on'}):
            ok, detail = run_runtime_check(
                _template_source(), 'Runtime Probe')
        self.assertTrue(ok, detail)
        self.assertEqual('passed', detail)

    @unittest.skipUnless(_HAVE_DISPLAY, 'needs a display')
    def test_crash_in_init_fails_with_traceback(self):
        source = _template_source()
        crashing = source.replace(
            'self._build_canvas()',
            'self._build_canvas()\n'
            '        raise RuntimeError("boom-at-runtime")',
            1,
        )
        self.assertNotEqual(source, crashing)
        with mock.patch.dict(os.environ, {'AOD_RUNTIME_CHECK': 'on'}):
            ok, detail = run_runtime_check(crashing, 'Runtime Probe')
        self.assertFalse(ok)
        self.assertIn('boom-at-runtime', detail)

    @unittest.skipUnless(_HAVE_DISPLAY, 'needs a display')
    def test_blocking_init_times_out(self):
        source = _template_source()
        blocking = source.replace(
            'self._build_canvas()',
            'self._build_canvas()\n'
            '        import time as _time\n'
            '        _time.sleep(120)',
            1,
        )
        self.assertNotEqual(source, blocking)
        with mock.patch.dict(os.environ, {'AOD_RUNTIME_CHECK': 'on'}):
            ok, detail = run_runtime_check(
                blocking, 'Runtime Probe', timeout=8)
        self.assertFalse(ok)
        self.assertIn('blocking loops', detail)


if __name__ == '__main__':
    unittest.main()
