#!/usr/bin/env python
# Copyright (C) 2006, One Laptop Per Child
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
from sugar.datastore import datastore
from sugar.datastore.datastore import Text

# Write a text object
metadata = { 'date'    : 1000900000,
             'title'   : 'Thai history',
             'preview' : 'The subject of thai history...',
             'icon-color' : '#C2B00C,#785C78',
           }
text = Text(metadata)
f = open("/tmp/hello.txt", 'w')
try:
    f.write('The subject of thai history blah blah blah, blah blah blah and blah.')
finally:
    f.close()
text.set_file_path(f.name)
handle = datastore.write(text)

# Read back that object
thing = datastore.read(handle)
metadata = thing.get_metadata()
print metadata

file_path = thing.get_file_path()
f = open(file_path)
try:
    print f.read()
finally:
    f.close()

# Retrieve all the objects
objects = datastore.find('')
for obj in objects:
    print obj.get_metadata()['title']
