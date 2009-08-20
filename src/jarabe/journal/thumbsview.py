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
import gobject
import logging
import hippo

from jarabe.journal.browse.lazymodel import Source
from jarabe.journal.browse.tableview import TableView, TableCell

class ThumbsCell(TableCell, hippo.CanvasBox):
    def __init__(self):
        TableCell.__init__(self)
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_VERTICAL)

        label = hippo.CanvasWidget(widget=gtk.Button('!!!'))
        self.append(label)

class ThumbsView(TableView):
    __gsignals__ = {
            'detail-clicked': (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                              ([object])),
            }

    def __init__(self):
        TableView.__init__(self, ThumbsCell, 3, 3)
