# Copyright (C) 2007, Red Hat, Inc.
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


def bytes_to_string(bytes):
    """The function converts a  D-BUS byte array provided by dbus to string format.
    
    bytes -- a D-Bus array of bytes. Handle both DBus byte arrays and strings
    
    """
    try:
        # DBus Byte array
        ret = ''.join([chr(item) for item in bytes])
    except TypeError:
        # Python string
        ret = ''.join([str(item) for item in bytes])
    return ret
