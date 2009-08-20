# Copyright (C) 2009, Aleksey Lim
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

import gtk

from jarabe.journal.browse.source import Source

class LocalSource(Source):
    def __init__(self, resultset):
        Source.__init__(self)
        self._resultset = resultset

    def get_count(self):
        return self._resultset.length

    def get_row(self, offset):
        if offset >= self.get_count():
            return False
        self._resultset.seek(offset)
        return self._resultset.read()

    def get_order(self):
        """ Get current order, returns (field_name, gtk.SortType) """
        pass

    def set_order(self, field_name, sort_type):
        """ Set current order """
        pass
