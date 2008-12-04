# Copyright (C) 2007, 2008 One Laptop Per Child
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
#
#
# The timezone config is based on the system-config-date
# (http://fedoraproject.org/wiki/SystemConfig/date) tool.
# Parts of the code were reused.
#

import os
from gettext import gettext as _

from sugar import profile

_zone_tab = '/usr/share/zoneinfo/zone.tab'

def _initialize():
    '''Initialize the docstring of the set function'''
    if set_timezone.__doc__ is None:
        # when running under 'python -OO', all __doc__ fields are None,
        # so += would fail -- and this function would be unnecessary anyway.
        return
    timezones = read_all_timezones()    
    for timezone in timezones:
        set_timezone.__doc__ += timezone + '\n'                        
                
def read_all_timezones(fn=_zone_tab):
    fd = open (fn, 'r')
    lines = fd.readlines()
    fd.close()
    timezones = []
    for line in lines:
        if line.startswith('#'):
            continue
        line = line.split()
        if len(line) > 1:
            timezones.append(line[2])
    timezones.sort()
   
    for offset in xrange(-12, 13):
        if offset < 0:
            tz = 'GMT%d' % offset
        elif offset > 0:
            tz = 'GMT+%d' % offset
        else:
            tz = 'GMT'
        timezones.append(tz)    
    for offset in xrange(-12, 13):
        if offset < 0:
            tz = 'UTC%d' % offset
        elif offset > 0:
            tz = 'UTC+%d' % offset
        else:
            tz = 'UTC'
        timezones.append(tz)    
    return timezones

def get_timezone():
    pro = profile.get_profile()    
    return pro.timezone

def print_timezone():
    print get_timezone()

def set_timezone(timezone):
    """Set the system timezone
    timezone : e.g. 'America/Los_Angeles'
    """
    timezones = read_all_timezones()
    if timezone in timezones:
        os.environ['TZ'] = timezone
        pro = profile.get_profile()
        pro.timezone = timezone
        pro.save()
    else:
        raise ValueError(_("Error timezone does not exist."))
    return 1

# inilialize the docstrings for the timezone 
_initialize()

