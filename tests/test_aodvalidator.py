# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodtemplates import render_activity_source
from jarabe.model.aodgenerator import enrich_plan
from jarabe.model.aodvalidator import validate_activity_source_for_request
from jarabe.model.aodvalidator import validate_source


class TestAodValidator(unittest.TestCase):

    def test_rejects_syntax_errors(self):
        report = validate_source('class Broken(:\n    pass\n')
        self.assertFalse(report.valid)
        self.assertIn('Python syntax error', report.errors[0])

    def test_rejects_dangerous_imports_and_calls(self):
        report = validate_source(
            'import subprocess\n'
            'eval("1 + 1")\n'
        )
        self.assertFalse(report.valid)
        self.assertIn('Forbidden import: subprocess', report.errors)
        self.assertIn('Forbidden call: eval', report.errors)

    def test_requires_activity_structure(self):
        report = validate_source('class PlainObject:\n    pass\n')
        self.assertFalse(report.valid)
        self.assertIn(
            'Generated source must define exactly one Activity subclass.',
            report.errors,
        )

    def test_rejects_invented_toolbar_and_adjustment_apis(self):
        spec = ActivitySpec(
            'Counter',
            'Make a counter utility.',
            'tools_utils',
            'MIT',
        )
        plan = enrich_plan(spec, {'template': 'utility'})
        source = render_activity_source(spec, plan)
        source = source.replace(
            'toolbar.insert(ActivityToolbarButton(self), 0)',
            'toolbar_box.add_toolbar_button(ActivityToolbarButton(self))',
        )
        source = source.replace(
            'self.set_canvas(canvas)',
            'adjustment.set_bounds(0, 10)\n        self.set_canvas(canvas)',
        )

        report = validate_source(source)

        self.assertFalse(report.valid)
        self.assertTrue(any(
            'add_toolbar_button' in error for error in report.errors
        ))
        self.assertTrue(any(
            'set_bounds' in error for error in report.errors
        ))

    def test_request_validation_rejects_generic_source_for_drawing(self):
        spec = ActivitySpec(
            'Draw Together',
            'Make an activity where two students can draw together.',
            'creation',
            'MIT',
        )
        plan = enrich_plan(spec, {
            'template': 'narrative',
            'summary': 'A writing activity.',
            'learner_goal': 'Write together.',
            'learner_steps': ['Write', 'Share'],
        })
        source = render_activity_source(spec, plan)

        report = validate_activity_source_for_request(source, spec, plan)

        self.assertFalse(report.valid)
        self.assertTrue(any(
            'Drawing requests must use' in error
            for error in report.errors
        ))

    def test_request_validation_accepts_real_canvas_for_drawing(self):
        spec = ActivitySpec(
            'Draw Together',
            'Make an activity where two students can draw together.',
            'creation',
            'MIT',
        )
        plan = enrich_plan(spec, {
            'template': 'canvas',
            'summary': 'A drawing activity for Student A and Student B.',
            'learner_goal': 'Students draw together.',
            'learner_steps': ['Student A draws', 'Student B draws'],
            'interaction_model': 'Students switch turns and draw together.',
        })
        source = render_activity_source(spec, plan)
        source += '\n# Student A and Student B switch turns together.\n'

        report = validate_activity_source_for_request(source, spec, plan)

        self.assertTrue(report.valid, report.errors)
