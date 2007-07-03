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

class _ServiceParser(ConfigParser):
    def optionxform(self, option):
        return option

def write_service(name, bin, path):
    """Write a D-BUS service definition file 
    
    These are written by the bundleregistry when 
    a new activity is registered.  They bind a 
    D-BUS bus-name with an executable which is 
    to provide the named service.
    
    name -- D-BUS service name, must be a valid 
        filename/D-BUS name
    bin -- executable providing named service 
    path -- directory into which to write the 
        name.service file
    
    The service files themselves are written using 
    the _ServiceParser class, which is a subclass 
    of the standard ConfigParser class.
    """
    service_cp = _ServiceParser()
    section = 'D-BUS Service'    
    service_cp.add_section(section)
    service_cp.set(section, 'Name', name)
    service_cp.set(section, 'Exec', bin)

    dest_filename = os.path.join(path, name + '.service')
    fileobject = open(dest_filename, 'w')
    service_cp.write(fileobject)
    fileobject.close()

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

def choose_most_significant_mime_type(mime_types):
    logging.debug('Choosing between %r.' % mime_types)
    if not mime_types:
        return ''

    if 'text/uri-list' in mime_types:
        return 'text/uri-list'

    for mime_category in ['image/', 'text/', 'application/']:
        for mime_type in mime_types:
            if mime_type.startswith(mime_category) and \
                    not mime_type.split('/')[1].startswith('_'):
                mime_type = mime_type.split(';')[0]
                logging.debug('Choosed %r!' % mime_type)
                return mime_type

    if 'STRING' in mime_types:
        return 'text/plain'

    logging.debug('Returning first: %r.' % mime_types[0])
    return mime_types[0]

