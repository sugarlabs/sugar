# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Live preview of generated Sugar activities.

Instead of showing a static mockup, this module imports the generated
activity.py, instantiates GeneratedActivity with a minimal stub base
class, and captures the real GTK canvas + toolbar widgets for embedding
in the AOD preview area.

The stub provides just enough of the sugar3.activity.Activity API for
generated code to run without D-Bus, the Sugar shell, or the Journal.
"""

import logging
import os
import re
import shutil
import tempfile
from gettext import gettext as _

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango


class _PreviewMetadata:
    """Minimal stand-in for Sugar's metadata object.

    The real metadata is a SugarMetadata GObject that emits 'updated'
    signals.  Generated activity widgets (ActivityToolbarButton,
    TitleEntry) call metadata.connect('updated', cb) and read
    metadata['title'] and metadata.get('icon-color').  We provide a
    dict subclass with a no-op connect() so the widgets construct
    without crashing.
    """

    def __init__(self, title):
        self._data = {
            'title': title or 'Preview',
            'icon-color': '',
            'description': '',
            'tags': '',
        }

    def __getitem__(self, key):
        return self._data.get(key, '')

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def get(self, key, fallback=None):
        return self._data.get(key, fallback)

    def keys(self):
        return self._data.keys()

    def connect(self, signal, callback):
        return 0

    def disconnect(self, handler_id):
        pass


class _NoOpProxy:
    """A proxy that absorbs all attribute access, calls, and iteration.

    Used by PreviewActivity.__getattr__ so that generated code like
    ``self.log_text_view.get_buffer()`` doesn't crash when
    ``log_text_view`` hasn't been created yet.
    """

    def __getattr__(self, name):
        return _NoOpProxy()

    def __call__(self, *args, **kwargs):
        return _NoOpProxy()

    def __iter__(self):
        return iter([])

    def __len__(self):
        return 0

    def __bool__(self):
        return False

    def __str__(self):
        return ''

    def __repr__(self):
        return '<NoOp>'

class PreviewActivity(Gtk.Window):
    """Minimal stub of sugar3.activity.Activity for preview rendering.

    Generated activities call activity.Activity.__init__(self, handle)
    and then self.set_canvas(), self.set_toolbar_box(), self.show_all().
    This stub captures the canvas and toolbar widgets so they can be
    reparented into the AOD preview area.

    The stub provides:
    - metadata: _PreviewMetadata for ActivityToolbarButton/StopButton
    - set_canvas/set_toolbar_box: capture widgets instead of using them
    - show_all/show: no-op (the preview area handles visibility)
    - add_stop_button/close: no-op
    - connect: fake signal registration for 'shared', 'joined', 'closing'
    - get_bundle_path: returns the project directory for icon loading
    """

    __gsignals__ = {
        'shared': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'joined': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'closing': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, handle=None, bundle_path=''):
        Gtk.Window.__init__(self)
        self._handle = handle
        self._bundle_path = bundle_path
        self._canvas = None
        self._toolbar_box = None
        self._stop_buttons = []
        self.metadata = _PreviewMetadata('Preview')
        self._stop_callback = None
        self.max_participants = 1
        self.shared_activity = None
        self._title = self.metadata['title']
        self._activity_root = ''

    def __getattr__(self, name):
        # Generated activities sometimes call self.some_method() or
        # access attributes (including private ones like
        # self._lesson_steps) before creating them in __init__.
        # Return a safe no-op proxy that absorbs all attribute access
        # and calls instead of crashing with AttributeError.  Dunder
        # lookups must still fail normally so Python protocol probes
        # (copy, pickle, GObject machinery) behave correctly, and once
        # construction is over private attributes raise normally again
        # so lazy-init idioms in event handlers keep working:
        #     if not hasattr(self, '_count'):
        #         self._count = 0
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        if name.startswith('_') and self.__dict__.get(
                '_preview_construction_done', False):
            raise AttributeError(name)
        return _NoOpProxy()

    def set_canvas(self, canvas):
        self._canvas = canvas

    def get_canvas(self):
        return self._canvas

    def set_toolbar_box(self, toolbar_box):
        self._toolbar_box = toolbar_box

    def get_toolbar_box(self):
        return self._toolbar_box

    def show_all(self):
        pass

    def show(self):
        pass

    def add_stop_button(self, button):
        self._stop_buttons.append(button)

    def close(self):
        if self._stop_callback is not None:
            self._stop_callback()
        self.emit('closing')

    def set_stop_callback(self, callback):
        self._stop_callback = callback

    def get_bundle_path(self):
        return self._bundle_path

    def get_bundle_id(self):
        return _read_bundle_id(self._bundle_path)

    def get_id(self):
        return 'aod-preview'

    def save(self):
        pass

    def share(self):
        pass

    def get_shared_activity(self):
        return self.shared_activity

    def set_title(self, title):
        self._title = title
        self.metadata['title'] = title

    def get_title(self):
        return self._title

    def get_activity_root(self):
        if not self._activity_root:
            self._activity_root = tempfile.mkdtemp(
                prefix='aod-preview-root-')
            for subdir in ('data', 'instance', 'tmp'):
                os.makedirs(
                    os.path.join(self._activity_root, subdir),
                    exist_ok=True,
                )
        return self._activity_root

    def get_documents_path(self):
        return tempfile.gettempdir()

    def cleanup(self):
        """Remove the temporary activity root directory if one was created."""
        root = self._activity_root
        if root and os.path.isdir(root):
            shutil.rmtree(root, ignore_errors=True)
        self._activity_root = ''

    def write_file(self, file_path):
        pass

    def read_file(self, file_path):
        pass

    def copy(self):
        pass

    def get_xo_color(self):
        try:
            from sugar3.graphics.xocolor import XoColor
            return XoColor()
        except Exception:
            return None

    def busy(self):
        pass

    def unbusy(self):
        pass

    def get_preferred_size(self):
        return 1200, 900


def render_activity_preview(project_path, activity_name=''):
    """Import and instantiate a generated activity for preview.

    Reads activity.py from project_path, replaces the sugar3 Activity
    base class with PreviewActivity, execs the modified source, and
    returns a PreviewActivity instance with the real canvas and toolbar
    widgets ready for embedding.

    Returns (preview_activity, canvas_widget, toolbar_widget) or
    (None, error_message, None) if instantiation fails.
    """
    source_path = os.path.join(project_path, 'activity.py')
    if not os.path.isfile(source_path):
        return None, 'activity.py not found in %s' % project_path, None

    try:
        with open(source_path, encoding='utf-8') as f:
            source = f.read()
    except OSError as error:
        return None, 'Could not read activity.py: %s' % error, None

    patched_source = _patch_source(source)

    bundle_path = project_path
    _install_bundle_path_helper(bundle_path)
    _install_preview_compatibility()

    result = _try_exec_preview(patched_source, source_path,
                               bundle_path, activity_name)
    if result[0] is not None:
        return result

    first_error = result[1]
    logging.warning('First preview attempt failed: %s', first_error)

    # Second attempt: add import-error resilience and stub missing
    # modules that some LLM-generated code references.
    hardened_source = _harden_imports(patched_source)
    result = _try_exec_preview(hardened_source, source_path,
                               bundle_path, activity_name)
    if result[0] is not None:
        return result

    logging.warning('Hardened preview also failed: %s', result[1])

    # Last attempt: wrap every import so no exotic module the model
    # hallucinated can take the whole preview down.
    aggressive_source = _harden_imports(patched_source, aggressive=True)
    result = _try_exec_preview(aggressive_source, source_path,
                               bundle_path, activity_name)
    if result[0] is not None:
        return result

    logging.warning('Aggressive preview also failed: %s', result[1])
    return None, first_error, None


def _try_exec_preview(patched_source, source_path, bundle_path,
                      activity_name):
    """Try to exec the patched source and return a preview tuple."""
    preview = PreviewActivity(bundle_path=bundle_path)
    preview.metadata = _PreviewMetadata(activity_name or 'Preview')

    namespace = {
        '__name__': 'aod_preview_module',
        '__file__': source_path,
        'PreviewActivity': PreviewActivity,
        '_preview_instance': preview,
        # Keep preview useful when otherwise valid generated code forgot the
        # standard gettext import.  The exported source is still validated
        # separately; this fallback only prevents the preview from blanking.
        '_': _,
    }

    try:
        exec(compile(patched_source, source_path, 'exec'), namespace)
    except SyntaxError as error:
        return None, 'Syntax error in activity.py line %s: %s' % (
            error.lineno, error.msg), None
    except Exception as error:
        logging.exception('Preview exec failed')
        return None, 'Could not load activity: %s' % error, None

    activity_class = namespace.get('GeneratedActivity')
    if activity_class is None:
        return None, 'GeneratedActivity class not found in source', None

    # Construct via __new__ + explicit __init__ so that when the
    # generated __init__ crashes we still hold the partially-built
    # instance and can salvage whatever canvas it managed to set,
    # without running side effects (timers, tempdirs) a second time.
    try:
        instance = activity_class.__new__(activity_class)
        if isinstance(instance, PreviewActivity):
            PreviewActivity.__init__(instance)
    except Exception as error:
        logging.exception('Preview instance allocation failed')
        return None, 'Activity __init__ failed: %s' % error, None

    try:
        instance.__init__(handle=None)
    except Exception as error:
        logging.exception('Preview __init__ failed')
        if not _has_salvageable_canvas(instance):
            _dispose_preview_instance(instance)
            return None, 'Activity __init__ failed: %s' % error, None
        logging.warning(
            'Preview salvaged a partial canvas after __init__ failed: %s',
            error)

    if not isinstance(instance, PreviewActivity):
        return None, 'Activity did not inherit from PreviewActivity', None

    instance.__dict__['_preview_construction_done'] = True

    try:
        canvas = instance.get_canvas()
    except Exception:
        canvas = None
    try:
        toolbar = instance.get_toolbar_box()
    except Exception:
        toolbar = None
    if isinstance(toolbar, _NoOpProxy):
        toolbar = None

    if canvas is None or isinstance(canvas, _NoOpProxy):
        return None, 'Activity did not call set_canvas()', None

    return instance, canvas, toolbar


def _has_salvageable_canvas(instance):
    """Return True when a crashed instance still holds a usable canvas.

    Many generated activities crash after set_canvas() while wiring
    secondary features (timers, journal hooks, decorations).  The
    canvas that was already built is still perfectly previewable, so
    keep it instead of losing the whole preview.
    """
    try:
        canvas = instance.get_canvas()
    except Exception:
        return False
    return canvas is not None and not isinstance(canvas, _NoOpProxy)


def _dispose_preview_instance(instance):
    """Best-effort teardown of a failed preview instance."""
    try:
        instance.cleanup()
    except Exception:
        pass
    try:
        if isinstance(instance, Gtk.Widget):
            instance.destroy()
    except Exception:
        pass


def _harden_imports(source, aggressive=False):
    """Wrap problematic imports so preview survives missing modules.

    LLM-generated code sometimes imports sugar3 sub-modules that exist
    at runtime but fail during in-process exec (e.g. sugar3.datastore,
    sugar3.presence).  We wrap known-problematic import lines in
    try/except so the rest of the activity can still render.

    With aggressive=True every single-line import except the gi core is
    wrapped, as a last resort before giving up on the preview.
    """
    fragile_modules = (
        'sugar3.datastore',
        'sugar3.presence',
        'sugar3.network',
        'sugar3.profile',
        'sugar3.mime',
        'telepathy',
        'dbus',
    )
    lines = source.split('\n')
    patched_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(('import ', 'from ')):
            if aggressive:
                is_core = (
                    stripped == 'import gi' or
                    stripped.startswith(('import gi.', 'import gi ',
                                         'from gi import', 'from gi.',
                                         'from __future__')))
                balanced = stripped.count('(') == stripped.count(')')
                # Only wrap top-level imports: indented ones are often
                # already inside a try/except ImportError fallback, and
                # wrapping those would swallow the ImportError the
                # fallback depends on.
                top_level = line == stripped
                wrap = (not is_core and balanced and top_level and
                        not stripped.endswith('\\'))
            else:
                wrap = any(module in stripped
                           for module in fragile_modules)
            if wrap:
                indent = line[:len(line) - len(stripped)]
                patched_lines.append('%stry:' % indent)
                patched_lines.append('    %s' % line)
                patched_lines.append('%sexcept (ImportError, Exception):'
                                     % indent)
                patched_lines.append('%s    pass' % indent)
                continue
        patched_lines.append(line)
    return '\n'.join(patched_lines)


def _patch_source(source):
    """Replace activity.Activity with PreviewActivity in source code.

    The generated source does:
        from sugar3.activity import activity
        class GeneratedActivity(activity.Activity):
            def __init__(self, handle):
                activity.Activity.__init__(self, handle)

    We replace the base class references so the generated class inherits
    from PreviewActivity instead of the real Activity, which requires
    D-Bus and the Sugar shell.

    LLM-generated code may use super().__init__(handle) or
    super(GeneratedActivity, self).__init__(handle) instead of the
    explicit activity.Activity.__init__ form. The class declaration
    patch handles those automatically because super() resolves via MRO
    to PreviewActivity once the class inherits from it.
    """
    patched = source

    # Explicit old-style super call.
    patched = patched.replace(
        'activity.Activity.__init__',
        'PreviewActivity.__init__',
    )

    # Class declaration: replace base class.
    patched = re.sub(
        r'class\s+GeneratedActivity\s*\(\s*activity\.Activity\s*\)\s*:',
        'class GeneratedActivity(PreviewActivity):',
        patched,
    )

    # Some models use Activity directly without the module prefix.
    patched = re.sub(
        r'class\s+GeneratedActivity\s*\(\s*Activity\s*\)\s*:',
        'class GeneratedActivity(PreviewActivity):',
        patched,
    )

    # Replace direct Activity.__init__ calls (without module prefix).
    # Use a letter lookbehind so we do not double-replace
    # PreviewActivity.__init__ (which already contains 'Activity').
    patched = re.sub(
        r'(?<![a-zA-Z])Activity\.__init__\s*\(\s*self',
        'PreviewActivity.__init__(self',
        patched,
    )

    return patched


def _install_preview_compatibility():
    """Install small shims for common generated GTK/Sugar API mistakes.

    Provider validation normally rejects these calls.  Validation can be
    disabled for faster iteration, though, and a minor API hallucination
    should not make the entire preview disappear.  Keep the shims narrowly
    scoped to unambiguous aliases with the same behavior as the real API.
    """
    try:
        from sugar3.graphics.toolbarbox import ToolbarBox
        if not hasattr(ToolbarBox, 'add_toolbar_button'):
            ToolbarBox.add_toolbar_button = _add_toolbar_button
    except ImportError:
        pass

    if not hasattr(Gtk.Adjustment, 'set_bounds'):
        Gtk.Adjustment.set_bounds = _set_adjustment_bounds


def _add_toolbar_button(toolbar_box, item):
    toolbar_box.toolbar.insert(item, -1)


def _set_adjustment_bounds(adjustment, lower, upper):
    adjustment.set_lower(lower)
    adjustment.set_upper(upper)


_bundle_path_override = ['']


def _install_bundle_path_helper(bundle_path):
    """Make sugar3.activity.activity.get_bundle_path() return the project dir.

    ActivityToolbarButton calls get_bundle_path() to load the activity
    icon.  We temporarily monkey-patch it to return the generated
    project directory so the icon loads without a real bundle.
    """
    _bundle_path_override[0] = bundle_path

    try:
        from sugar3.activity import activity as sugar_activity
        if not hasattr(sugar_activity, '_original_get_bundle_path'):
            sugar_activity._original_get_bundle_path = \
                sugar_activity.get_bundle_path
        sugar_activity.get_bundle_path = _get_bundle_path
    except ImportError:
        pass


def _get_bundle_path():
    return _bundle_path_override[0] or '.'


def _read_bundle_id(bundle_path):
    info_path = os.path.join(bundle_path or '', 'activity', 'activity.info')
    try:
        with open(info_path, encoding='utf-8') as info_file:
            for line in info_file:
                line = line.strip()
                if line.startswith('bundle_id'):
                    unused_key, value = line.split('=', 1)
                    return value.strip()
    except (OSError, ValueError):
        pass
    return os.environ.get('SUGAR_BUNDLE_ID', 'org.sugarlabs.aod.preview')


def _restore_bundle_path():
    try:
        from sugar3.activity import activity as sugar_activity
        if hasattr(sugar_activity, '_original_get_bundle_path'):
            sugar_activity.get_bundle_path = \
                sugar_activity._original_get_bundle_path
    except ImportError:
        pass
