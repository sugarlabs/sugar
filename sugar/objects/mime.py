# Copyright (C) 2006-2007, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
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

import logging

from sugar import _sugarext

def get_for_file(file_name):
    mime_type = _sugarext.get_mime_type_for_file(file_name)
    if mime_type == 'application/octet-stream':
        if _file_looks_like_text(file_name):
            return 'text/plain'
        else:
            return 'application/octet-stream'
    return mime_type
        
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

def choose_most_significant(mime_types):
    logging.debug('Choosing between %r.' % mime_types)
    if not mime_types:
        return ''

    if 'text/uri-list' in mime_types:
        return 'text/uri-list'

    for mime_category in ['image/', 'application/']:
        for mime_type in mime_types:

            if mime_type.startswith(mime_category):
                # skip mozilla private types (second component starts with '_'
                # or ends with '-priv') 
                if mime_type.split('/')[1].startswith('_') or \
                   mime_type.split('/')[1].endswith('-priv'):
                    continue

                # take out the specifier after ';' that mozilla likes to add
                mime_type = mime_type.split(';')[0]
                logging.debug('Choosed %r!' % mime_type)
                return mime_type

    if 'text/x-moz-url' in mime_types:
        logging.debug('Choosed text/x-moz-url!')
        return 'text/x-moz-url'

    if 'text/html' in mime_types:
        logging.debug('Choosed text/html!')
        return 'text/html'

    if 'text/plain' in mime_types or 'STRING' in mime_types:
        logging.debug('Choosed text/plain!')
        return 'text/plain'

    logging.debug('Returning first: %r.' % mime_types[0])
    return mime_types[0]

def _file_looks_like_text(file_name):
    f = open(file_name, 'r')
    try:
        sample = f.read(256)
    finally:
        f.close()

    if '\000' in sample:
        return False

    for encoding in ('ascii', 'latin_1', 'utf_8', 'utf_16'):
        try:
            string = unicode(sample, encoding)
            return True
        except Exception, e:
            pass

    return False
