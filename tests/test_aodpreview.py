# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest import mock

from jarabe.model.aodpreview import _add_toolbar_button
from jarabe.model.aodpreview import _set_adjustment_bounds
from jarabe.model.aodpreview import _try_exec_preview


class TestAodPreviewCompatibility(unittest.TestCase):

    def test_toolbar_alias_inserts_at_end(self):
        toolbar_box = mock.Mock()
        item = object()

        _add_toolbar_button(toolbar_box, item)

        toolbar_box.toolbar.insert.assert_called_once_with(item, -1)

    def test_adjustment_alias_sets_both_limits(self):
        adjustment = mock.Mock()

        _set_adjustment_bounds(adjustment, 2, 12)

        adjustment.set_lower.assert_called_once_with(2)
        adjustment.set_upper.assert_called_once_with(12)

    def test_preview_supplies_gettext_fallback(self):
        class FakePreviewActivity:
            def __init__(self, handle=None, bundle_path=''):
                self.canvas = object()

            def get_canvas(self):
                return self.canvas

            def get_toolbar_box(self):
                return None

        source = (
            'class GeneratedActivity(PreviewActivity):\n'
            '    def __init__(self, handle=None):\n'
            '        PreviewActivity.__init__(self, handle)\n'
            '        self.label = _("Hello")\n'
        )

        with mock.patch(
                'jarabe.model.aodpreview.PreviewActivity',
                FakePreviewActivity):
            result = _try_exec_preview(
                source, 'activity.py', '.', 'Preview')

        self.assertIsNotNone(result[0])
        self.assertEqual('Hello', result[0].label)


if __name__ == '__main__':
    unittest.main()
