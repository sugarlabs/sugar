#!/bin/env python
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
import random

from jarabe.journal.browse.smoothtable import SmoothTable

window = gtk.Window()

scrolled = gtk.ScrolledWindow()
scrolled.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)
window.add(scrolled)

def do_fill_in(cell, row, column):
    cell.props.label = '%s:%s' % (row, column)
table = SmoothTable(3, 3, gtk.Button, do_fill_in)
table.bin_rows = 100
scrolled.add(table)

for row in table._rows:
    for cell in row:
        cell.connect('clicked',
                lambda button: table.goto(random.randint(0, 100)))

window.show_all()
gtk.main()
