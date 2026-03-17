# Copyright(c) 2007-2010 by Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#              2009-2010 by Yaco S.L. <lgs@yaco.es>
#
# This file is part of PyCha.
#
# PyCha is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyCha is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyCha.  If not, see <http://www.gnu.org/licenses/>.


def clamp(minValue, maxValue, value):
    """Make sure value is between minValue and maxValue"""
    if value < minValue:
        return minValue
    if value > maxValue:
        return maxValue
    return value


def safe_unicode(obj, encoding=None):
    """Return a unicode value from the argument"""
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, str):
        if encoding is None:
            return str(obj)
        else:
            return str(obj, encoding)
    else:
        # it may be an int or a float
        return str(obj)
