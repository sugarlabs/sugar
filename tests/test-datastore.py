#!/usr/bin/env python
# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import unittest
from sugar.datastore import datastore
from sugar import util
import dbus

class NotFoundError(dbus.DBusException): pass

_ds = datastore.get_instance()

class DataStoreTestCase(unittest.TestCase):
    _TEST_DATA = "adsfkjadsfadskjasdkjf"
    _TEST_PROPS = {'foo': 1, 'bar': 'baz'}
    def _create_test_object(self, activity_id=None):
        obj = _ds.create(self._TEST_DATA, self._TEST_PROPS, activity_id=activity_id)
        self.assert_(obj)
        return obj

    def testObjectCreate(self):
        obj = self._create_test_object()
        self.assert_(obj.uid())
        _ds.delete(obj)

    def testObjectCreateWithActivityId(self):
        # Try known good create
        act_id = util.unique_id('afdkjakjddasf')
        obj = self._create_test_object(act_id)
        self.assert_(obj.uid())
        _ds.delete(obj)

    def testObjectCreateWithBadActivityId(self):
        # try malformed activity id
        try:
            uid = self._create_test_object("adfadf")
        except ValueError:
            pass
        else:
            self.fail("Expected ValueError")

    def testObjectGetActivityObject(self):
        # create a new object
        act_id = util.unique_id('afdkjakjddasf')
        obj = self._create_test_object(act_id)
        self.assert_(obj.uid())
        obj2 = _ds.get(activity_id=act_id)
        self.assert_(obj2)
        _ds.delete(obj)

    def testObjectGet(self):
        # create a new object
        obj = self._create_test_object()
        self.assert_(obj.uid())
        obj2 = _ds.get(obj.uid())
        self.assert_(obj2)
        _ds.delete(obj)

    def testObjectDelete(self):
        obj = self._create_test_object()
        uid = obj.uid()
        _ds.delete(obj)
        try:
            _ds.get(uid)
        except dbus.DBusException, e:
            if str(e).find("NotFoundError:") < 0:
                self.fail("Expected a NotFoundError")
        else:
            self.fail("Expected a NotFoundError.")

    def testObjectFind(self):
        obj = self._create_test_object()
        found = _ds.find(self._TEST_PROPS)
        self.assert_(obj in found)
        _ds.delete(obj)

    def testObjectGetData(self):
        obj = self._create_test_object()
        data = obj.get_data()
        self.assert_(data == self._TEST_DATA)
        _ds.delete(obj)

    _OTHER_DATA = "532532532532532;lkjkjkjfsakjfakjfdsakj"
    def testObjectSetData(self):
        obj = self._create_test_object()
        data = obj.get_data()
        self.assert_(data == self._TEST_DATA)
        obj.set_data(self._OTHER_DATA)
        data = obj.get_data()
        self.assert_(data == self._OTHER_DATA)
        _ds.delete(obj)

    def testObjectGetProperties(self):
        obj = self._create_test_object()
        props = obj.get_properties()
        for (key, value) in props.items():
            if key == 'uid':
                continue
            self.assert_(key in self._TEST_PROPS)
            self.assert_(str(self._TEST_PROPS[key]) == str(value))
        for (key, value) in self._TEST_PROPS.items():
            self.assert_(key in props)
            self.assert_(str(props[key]) == str(value))
        _ds.delete(obj)

def main():
    dsTestSuite = unittest.TestSuite()
    dsTestSuite.addTest(DataStoreTestCase('testObjectCreate'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectCreateWithActivityId'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectCreateWithBadActivityId'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectGet'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectGetActivityObject'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectDelete'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectFind'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectGetData'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectSetData'))
    dsTestSuite.addTest(DataStoreTestCase('testObjectGetProperties'))
    unittest.TextTestRunner(verbosity=2).run(dsTestSuite)


if __name__ == "__main__":
    main()
