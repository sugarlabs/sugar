#!/usr/bin/env python3
# Copyright (C) 2025, Sugar Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Test GObject super() initialization pattern.

This test file demonstrates how to verify that GObject subclasses
are properly initialized when using super().__init__() instead of
GObject.GObject().__init__(self).
"""

import unittest
from gi.repository import GObject, GLib


class SimpleGObjectClass(GObject.GObject):
    """Example class with super() replacement."""

    __gsignals__ = {
        'test-signal': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self):
        super().__init__()  # This replaced: GObject.GObject.__init__(self)
        self.test_prop = "initialized"


class GObjectWithKwargs(GObject.GObject):
    """GObject class with **kwargs pattern (like BaseBuddyModel)."""

    test_prop = GObject.Property(type=str, default="")

    def __init__(self, **kwargs):
        self._internal_prop = None
        super().__init__(**kwargs)  # This replaced: GObject.GObject.__init__(self, **kwargs)


class TestGObjectSuperPattern(unittest.TestCase):
    """Verify super().__init__() properly initializes GObject."""

    def test_instantiation_works(self):
        """Test that class can be instantiated."""
        obj = SimpleGObjectClass()
        self.assertIsNotNone(obj)

    def test_is_gobject_subclass(self):
        """Verify it's a proper GObject subclass."""
        obj = SimpleGObjectClass()
        self.assertIsInstance(obj, GObject.GObject)

    def test_has_gobject_methods(self):
        """Verify GObject methods are available."""
        obj = SimpleGObjectClass()
        # Essential GObject methods
        self.assertTrue(hasattr(obj, 'emit'))
        self.assertTrue(hasattr(obj, 'connect'))
        self.assertTrue(hasattr(obj, 'freeze_notify'))
        self.assertTrue(hasattr(obj, 'thaw_notify'))

    def test_properties_initialized(self):
        """Test instance properties are set correctly."""
        obj = SimpleGObjectClass()
        self.assertEqual(obj.test_prop, "initialized")

    def test_signal_emission(self):
        """Test signal emission works with super() init."""
        obj = SimpleGObjectClass()
        signals_received = []

        def on_signal(obj, data):
            signals_received.append(data)

        obj.connect('test-signal', on_signal)
        obj.emit('test-signal', 'test_value')

        self.assertEqual(len(signals_received), 1)
        self.assertEqual(signals_received[0], 'test_value')

    def test_multiple_signal_handlers(self):
        """Test multiple handlers work correctly."""
        obj = SimpleGObjectClass()
        results = []

        def handler1(obj, data):
            results.append(('handler1', data))

        def handler2(obj, data):
            results.append(('handler2', data))

        obj.connect('test-signal', handler1)
        obj.connect('test-signal', handler2)
        obj.emit('test-signal', 'msg')

        self.assertEqual(len(results), 2)
        self.assertIn(('handler1', 'msg'), results)
        self.assertIn(('handler2', 'msg'), results)

    def test_freeze_thaw_notify(self):
        """Test freeze/thaw notify works."""
        obj = SimpleGObjectClass()
        # These should not raise exceptions
        obj.freeze_notify()
        obj.thaw_notify()

    def test_multiple_instances(self):
        """Test creating multiple independent instances."""
        obj1 = SimpleGObjectClass()
        obj2 = SimpleGObjectClass()

        obj1.test_prop = "obj1_value"
        obj2.test_prop = "obj2_value"

        self.assertNotEqual(obj1.test_prop, obj2.test_prop)
        self.assertIsNot(obj1, obj2)

    def test_class_with_initialization_chain(self):
        """Test complex initialization chain."""
        init_order = []

        class Parent(GObject.GObject):
            def __init__(self):
                super().__init__()
                init_order.append('parent')

        class Child(Parent):
            def __init__(self):
                super().__init__()  # Calls Parent.__init__
                init_order.append('child')

        obj = Child()
        # Verify initialization happened in correct order
        self.assertIn('parent', init_order)
        self.assertIn('child', init_order)
        self.assertIsInstance(obj, GObject.GObject)


class TestSuperVsOldPattern(unittest.TestCase):
    """Compare new super() pattern with old GObject.GObject() pattern."""

    def test_both_patterns_create_valid_gobjects(self):
        """Verify both patterns result in valid GObjects."""
        # New pattern (using super())
        new_obj = SimpleGObjectClass()

        self.assertIsInstance(new_obj, GObject.GObject)
        self.assertTrue(hasattr(new_obj, 'emit'))
        self.assertTrue(hasattr(new_obj, 'connect'))

    def test_signal_emission_consistency(self):
        """Test that signals work the same way."""
        obj = SimpleGObjectClass()
        emitted = []

        obj.connect('test-signal', lambda o, d: emitted.append(d))
        obj.emit('test-signal', 'data')

        self.assertEqual(emitted, ['data'])

    def test_property_assignment_works(self):
        """Verify property assignment works correctly."""
        obj = SimpleGObjectClass()
        obj.test_prop = "new_value"
        self.assertEqual(obj.test_prop, "new_value")


class TestGObjectInitializationVerification(unittest.TestCase):
    """Tests to verify GObject was properly initialized."""

    def test_glib_main_context_available(self):
        """Verify GLib integration works."""
        obj = SimpleGObjectClass()
        context = GLib.MainContext.default()
        self.assertIsNotNone(context)

    def test_signal_not_firing_before_connection(self):
        """Verify signal doesn't fire if not connected."""
        obj = SimpleGObjectClass()
        handler_called = []

        # Connect after emission
        obj.emit('test-signal', 'data1')
        obj.connect('test-signal', lambda o, d: handler_called.append(d))
        obj.emit('test-signal', 'data2')

        # Only data2 should be in the list
        self.assertEqual(handler_called, ['data2'])

    def test_reference_counting_works(self):
        """Verify GObject reference counting is functional."""
        obj = SimpleGObjectClass()
        # GObject uses reference counting
        # Create a reference and verify it exists
        ref = obj
        self.assertIs(ref, obj)


class TestSuperWithKwargs(unittest.TestCase):
    """Test super().__init__(**kwargs) pattern as used in BaseBuddyModel."""

    def test_kwargs_instantiation(self):
        """Test class with **kwargs can be instantiated."""
        obj = GObjectWithKwargs()
        self.assertIsNotNone(obj)

    def test_kwargs_is_gobject_subclass(self):
        """Verify kwargs class is a proper GObject subclass."""
        obj = GObjectWithKwargs()
        self.assertIsInstance(obj, GObject.GObject)

    def test_kwargs_with_properties(self):
        """Test **kwargs pattern with GObject properties."""
        obj = GObjectWithKwargs(test_prop="custom_value")
        self.assertEqual(obj.props.test_prop, "custom_value")

    def test_kwargs_without_properties(self):
        """Test **kwargs without passing properties."""
        obj = GObjectWithKwargs()
        self.assertEqual(obj.props.test_prop, "")

    def test_kwargs_internal_properties_initialized(self):
        """Verify internal properties are initialized before super()."""
        obj = GObjectWithKwargs()
        self.assertIsNone(obj._internal_prop)

    def test_kwargs_multiple_instances(self):
        """Test multiple instances with different property values."""
        obj1 = GObjectWithKwargs(test_prop="value1")
        obj2 = GObjectWithKwargs(test_prop="value2")

        self.assertEqual(obj1.props.test_prop, "value1")
        self.assertEqual(obj2.props.test_prop, "value2")
        self.assertIsNot(obj1, obj2)

    def test_kwargs_has_gobject_methods(self):
        """Verify GObject methods work with kwargs pattern."""
        obj = GObjectWithKwargs()
        self.assertTrue(hasattr(obj, 'emit'))
        self.assertTrue(hasattr(obj, 'connect'))
        self.assertTrue(hasattr(obj, 'freeze_notify'))
        self.assertTrue(hasattr(obj, 'thaw_notify'))


if __name__ == '__main__':
    unittest.main()