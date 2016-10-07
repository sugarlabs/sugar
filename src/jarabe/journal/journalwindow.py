# Copyright (C) 2010 Software for Education, Entertainment and Training
# Activities
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

from sugar3.graphics.window import Window

from gettext import gettext as _

_journal_window = None


class JournalWindow(Window):

    def __init__(self):

        global _journal_window
        Window.__init__(self)
        _journal_window = self
        self.set_icon_name('activity-journal')
        self.set_title(_('Journal'))

        # Stop the user from closing the journal window.
        self.connect('delete-event', lambda widget, event: True)


def get_journal_window():
    return _journal_window
