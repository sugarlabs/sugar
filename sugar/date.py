"""Simple date-representation model"""

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

import datetime

class Date(object):
    """Date-object storing a simple time.time() float

       Useful to display dates in the UI in an
       abbreviated and easy to read format.
    """
    def __init__(self, timestamp):
        """Initialise via a timestamp (floating point value)"""
        self._today = datetime.date.today()
        self._timestamp = timestamp

    def __str__(self):
        """Produce a formatted date representation
        
        Eventually this should produce a localised version 
        of the date.  At the moment it always produces English
        dates in long form with Today and Yesterday 
        special-cased and dates from this year not presenting
        the year in the date.
        """
        date = datetime.date.fromtimestamp(self._timestamp)

        # FIXME localization
        if date == self._today:
            result = 'Today'
        elif date == self._today - datetime.timedelta(1):
            result = 'Yesterday'
        elif date.year == self._today.year:
            result = date.strftime('%B %d')
        else:
            result = date.strftime('%B %d, %Y')

        time = datetime.datetime.fromtimestamp(self._timestamp)
        result = result + ', ' + time.strftime('%I:%M %p')

        return result
