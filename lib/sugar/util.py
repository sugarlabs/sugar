"""Various utility functions"""
# Copyright (C) 2006-2007 Red Hat, Inc.
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
import os
import logging

from ConfigParser import ConfigParser
from ConfigParser import NoOptionError

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
    """Generate a likely-unique ID for whatever purpose
    
    data -- suffix appended to working data before hashing
    
    Returns a 40-character string with hexidecimal digits
    representing an SHA hash of the time, a random digit 
    within a constrained range and the data passed.
    
    Note: these are *not* crypotographically secure or 
        globally unique identifiers.  While they are likely 
        to be unique-enough, no attempt is made to make 
        perfectly unique values.
    """
    data_string = "%s%s%s" % (time.time(), random.randint(10000, 100000), data)
    return printable_hash(_sha_data(data_string))


ACTIVITY_ID_LEN = 40

def is_hex(s):
    return s.strip(string.hexdigits) == ''    

def validate_activity_id(actid):
    """Validate an activity ID."""
    if not isinstance(actid, (str,unicode)):
        return False
    if len(actid) != ACTIVITY_ID_LEN:
        return False
    if not is_hex(actid):
        return False
    return True

def set_proc_title(title):
    """Sets the process title so ps and top show more
       descriptive names.  This does not modify argv[0]
       and only the first 15 characters will be shown.

       title -- the title you wish to change the process
                title to 

       Returns True on success.  We don't raise exceptions
       because if something goes wrong here it is not a big
       deal as this is intended as a nice thing to have for
       debugging
    """
    try:
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        libc.prctl(15, str(title), 0, 0, 0)

        return True
    except:
        return False

class Node(object):
    __slots__ = ['prev', 'next', 'me']
    def __init__(self, prev, me):
        self.prev = prev
        self.me = me
        self.next = None

class LRU:
    """
    Implementation of a length-limited O(1) LRU queue.
    Built for and used by PyPE:
    http://pype.sourceforge.net
    Copyright 2003 Josiah Carlson.
    """
    def __init__(self, count, pairs=[]):
        self.count = max(count, 1)
        self.d = {}
        self.first = None
        self.last = None
        for key, value in pairs:
            self[key] = value
    def __contains__(self, obj):
        return obj in self.d
    def __getitem__(self, obj):
        a = self.d[obj].me
        self[a[0]] = a[1]
        return a[1]
    def __setitem__(self, obj, val):
        if obj in self.d:
            del self[obj]
        nobj = Node(self.last, (obj, val))
        if self.first is None:
            self.first = nobj
        if self.last:
            self.last.next = nobj
        self.last = nobj
        self.d[obj] = nobj
        if len(self.d) > self.count:
            if self.first == self.last:
                self.first = None
                self.last = None
                return
            a = self.first
            a.next.prev = None
            self.first = a.next
            a.next = None
            del self.d[a.me[0]]
            del a
    def __delitem__(self, obj):
        nobj = self.d[obj]
        if nobj.prev:
            nobj.prev.next = nobj.next
        else:
            self.first = nobj.next
        if nobj.next:
            nobj.next.prev = nobj.prev
        else:
            self.last = nobj.prev
        del self.d[obj]
    def __iter__(self):
        cur = self.first
        while cur != None:
            cur2 = cur.next
            yield cur.me[1]
            cur = cur2
    def iteritems(self):
        cur = self.first
        while cur != None:
            cur2 = cur.next
            yield cur.me
            cur = cur2
    def iterkeys(self):
        return iter(self.d)
    def itervalues(self):
        for i,j in self.iteritems():
            yield j
    def keys(self):
        return self.d.keys()
