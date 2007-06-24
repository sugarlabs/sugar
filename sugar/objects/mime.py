# Copyright (C) 2006-2007, Red Hat, Inc.
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

try:
    from sugar import _sugarext
except ImportError:
    from sugar import ltihooks
    from sugar import _sugarext

def get_for_file(file_name):
    return _sugarext.get_mime_type_for_file(file_name)
        
def get_from_file_name(file_name):
    return _sugarext.get_mime_type_from_file_name(file_name)

_extensions_cache = {}
def get_primary_extension(mime_type):
    if _extensions_cache.has_key(mime_type):
        return _extensions_cache[mime_type]

    f = open('/etc/mime.types')
    while True:
        line = f.readline()
        cols = line.replace('\t', ' ').split(' ')
        if mime_type == cols[0]:
            for col in cols[1:]:
                if col:
                    _extensions_cache[mime_type] = col
                    return col

    _extensions_cache[mime_type] = None
    return None
