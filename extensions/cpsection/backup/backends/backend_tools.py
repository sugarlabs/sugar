# Copyright (C) 2013, Martin Abente Lahaye - tch@sugarlabs.org
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

from gi.repository import GObject


class PreConditionsError(Exception):
    """
    To manage a precondition error exception, the view only show a message
    and restart the process
    """
    pass


class PreConditionsChoose(Exception):
    """
    To manage a precondition choose exception, the view need show options
    to the user and continue process.
    options is a dictionary with structure:
        options = {}
        options['parameter'] = (str) the name of the parameter to request
        options['options'] = []
    """

    def __init__(self, message, options):
        Exception.__init__(self, message)
        self.options = options


class Backend(GObject.GObject):

    __gsignals__ = {
        'started':   (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'progress':  (GObject.SignalFlags.RUN_FIRST, None, ([float])),
        'finished':  (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'cancelled': (GObject.SignalFlags.RUN_FIRST, None, ([]))}

    def verify_preconditions(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()
