#!/bin/env python

import gtk
import unittest
import logging
import gobject
import glib

import gobject
gobject.threads_init()

from jarabe.journal.browse.lazymodel import Source, LazyModel, Row

TIMEOUT = 100

class FakeSource(Source):
    def __init__(self):
        self.count = 9
        Source.__init__(self)
        self.stat = [0] * self.get_count()
        self.delayed_stat = [0] * self.get_count()
        self.delayed = False

    def get_count(self):
        return self.count

    def get_row(self, offset):
        if not self.delayed:
            self.stat[offset] += 1
            return {'f': offset}

        def timeout_cb():
            self.delayed_stat[offset] += 1
            self.emit('row-delayed-fetch', offset, {'f': offset})
            return False

        gobject.timeout_add(TIMEOUT, timeout_cb)

    def get_columns(self):
        return ['f']

    def get_order(self):
        return ('f', gtk.SORT_ASCENDING)

    def set_order(self, field_name, sort_type):
        pass

class FakeView:
    def set_model(self, model):
        if model:
            self.frame = (0, model.source.get_count()-1)

    def get_visible_range(self):
        return ((self.frame[0],), (self.frame[1],))

    def get_cursor(self):
        return None

class CalcModel(LazyModel):
    def __init__(self, fields, calced_fields):
        LazyModel.__init__(self, fields, calced_fields)

    def set_source(self, source, force=False):
        if source:
            self.stat = [0] * source.get_count()
        LazyModel.set_source(self, source, force)

    def on_calc_value(self, row, column):
        self.stat[row.path[0]] += 1
        return -row.path[0]

class TestLazyModel(unittest.TestCase):
    def test_per_row_fetch(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        for i in range(9):
            model.view.frame = (i, i+2)
            for j in range(3):
                self.assertEqual((i+j) < 9 and i+j or 0, model.get_value(model.get_iter((i+j,)), 0))
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.stat)

        for i in range(3):
            self.assertEqual(0, model.get_value(model.get_iter((9+i,)), 0))
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.stat)

        for i in range(8, -1, -1):
            model.view.frame = (i, i+2)
            for j in range(3):
                self.assertEqual((i+j) < 9 and i+j or 0, model.get_value(model.get_iter((i+j,)), 0))
        self.assertEqual([2, 2, 2, 2, 2, 2, 1, 1, 1], model.source.stat)

    def test_per_page_fetch(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        for page in range(3):
            i = page*3
            model.view.frame = (i, i+2)
            for j in range(3):
                self.assertEqual((i+j) < 9 and i+j or 0, model.get_value(model.get_iter((i+j,)), 0))
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.stat)

        for page in range(2, -1, -1):
            i = page*3
            model.view.frame = (i, i+2)
            for j in range(3):
                self.assertEqual((i+j) < 9 and i+j or 0, model.get_value(model.get_iter((i+j,)), 0))
        self.assertEqual([2, 2, 2, 2, 2, 2, 1, 1, 1], model.source.stat)

    def test_subframe_fetch(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        for i in range(9):
            self.assertEqual(i, model.get_value(model.get_iter((i,)), 0))
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.stat)

        for i in range(4):
            model.view.frame = (i+1, 9-i-1)
            for j in range(model.view.frame[0], model.view.frame[1]+1):
                self.assertEqual(j, model.get_value(model.get_iter((j,)), 0))
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.stat)

    def test_delayed_fetch(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        model.source.delayed = True
        stat_signal = []

        def row_changed_cb(sender, path, iter):
            stat_signal.append(path)

        model.connect('row-changed', row_changed_cb)

        for i in range(9):
            self.assertEqual(None, model.get_row((i,)))
        run_timed(TIMEOUT*18)
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.delayed_stat)
        self.assertEqual(9, len(stat_signal))

        for i in range(9):
            self.assertEqual(None, model.get_row((i,)))
        run_timed(TIMEOUT*18)
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([2, 2, 2, 2, 2, 2, 2, 2, 2], model.source.delayed_stat)
        self.assertEqual(18, len(stat_signal))

        model.source.delayed = False

        for i in range(9):
            self.assertEqual(i, model.get_value(model.get_iter((i,)), 0))
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.stat)
        self.assertEqual([2, 2, 2, 2, 2, 2, 2, 2, 2], model.source.delayed_stat)

        model.source.delayed = True

        for i in range(9):
            self.assertEqual((i,), model.get_row((i,)).path)
        run_timed(TIMEOUT*18)
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.source.stat)
        self.assertEqual([2, 2, 2, 2, 2, 2, 2, 2, 2], model.source.delayed_stat)
        self.assertEqual(18, len(stat_signal))

    def test_calced_cache(self):
        model = CalcModel({'f': (0, int)}, {'f2': (1, int)})
        model.set_source(FakeSource())
        model.view = FakeView()

        for trying in range(9):
            for i in range(9):
                self.assertEqual(-i, model.get_value(model.get_iter((i,)), 1))

        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1, 1], model.stat)

    def test_fast_scroll(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        model.source.delayed = True

        for page in range(3):
            i = page*3
            for j in range(3):
                self.assertEqual(None, model.get_row((i+j,), (i, i+2)))

        run_timed(TIMEOUT*18)

        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([1, 0, 0, 0, 0, 0, 1, 1, 1], model.source.delayed_stat)

    def test_mutlty_request(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        model.source.delayed = True

        for trying in range(3):
            self.assertEqual(None, model.get_row((0,)))
        run_timed(TIMEOUT*16)
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([3, 0, 0, 0, 0, 0, 0, 0, 0], model.source.delayed_stat)

        for trying in range(3):
            self.assertEqual(None, model.get_row((0,), (0, 8)))
        run_timed(TIMEOUT*6)
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([4, 0, 0, 0, 0, 0, 0, 0, 0], model.source.delayed_stat)

        for trying in range(3):
            self.assertEqual(0, model.get_row((0,)).path[0])
        run_timed(TIMEOUT*6)
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([4, 0, 0, 0, 0, 0, 0, 0, 0], model.source.delayed_stat)

    def test_fast_scroll_plus_back_scroll(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        def row_changed_cb(sender, path, iter):
            signals.append(path[0])
        model.connect('row-changed', row_changed_cb)

        model.source.delayed = True
        signals = []

        for page in range(3):
            i = page*3
            for j in range(3):
                self.assertEqual(None, model.get_row((i+j,), (i, i+2)))
        run_timed(TIMEOUT*18)
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([1, 0, 0, 0, 0, 0, 1, 1, 1], model.source.delayed_stat)
        self.assertEqual([0, 6, 7, 8], signals.sort() or signals)

        signals = []

        for page in reversed(range(2)):
            i = page*3
            for j in range(3):
                self.assertEqual(None, model.get_row((i+j,), (i, i+2)))
            run_timed(TIMEOUT*6)
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], model.source.stat)
        self.assertEqual([2, 1, 1, 1, 1, 1, 1, 1, 1], model.source.delayed_stat)
        self.assertEqual([0, 1, 2, 3, 4, 5], signals.sort() or signals)

    def test_refresh(self):
        model = LazyModel({'f': (0, int)})
        model.source = FakeSource()
        model.view = FakeView()

        def row_cb(sender, path, iter, type):
            signals[type].append(path[0])
        model.connect('row-changed', row_cb, 0)
        model.connect('row-deleted', row_cb, None, 1)
        model.connect('row-inserted', row_cb, 2)

        signals = [[], [], []]

        model.refresh()
        run_timed(TIMEOUT*18)
        self.assertEqual([[], [], []], signals)

        signals = [[], [], []]

        model.view.frame = (3, 5)
        for i in range(*model.view.frame):
            self.assertEqual(i, model.get_value(model.get_iter((i,)), 0))
        model.refresh()
        run_timed(TIMEOUT*6)
        self.assertEqual([[3, 4, 5], [], []], signals)

        signals = [[], [], []]

        model.source.count = 12
        model.refresh()
        run_timed(TIMEOUT*12)
        self.assertEqual([[3, 4, 5], [], [9, 10, 11]], signals)

        signals = [[], [], []]

        model.source.count = 9
        model.refresh()
        run_timed(TIMEOUT*12)
        self.assertEqual([[3, 4, 5], [11, 10, 9], []], signals)

        signals = [[], [], []]

        model.source.count = 5
        model.refresh()
        run_timed(TIMEOUT*12)
        self.assertEqual([[3, 4], [8, 7, 6, 5], []], signals)

        signals = [[], [], []]

        model.source.count = 3
        model.refresh()
        run_timed(TIMEOUT*4)
        self.assertEqual([[], [4, 3], []], signals)

def run_timed(timeout):
    def _timeout_cb():
        gtk.main_quit()
        return False
    gobject.timeout_add(timeout, _timeout_cb)
    gtk.main()

if __name__ == '__main__':
    unittest.main()
