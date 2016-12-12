# Copyright (C) 2007, 2008 One Laptop Per Child
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
#
#
# The timezone config is based on the system-config-date
# (http://fedoraproject.org/wiki/SystemConfig/date) tool.
# Parts of the code were reused.
#

import os
from gettext import gettext as _
from gi.repository import Gio

_zone_tab = '/usr/share/zoneinfo/zone.tab'


def _initialize():
    """Initialize the docstring of the set function"""
    if set_timezone.__doc__ is None:
        # when running under 'python -OO', all __doc__ fields are None,
        # so += would fail -- and this function would be unnecessary anyway.
        return
    timezones = read_all_timezones()
    for timezone in timezones:
        set_timezone.__doc__ += timezone + '\n'


def read_all_timezones(fn=_zone_tab):
    fd = open(fn, 'r')
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

    for offset in xrange(-12, 15):
        if offset < 0:
            tz = 'UTC%d' % offset
        elif offset > 0:
            tz = 'UTC+%d' % offset
        else:
            tz = 'UTC'
        timezones.append(tz)
    return timezones


def get_timezone():
    settings = Gio.Settings('org.sugarlabs.date')
    return settings.get_string('timezone')


def print_timezone():
    print get_timezone()


def fix_UTC_time_zone(timezone):
    # Fixes the issue where the timezones are
    # wrong when using UTC to set the time.
    # This works by inverting the +/- and using
    # the Etc/GMT... to be POSIX compliant.
    if '+' in timezone:
        new = timezone.replace('+', '-')
    elif '-' in timezone:
        new = timezone.replace('-', '+')
    else:
        new = 'UTC'
    return 'Etc/' + new.replace('UTC', 'GMT')


def set_timezone(timezone):
    """Set the system timezone
    timezone : e.g. 'America/Los_Angeles'
    """
    timezones = read_all_timezones()
    if timezone in timezones:
        if timezone.startswith('UTC'):
            timezone = fix_UTC_time_zone(timezone)
        os.environ['TZ'] = timezone
        settings = Gio.Settings('org.sugarlabs.date')
        settings.set_string('timezone', timezone)
    else:
        raise ValueError(_('Error: timezone does not exist.'))
    return 1

# inilialize the docstrings for the timezone
_initialize()
