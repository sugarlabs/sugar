# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
import os
import re
import threading


DEFAULT_ACTIVITY_ROOTS = (
    '/usr/share/sugar/activities',
    os.path.expanduser('~/Activities'),
)

_corpus_cache = None
_corpus_lock = threading.Lock()
_corpus_mtime = 0.0


@dataclass(frozen=True)
class RagDocument:
    title: str
    text: str
    tags: tuple = ()
    source_path: str = ''


def build_corpus(activity_roots=None):
    """Build corpus of RAG documents from installed Sugar activities.

    Result is cached at process level and invalidated when activity bundles
    are added or removed. Pass activity_roots to force a rebuild with
    different roots.
    """
    global _corpus_cache, _corpus_mtime

    roots = activity_roots or DEFAULT_ACTIVITY_ROOTS

    # If custom roots provided, bypass cache
    if activity_roots is not None:
        return _build_corpus_uncached(roots)

    # Check if we can use cached corpus
    with _corpus_lock:
        current_mtime = _get_roots_mtime(roots)
        if _corpus_cache is not None and current_mtime == _corpus_mtime:
            return _corpus_cache

        # Cache miss or invalidated — rebuild
        documents = _build_corpus_uncached(roots)
        _corpus_cache = documents
        _corpus_mtime = current_mtime
        return documents


def _build_corpus_uncached(roots):
    documents = list(_REFERENCE_DOCUMENTS)

    for root in roots:
        if not os.path.isdir(root):
            continue
        for bundle_name in sorted(os.listdir(root)):
            bundle_path = os.path.join(root, bundle_name)
            if not os.path.isdir(bundle_path):
                continue
            info_path = os.path.join(bundle_path, 'activity', 'activity.info')
            info_text = _read_text(info_path, 6000)
            if _is_generated_aod_bundle(bundle_path, info_text):
                continue
            source_path = _find_activity_source(bundle_path)
            if source_path is None and not info_text:
                continue
            info_tags = _info_tags(bundle_name, info_text)
            if info_text:
                documents.append(RagDocument(
                    title='%s activity.info manifest' % bundle_name,
                    text=info_text,
                    tags=info_tags + ('manifest', 'bundle'),
                    source_path=info_path,
                ))
            if source_path is None:
                continue
            source = _read_text(source_path, 14000)
            if not source:
                continue
            documents.append(RagDocument(
                title='%s main Sugar source example' % bundle_name,
                text=_join_activity_context(info_text, source),
                tags=tuple(sorted(set(_source_tags(source) + info_tags))),
                source_path=source_path,
            ))
            for support_path in _find_support_sources(
                    bundle_path, source_path):
                support_source = _read_text(support_path, 8000)
                if not support_source:
                    continue
                documents.append(RagDocument(
                    title='%s supporting GTK source: %s' % (
                        bundle_name,
                        os.path.basename(support_path),
                    ),
                    text=support_source,
                    tags=tuple(sorted(set(
                        _source_tags(support_source) + info_tags
                    ))),
                    source_path=support_path,
                ))

    return documents


def _get_roots_mtime(roots):
    """Return max mtime of all activity bundle directories under roots."""
    latest = 0.0
    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            for bundle_name in os.listdir(root):
                bundle_path = os.path.join(root, bundle_name)
                if os.path.isdir(bundle_path):
                    stat = os.stat(bundle_path)
                    latest = max(latest, stat.st_mtime)
        except OSError:
            continue
    return latest


def search(query, limit=5, template='', corpus=None):
    documents = corpus if corpus is not None else build_corpus()
    query_words = _tokens(query)
    ranked = []

    for document in documents:
        title_words = _tokens(document.title)
        tag_words = set(document.tags)
        text_words = _tokens(document.text[:6000])
        score = sum((
            6 * len(query_words.intersection(title_words)),
            4 * len(query_words.intersection(tag_words)),
            len(query_words.intersection(text_words)),
        ))
        if template and template in tag_words:
            score += 5
        if score:
            ranked.append((score, document.title, document))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[:limit]]


def get_example_sources(query, template='', limit=2, corpus=None):
    documents = search(
        query,
        limit=max(limit * 3, limit),
        template=template,
        corpus=corpus,
    )
    examples = [
        document for document in documents
        if document.source_path or 'example' in document.tags
    ]
    return examples[:limit]


def get_api_reference():
    return _API_REFERENCE


def _find_activity_source(bundle_path):
    info_path = os.path.join(bundle_path, 'activity', 'activity.info')
    exec_module = ''
    if os.path.isfile(info_path):
        try:
            with open(info_path, encoding='utf-8') as info_file:
                for line in info_file:
                    if line.startswith('exec') and '=' in line:
                        exec_value = line.split('=', 1)[1].strip().split()
                        if len(exec_value) >= 2:
                            exec_module = exec_value[1].split('.')[0]
                        break
        except OSError:
            pass

    candidates = []
    if exec_module:
        candidates.append(os.path.join(bundle_path, exec_module + '.py'))
    candidates.extend([
        os.path.join(bundle_path, 'activity.py'),
        os.path.join(bundle_path, 'main.py'),
    ])
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    try:
        for filename in sorted(os.listdir(bundle_path)):
            if filename.endswith('.py') and filename != 'setup.py':
                return os.path.join(bundle_path, filename)
    except OSError:
        pass
    return None


def _find_support_sources(bundle_path, primary_source_path, limit=2):
    candidates = []
    try:
        for filename in sorted(os.listdir(bundle_path)):
            if not filename.endswith('.py') or filename == 'setup.py':
                continue
            path = os.path.join(bundle_path, filename)
            if path == primary_source_path:
                continue
            candidates.append(path)
    except OSError:
        return []
    return candidates[:limit]


def _read_text(path, limit):
    if not path or not os.path.isfile(path):
        return ''
    try:
        with open(path, encoding='utf-8') as source_file:
            return source_file.read(limit)
    except (OSError, UnicodeDecodeError):
        return ''


def _join_activity_context(info_text, source):
    blocks = []
    if info_text:
        blocks.append('activity/activity.info:\n%s' % info_text[:3000])
    blocks.append('main Python source:\n%s' % source[:12000])
    return '\n\n'.join(blocks)


def _info_tags(bundle_name, info_text):
    text = '%s\n%s' % (bundle_name, info_text or '')
    tags = {'sugar'}
    if 'max_participants' in text:
        tags.add('collaboration')
    if 'summary' in text:
        tags.add('metadata')
    if 'mime_types' in text:
        tags.add('journal')
    for token in _tokens(text):
        if len(token) > 2:
            tags.add(token)
    return tuple(sorted(tags))


def _is_generated_aod_bundle(bundle_path, info_text):
    if os.path.exists(os.path.join(bundle_path, 'aod_plan.json')):
        return True
    lowered = (info_text or '').lower()
    return (
        'org.sugarlabs.aod.' in lowered or
        'activity on demand' in lowered
    )


def _source_tags(source):
    tags = {'sugar', 'gtk3'}
    checks = {
        'canvas': ('DrawingArea', 'draw'),
        'carrom': ('_draw_carrom_board', 'Pocket queen', 'striker'),
        'chess': ('_starting_board', '_can_move', 'White to move'),
        'grid': ('Gtk.Grid', 'Grid('),
        'narrative': ('TextView', 'write_file'),
        'quiz': ('question', 'answer'),
        'utility': ('Entry', 'ToolButton'),
        'journal': ('read_file', 'write_file'),
        'collaboration': ('max_participants', 'presence'),
        'cairo': ('cairo', 'context.'),
        'pango': ('Pango', 'pango'),
    }
    for tag, needles in checks.items():
        if any(needle in source for needle in needles):
            tags.add(tag)
    return tuple(sorted(tags))


def _tokens(value):
    return set(re.findall(r'[a-z0-9_]+', value.lower()))


_API_REFERENCE = """Sugar Activity API reference:
- Subclass sugar3.activity.activity.Activity.
- Receive the Sugar handle in __init__ and initialize the Activity base class.
- Create a ToolbarBox with ActivityToolbarButton and StopButton.
- Set the toolbar with self.set_toolbar_box(toolbar_box).
- Build GTK3 widgets and set the root widget with self.set_canvas(canvas).
- Call show_all() after the widget tree is assembled.
- Implement write_file(file_path) and read_file(file_path) for Journal data.
- GTK widgets must be updated on the GTK main thread.
- Generated activities should work without network access.
- Prefer sugar3 / sugar-toolkit-gtk3 APIs before raw GTK equivalents:
  - sugar3.graphics.style: FONT_SIZE, COLOR_*, zoom() for DPI-aware sizing
  - sugar3.graphics.toolbutton.ToolButton: icon toolbar items with tooltip
  - sugar3.graphics.alert: NotifyAlert / ConfirmationAlert for in-activity messages
  - sugar3.graphics.icon.Icon: Sugar icon widget (icon_name, pixel_size)
"""

_REFERENCE_DOCUMENTS = (
    RagDocument(
        title='Sugar activity lifecycle and bundle contract',
        text=_API_REFERENCE,
        tags=('api', 'bundle', 'journal', 'sugar', 'toolbar'),
    ),
    RagDocument(
        title='Minimal Sugar activity.py contract',
        text=(
            'A generated activity.py should import Gtk from gi.repository, '
            'import activity from sugar3.activity, subclass '
            'activity.Activity, initialize the base class with the handle, '
            'build a ToolbarBox with ActivityToolbarButton and StopButton, '
            'call self.set_toolbar_box(toolbar_box), create a GTK widget '
            'tree, call self.set_canvas(root_widget), connect real signal '
            'handlers for learner actions, implement read_file and '
            'write_file, and finish with self.show_all().'
        ),
        tags=('api', 'gtk3', 'journal', 'source', 'sugar', 'toolbar'),
    ),
    RagDocument(
        title='Sugar activity.info manifest contract',
        text=(
            'The generated bundle contains activity/activity.info with '
            'name, bundle_id, icon, exec, activity_version, license, summary, '
            'and tags. The exec line for generated activities is '
            'sugar-activity3 activity.GeneratedActivity. The Python class in '
            'activity.py must match that exec target.'
        ),
        tags=('bundle', 'manifest', 'metadata', 'sugar'),
    ),
    RagDocument(
        title='GTK layout pattern for learning activities',
        text=(
            'Use one main Gtk.Box. Put learner controls in a compact sidebar '
            'or toolbar and the main work surface in an expanding center '
            'area. Use Gtk.Grid for board or tile activities, Gtk.TextView '
            'inside Gtk.ScrolledWindow for writing and explanation, and '
            'Gtk.DrawingArea for drawing or visual simulations. Prefer clear '
            'labels and immediate feedback over decorative placeholders.'
        ),
        tags=('gtk3', 'layout', 'ui', 'widgets'),
    ),
    RagDocument(
        title='Journal persistence pattern',
        text=(
            'Keep learner state in simple Python data: strings, numbers, '
            'lists, and dictionaries. write_file serializes that state, '
            'usually as JSON text. read_file restores it and refreshes the '
            'widgets. Never write arbitrary paths; Sugar passes the Journal '
            'file path to those methods.'
        ),
        tags=('journal', 'persistence', 'state'),
    ),
    RagDocument(
        title='Canvas activity pattern',
        text=(
            'Use Gtk.DrawingArea, connect the draw signal, store learner '
            'strokes as simple data, handle button-press, motion-notify, and '
            'button-release events for drawing, call queue_draw after edits, '
            'draw with cairo in the draw callback, and save the stroke data '
            'through write_file.'
        ),
        tags=('cairo', 'canvas', 'drawing', 'example'),
    ),
    RagDocument(
        title='Two learner turn-taking pattern',
        text=(
            'For paired activities, keep active_student or active_team in '
            'state, provide visible controls for Student A and Student B or '
            'Team A and Team B, include a Switch Turn action, color-code or '
            'label each learner contribution, and save the shared artifact '
            'plus the explanation in the Journal.'
        ),
        tags=('collaboration', 'pair', 'turns', 'two learners'),
    ),
    RagDocument(
        title='Grid activity pattern',
        text=(
            'Use Gtk.Grid with buttons or toggles. Keep state separate from '
            'widgets so it can be serialized to the Journal.'
        ),
        tags=('grid', 'logic', 'example'),
    ),
    RagDocument(
        title='Carrom board activity pattern',
        text=(
            'A carrom activity should use a square visual board with four '
            'corner pockets, visible white and black coins, a queen, a '
            'striker or aim marker, two-player turn taking, score and foul '
            'state, immediate shot feedback, and Journal persistence for '
            'the match state.'
        ),
        tags=('board', 'carrom', 'game', 'turns', 'score'),
    ),
    RagDocument(
        title='Chess board activity pattern',
        text=(
            'Use an 8x8 Gtk.Grid of buttons for the board. Keep board state '
            'as piece codes, track whose turn it is, validate basic moves, '
            'show move feedback, maintain a move log, and persist the board '
            'through write_file and read_file.'
        ),
        tags=('board', 'chess', 'game', 'grid', 'turns'),
    ),
    RagDocument(
        title='Narrative activity pattern',
        text=(
            'Use Gtk.TextView inside Gtk.ScrolledWindow. Read text through '
            'the TextBuffer bounds and persist it as UTF-8.'
        ),
        tags=('narrative', 'story', 'writing', 'example'),
    ),
    RagDocument(
        title='Quiz activity pattern',
        text=(
            'Keep questions as structured dictionaries. Show one question '
            'at a time, accept an answer, provide feedback, and persist '
            'progress and score.'
        ),
        tags=('assessment', 'quiz', 'example'),
    ),
    RagDocument(
        title='Utility activity pattern',
        text=(
            'A utility should solve one understandable problem. Keep its '
            'inputs visible, update results immediately, and persist the '
            'learner-owned input.'
        ),
        tags=('tool', 'utility', 'example'),
    ),
    RagDocument(
        title='sugargame / pygame activity pattern',
        text=(
            'sugargame wraps pygame so it runs inside a Sugar GTK3 window. '
            'Use it ONLY when the activity needs a continuous game loop — '
            'real-time arcade games, physics simulations, or frame-by-frame '
            'animation that cannot be driven by GTK signals.\n\n'
            'Structure for a sugargame activity:\n'
            '  import sugargame.canvas\n'
            '  import pygame\n'
            '  from sugar3.activity import activity\n'
            '  class GeneratedActivity(activity.Activity):\n'
            '      def __init__(self, handle):\n'
            '          super().__init__(handle)\n'
            '          self._canvas = sugargame.canvas.PygameCanvas(\n'
            '              self, main=self._game_loop,\n'
            '              modules=[pygame.display, pygame.font])\n'
            '          self.set_canvas(self._canvas)\n'
            '          self.show_all()\n'
            '          self._canvas.run_pygame(self._game_loop)\n'
            '      def _game_loop(self):\n'
            '          pygame.display.set_caption("Activity")\n'
            '          clock = pygame.time.Clock()\n'
            '          running = True\n'
            '          while running:\n'
            '              for event in pygame.event.get():\n'
            '                  if event.type == pygame.QUIT:\n'
            '                      running = False\n'
            '              # update + draw\n'
            '              pygame.display.flip()\n'
            '              clock.tick(30)\n'
            '      def read_file(self, file_path): pass\n'
            '      def write_file(self, file_path): pass\n\n'
            'Still use the Sugar ToolbarBox and Journal persistence. '
            'For everything else — board games, drawing, quizzes, writing — '
            'use GTK3 + cairo instead; it integrates better with Sugar.'
        ),
        tags=('game', 'pygame', 'sugargame', 'arcade', 'animation', 'loop'),
    ),
    RagDocument(
        title='sugar-toolkit-gtk3 preferred APIs',
        text=(
            'Always prefer sugar3 / sugar-toolkit-gtk3 wrappers over raw '
            'GTK equivalents:\n'
            '- sugar3.graphics.style.zoom(n): DPI-aware pixel sizes\n'
            '- sugar3.graphics.style.COLOR_*: Sugar palette colors\n'
            '- sugar3.graphics.style.FONT_SIZE: standard body font size\n'
            '- sugar3.graphics.toolbutton.ToolButton(icon_name): toolbar '
            'icon button with set_tooltip_text()\n'
            '- sugar3.graphics.alert.NotifyAlert / ConfirmationAlert: '
            'in-activity banners instead of Gtk.Dialog\n'
            '- sugar3.graphics.icon.Icon(icon_name, pixel_size): Sugar icon\n'
            '- sugar3.graphics.toolbarbox.ToolbarBox: the standard toolbar\n'
            '- sugar3.activity.widgets.ActivityToolbarButton: title + share\n'
            '- sugar3.activity.widgets.StopButton: the stop/close button\n'
            'Only fall back to plain Gtk when no Sugar wrapper exists.'
        ),
        tags=('api', 'sugar3', 'sugar-toolkit-gtk3', 'toolkit', 'style'),
    ),
)
