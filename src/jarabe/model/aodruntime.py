# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Run generated code before accepting it.

Static validation cannot see runtime crashes — code that imports
cleanly and has the right structure can still die in __init__ or in
its Journal methods.  This gate executes each candidate activity in a
sandboxed subprocess (the same PreviewActivity path the studio preview
uses) so a crash becomes retry feedback for the model instead of a
broken activity for the learner.
"""

import os
import shutil
import subprocess
import sys
import tempfile

_HARNESS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'aodruntimeharness.py')
_REPO_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

# Snap/IDE shells leak library paths that break GTK in subprocesses;
# same sanitization the offscreen tests use.
_SANITIZED_VARS = (
    'LD_LIBRARY_PATH', 'GTK_PATH', 'GIO_MODULE_DIR',
    'GDK_PIXBUF_MODULE_FILE', 'GTK_EXE_PREFIX', 'GTK_IM_MODULE_FILE',
)

_DETAIL_LINES = 15

_ACTIVITY_INFO = (
    '[Activity]\n'
    'name = %(name)s\n'
    'bundle_id = org.sugarlabs.aod.RuntimeCheck\n'
    'icon = activity\n'
    'exec = sugar-activity3 activity.GeneratedActivity\n'
    'activity_version = 1\n'
    'license = MIT\n'
)


def _env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def run_runtime_check(source, name='Generated Activity', timeout=None):
    """Return (ok, detail); never raises.

    ok is True when the activity started, survived event pumping, and
    completed a Journal round-trip — or when the check cannot run here
    (no display / disabled), in which case detail says why it was
    skipped.
    """
    if os.environ.get('AOD_RUNTIME_CHECK', 'on').lower() in (
            'off', '0', 'no', 'false'):
        return True, 'skipped: disabled'
    if not (os.environ.get('DISPLAY')
            or os.environ.get('WAYLAND_DISPLAY')):
        return True, 'skipped: no display'

    if timeout is None:
        timeout = _env_int('AOD_RUNTIME_CHECK_TIMEOUT', 25)

    project_dir = tempfile.mkdtemp(prefix='aod-runtime-check-')
    try:
        os.makedirs(os.path.join(project_dir, 'activity'))
        with open(os.path.join(project_dir, 'activity.py'), 'w',
                  encoding='utf-8') as output:
            output.write(source)
        with open(os.path.join(project_dir, 'activity',
                               'activity.info'), 'w',
                  encoding='utf-8') as output:
            output.write(_ACTIVITY_INFO % {'name': name})

        env = {key: value for key, value in os.environ.items()
               if key not in _SANITIZED_VARS}
        env['GDK_BACKEND'] = 'x11'
        env['PYTHONPATH'] = _REPO_ROOT

        try:
            completed = subprocess.run(
                [sys.executable, _HARNESS, project_dir],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, (
                'The activity took longer than %d seconds to start. '
                'Remove blocking loops from __init__; drive animation '
                'and game loops with GLib.timeout_add instead.'
                % timeout)

        if completed.returncode == 0 and \
                'RUNTIME-OK' in completed.stdout:
            return True, 'passed'
        return False, _failure_detail(completed, project_dir)
    except Exception as error:
        # The gate itself failing must never block generation.
        return True, 'skipped: %s' % error
    finally:
        shutil.rmtree(project_dir, ignore_errors=True)


def _failure_detail(completed, project_dir):
    text = (completed.stderr or '') + '\n' + (completed.stdout or '')
    lines = [line for line in text.splitlines() if line.strip()]
    tail = lines[-_DETAIL_LINES:]
    detail = '\n'.join(tail).replace(project_dir, '<activity>')
    return detail or ('runtime check exited with code %d'
                      % completed.returncode)
