# -*- coding: utf-8 -*-
# Copyright (C) 2012 One Laptop Per Child
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

from unicodedata import normalize


def normalize_string(unicode_string):
    u"""Return unicode_string normalized for searching.

    >>> normalize_string(u'Mónica Viñao')
    'monica vinao'

    >>> normalize_string(u'Ábaco')
    'abaco'

    """
    return normalize('NFKD', unicode_string).encode('ASCII', 'ignore').lower()
