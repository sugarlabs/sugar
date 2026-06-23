# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
import os
import tempfile

from jarabe.model.aodrag import build_corpus
from jarabe.model.aodrag import RagDocument
from jarabe.model.aodrag import search


class TestAodRag(unittest.TestCase):

    def test_search_ranks_relevant_document_first(self):
        corpus = [
            RagDocument(
                'Drawing example',
                'Gtk.DrawingArea stores learner strokes.',
                ('canvas', 'drawing'),
            ),
            RagDocument(
                'Writing example',
                'Gtk.TextView stores a learner story.',
                ('narrative', 'writing'),
            ),
        ]
        results = search(
            'draw a canvas picture',
            template='canvas',
            corpus=corpus,
        )
        self.assertEqual('Drawing example', results[0].title)

    def test_build_corpus_includes_manifest_and_support_sources(self):
        with tempfile.TemporaryDirectory() as root:
            bundle = os.path.join(root, 'PairDraw.activity')
            os.makedirs(os.path.join(bundle, 'activity'))
            with open(os.path.join(bundle, 'activity', 'activity.info'),
                      'w', encoding='utf-8') as info_file:
                info_file.write(
                    '[Activity]\n'
                    'name = Pair Draw\n'
                    'exec = sugar-activity3 activity.GeneratedActivity\n'
                    'summary = Students draw together.\n'
                    'tags = Drawing\n'
                )
            with open(os.path.join(bundle, 'activity.py'),
                      'w', encoding='utf-8') as source_file:
                source_file.write(
                    'from sugar3.activity import activity\n'
                    'from gi.repository import Gtk\n'
                    'class GeneratedActivity(activity.Activity):\n'
                    '    pass\n'
                )
            with open(os.path.join(bundle, 'widgets.py'),
                      'w', encoding='utf-8') as support_file:
                support_file.write('from gi.repository import Gtk\n')

            corpus = build_corpus(activity_roots=(root,))

        titles = [document.title for document in corpus]
        self.assertIn('PairDraw.activity activity.info manifest', titles)
        self.assertIn('PairDraw.activity main Sugar source example', titles)
        self.assertIn(
            'PairDraw.activity supporting GTK source: widgets.py',
            titles,
        )

    def test_build_corpus_skips_generated_aod_bundles(self):
        with tempfile.TemporaryDirectory() as root:
            bundle = os.path.join(root, 'Generated.activity')
            os.makedirs(os.path.join(bundle, 'activity'))
            with open(os.path.join(bundle, 'aod_plan.json'),
                      'w', encoding='utf-8') as plan_file:
                plan_file.write('{}\n')
            with open(os.path.join(bundle, 'activity', 'activity.info'),
                      'w', encoding='utf-8') as info_file:
                info_file.write(
                    '[Activity]\n'
                    'name = Generated\n'
                    'exec = sugar-activity3 activity.GeneratedActivity\n'
                )
            with open(os.path.join(bundle, 'activity.py'),
                      'w', encoding='utf-8') as source_file:
                source_file.write('class GeneratedActivity: pass\n')

            corpus = build_corpus(activity_roots=(root,))

        titles = [document.title for document in corpus]
        self.assertNotIn('Generated.activity main Sugar source example',
                         titles)
