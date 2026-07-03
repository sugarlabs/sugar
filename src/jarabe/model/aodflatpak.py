# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Flatpak export for generated Sugar activities.

The primary artifact is a self-contained ``.tar.gz`` that holds a Flatpak
manifest, the activity sources, a launcher, and a ``build.sh``. Anyone can
unpack it and run ``flatpak-builder`` to produce an installable Flatpak.

When ``flatpak-builder`` is available on the machine, :func:`package_flatpak`
additionally tries to build a ready-to-install ``.flatpak`` bundle. That build
needs the ``org.gnome.Platform``/``org.gnome.Sdk`` runtimes and network access,
so it is best-effort: on failure the buildable source bundle is still returned.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tarfile

from jarabe.model.aodgenerator import _identifier

# Flatpak application ids are reverse-DNS: at least two dot-separated
# elements, each starting with a letter or underscore and otherwise
# alphanumeric/underscore. Validating against this keeps a provider-supplied
# bundle_id from reaching a filename, the generated build.sh, or a
# flatpak-builder argument with path-traversal or shell metacharacters.
# \A and \Z (not ^/$) so a trailing newline cannot slip through validation.
_APP_ID_RE = re.compile(
    r'\A[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+\Z')

_RUNTIME = 'org.gnome.Platform'
_SDK = 'org.gnome.Sdk'
_RUNTIME_VERSION = '46'
_LAUNCHER_NAME = 'sugar-activity-run'
_SUGAR_TOOLKIT_GIT = 'https://github.com/sugarlabs/sugar-toolkit-gtk3.git'


def _is_valid_app_id(app_id):
    if not isinstance(app_id, str) or len(app_id) > 255:
        return False
    return _APP_ID_RE.match(app_id) is not None


def flatpak_app_id(plan):
    """Return a validated Flatpak application id for a generated activity.

    ``plan['bundle_id']`` may carry a provider/LLM-supplied value (see
    ``normalize_plan``), so it is validated against the Flatpak app-id grammar
    before use. Anything that does not match falls back to a safe deterministic
    id derived from the activity name, so a tainted bundle_id can never reach a
    filename, the generated ``build.sh``, or a ``flatpak-builder`` argument.
    """
    bundle_id = plan.get('bundle_id')
    if _is_valid_app_id(bundle_id):
        return bundle_id
    return 'org.sugarlabs.aod.%s' % _identifier(plan.get('name', 'Activity'))


def _flatpak_stem(spec, plan):
    return _identifier(getattr(spec, 'name', '') or plan.get('name', ''))


def render_flatpak_manifest(spec, plan, app_id):
    """Build the Flatpak manifest dictionary for the activity."""
    class_name = plan.get('class_name', 'GeneratedActivity')
    manifest = {
        'app-id': app_id,
        'runtime': _RUNTIME,
        'runtime-version': _RUNTIME_VERSION,
        'sdk': _SDK,
        'command': _LAUNCHER_NAME,
        'finish-args': [
            '--share=ipc',
            '--socket=fallback-x11',
            '--socket=wayland',
            '--socket=pulseaudio',
            '--device=dri',
            '--share=network',
            '--filesystem=home',
        ],
        'modules': [
            {
                'name': 'sugar-toolkit-gtk3',
                'buildsystem': 'autotools',
                'config-opts': ['--disable-static'],
                'sources': [
                    {
                        'type': 'git',
                        'url': _SUGAR_TOOLKIT_GIT,
                        'branch': 'master',
                    },
                ],
            },
            {
                'name': 'activity',
                'buildsystem': 'simple',
                'build-commands': [
                    'python3 setup.py install --prefix=/app',
                ],
                'sources': [
                    {'type': 'dir', 'path': 'activity-src'},
                ],
            },
            {
                'name': 'launcher',
                'buildsystem': 'simple',
                'build-commands': [
                    'install -D -m755 %s /app/bin/%s'
                    % (_LAUNCHER_NAME, _LAUNCHER_NAME),
                ],
                'sources': [
                    {'type': 'file', 'path': _LAUNCHER_NAME},
                ],
            },
        ],
        'x-sugar': {
            'activity-class': 'activity.%s' % class_name,
            'bundle-id': app_id,
        },
    }
    return manifest


def render_flatpak_launcher(plan):
    """Return the wrapper that launches the activity outside the shell."""
    class_name = plan.get('class_name', 'GeneratedActivity')
    return (
        '#!/bin/sh\n'
        '# SPDX-License-Identifier: GPL-3.0-or-later\n'
        '# Launch the bundled Sugar activity outside the Sugar shell.\n'
        'ACTIVITY_ROOT="/app/share/sugar/activities"\n'
        'BUNDLE_DIR="$(find "$ACTIVITY_ROOT" -maxdepth 1 -name \'*.activity\' '
        '-print -quit 2>/dev/null)"\n'
        'if [ -n "$BUNDLE_DIR" ]; then\n'
        '    cd "$BUNDLE_DIR" || true\n'
        'fi\n'
        'exec sugar-activity3 activity.%s "$@"\n'
    ) % class_name


def render_flatpak_build_script(stem, app_id):
    """Return a build.sh that turns the manifest into a .flatpak."""
    return (
        '#!/bin/sh\n'
        '# SPDX-License-Identifier: GPL-3.0-or-later\n'
        'set -e\n'
        '# Build and bundle this activity as a Flatpak.\n'
        '# Requires flatpak-builder and the %(runtime)s/%(sdk)s//%(ver)s '
        'runtimes.\n'
        'APP_ID="%(app_id)s"\n'
        'MANIFEST="$APP_ID.json"\n'
        'flatpak-builder --force-clean --repo=repo build-dir "$MANIFEST"\n'
        'flatpak build-bundle repo "%(stem)s.flatpak" "$APP_ID"\n'
        'echo "Built %(stem)s.flatpak"\n'
        'echo "Install with: flatpak install --user %(stem)s.flatpak"\n'
    ) % {
        'runtime': _RUNTIME,
        'sdk': _SDK,
        'ver': _RUNTIME_VERSION,
        'app_id': app_id,
        'stem': stem,
    }


def render_flatpak_readme(spec, plan, app_id, stem):
    """Return a README describing how to build the exported Flatpak."""
    name = getattr(spec, 'name', '') or plan.get('name', 'Activity')
    return (
        '# %(name)s — Flatpak export\n\n'
        'This folder contains a Flatpak manifest (`%(app_id)s.json`), the '
        'activity sources under `activity-src/`, a launcher, and a build '
        'script.\n\n'
        '## Build\n\n'
        '```sh\n'
        './build.sh\n'
        '```\n\n'
        'or manually:\n\n'
        '```sh\n'
        'flatpak-builder --force-clean --repo=repo build-dir %(app_id)s.json\n'
        'flatpak build-bundle repo %(stem)s.flatpak %(app_id)s\n'
        'flatpak install --user %(stem)s.flatpak\n'
        '```\n\n'
        '## Notes\n\n'
        'This manifest targets the `%(runtime)s//%(ver)s` runtime and builds '
        '`sugar-toolkit-gtk3` from source as a module. It is a starting '
        'point: depending on the runtime, the toolkit build may need extra '
        'dependencies, and the launcher path may need tuning for your '
        'activity. Validate the build against a real Sugar runtime before '
        'distributing.\n'
    ) % {
        'name': name,
        'app_id': app_id,
        'stem': stem,
        'runtime': _RUNTIME,
        'ver': _RUNTIME_VERSION,
    }


def assemble_flatpak_sources(result, staging_dir):
    """Write the buildable Flatpak sources for ``result`` into ``staging_dir``.

    Returns the path to ``staging_dir``.
    """
    spec = result.spec
    plan = result.plan
    app_id = flatpak_app_id(plan)
    stem = _flatpak_stem(spec, plan)

    if os.path.isdir(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)

    manifest = render_flatpak_manifest(spec, plan, app_id)
    manifest_path = os.path.join(staging_dir, '%s.json' % app_id)
    with open(manifest_path, 'w', encoding='utf-8') as manifest_file:
        json.dump(manifest, manifest_file, indent=4, sort_keys=True)
        manifest_file.write('\n')

    launcher_path = os.path.join(staging_dir, _LAUNCHER_NAME)
    with open(launcher_path, 'w', encoding='utf-8') as launcher_file:
        launcher_file.write(render_flatpak_launcher(plan))
    os.chmod(launcher_path, 0o755)

    build_path = os.path.join(staging_dir, 'build.sh')
    with open(build_path, 'w', encoding='utf-8') as build_file:
        build_file.write(render_flatpak_build_script(stem, app_id))
    os.chmod(build_path, 0o755)

    readme_path = os.path.join(staging_dir, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as readme_file:
        readme_file.write(render_flatpak_readme(spec, plan, app_id, stem))

    source_dir = os.path.join(staging_dir, 'activity-src')
    os.makedirs(source_dir)
    for relative_path, content in (result.files or {}).items():
        destination = os.path.join(source_dir, relative_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'w', encoding='utf-8') as source_file:
            source_file.write(content)

    return staging_dir


def _flatpak_root(result):
    return os.path.abspath(result.project_path.rstrip(os.sep) + '-flatpak')


def flatpak_builder_available():
    return shutil.which('flatpak-builder') is not None


def _build_flatpak_bundle(staging_dir, flatpak_root, app_id, stem):
    """Best-effort ``flatpak-builder`` run; returns .flatpak path or None."""
    manifest = '%s.json' % app_id
    repo_dir = os.path.join(flatpak_root, 'repo')
    build_dir = os.path.join(flatpak_root, 'build-dir')
    output_path = os.path.join(flatpak_root, '%s.flatpak' % stem)
    try:
        subprocess.run(
            ['flatpak-builder', '--force-clean', '--repo', repo_dir,
             build_dir, manifest],
            cwd=staging_dir, check=True, capture_output=True, timeout=1800)
        subprocess.run(
            ['flatpak', 'build-bundle', repo_dir, output_path, app_id],
            check=True, capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as error:
        logging.warning('flatpak-builder build failed, exporting sources '
                        'only: %s', error)
        return None
    if os.path.isfile(output_path):
        return output_path
    return None


def package_flatpak(result):
    """Package ``result`` as a Flatpak export.

    Always produces a buildable ``.tar.gz`` of the Flatpak sources. When
    ``flatpak-builder`` is available it also tries to build an installable
    ``.flatpak``. Returns a dict with ``kind`` (``'flatpak'`` or ``'source'``),
    ``path`` (the artifact to hand to the user), ``source_path`` (the tarball),
    and ``app_id``.
    """
    plan = result.plan
    app_id = flatpak_app_id(plan)
    stem = _flatpak_stem(result.spec, plan)

    flatpak_root = _flatpak_root(result)
    os.makedirs(flatpak_root, exist_ok=True)
    staging_dir = os.path.join(flatpak_root, '%s-flatpak' % stem)
    assemble_flatpak_sources(result, staging_dir)

    tarball_path = os.path.join(flatpak_root, '%s-flatpak.tar.gz' % stem)
    if os.path.isfile(tarball_path):
        os.remove(tarball_path)
    with tarfile.open(tarball_path, 'w:gz') as tar:
        tar.add(staging_dir, arcname='%s-flatpak' % stem)

    builder_available = flatpak_builder_available()
    export = {
        'kind': 'source',
        'path': tarball_path,
        'source_path': tarball_path,
        'app_id': app_id,
        'builder_available': builder_available,
    }

    if builder_available:
        built = _build_flatpak_bundle(staging_dir, flatpak_root, app_id, stem)
        if built:
            export['kind'] = 'flatpak'
            export['path'] = built

    return export
