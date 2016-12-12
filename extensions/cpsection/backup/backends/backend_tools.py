# Copyright (C) 2013, Martin Abente Lahaye - tch@sugarlabs.org
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

import os

from gi.repository import GObject


def get_valid_file_name(file_name):
    # Invalid characters in VFAT filenames. From
    # http://en.wikipedia.org/wiki/File_Allocation_Table
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x7F']
    invalid_chars.extend([chr(x) for x in range(0, 32)])
    for char in invalid_chars:
        file_name = file_name.replace(char, '_')

    # FAT limit is 255, leave some space for uniqueness
    max_len = 250
    if len(file_name) > max_len:
        name, extension = os.path.splitext(file_name)
        file_name = name[0:max_len - len(extension)] + extension

    return file_name


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
        'started': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'progress': (GObject.SignalFlags.RUN_FIRST, None, ([float])),
        'finished': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'cancelled': (GObject.SignalFlags.RUN_FIRST, None, ([]))}

    def verify_preconditions(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()
