# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import time
import sha
import random
import binascii
import string

import gobject

class GObjectSingletonMeta(gobject.GObjectMeta):
    """GObject Singleton Metaclass"""

    def __init__(klass, name, bases, dict):
        gobject.GObjectMeta.__init__(klass, name, bases, dict)
        klass.__instance = None

    def __call__(klass, *args, **kwargs):
        if klass.__instance is None:
            klass.__instance = gobject.GObjectMeta.__call__(klass, *args, **kwargs)
        return klass.__instance

def printable_hash(in_hash):
	"""Convert binary hash data into printable characters."""
	printable = ""
	for char in in_hash:
		printable = printable + binascii.b2a_hex(char)
	return printable

def _sha_data(data):
	"""sha1 hash some bytes."""
	sha_hash = sha.new()
	sha_hash.update(data)
	return sha_hash.digest()

def unique_id(data = ''):
	data_string = "%s%s%s" % (time.time(), random.randint(10000, 100000), data)
	return printable_hash(_sha_data(data_string))


ACTIVITY_ID_LEN = 40

def is_hex(s):
	return s.strip(string.hexdigits) == ''	

def validate_activity_id(actid):
	"""Validate an activity ID."""
	if not isinstance(actid, str) and not isinstance(actid, unicode):
		return False
	if len(actid) != ACTIVITY_ID_LEN:
		return False
	if not is_hex(actid):
		return False
	return True

