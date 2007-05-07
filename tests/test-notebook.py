#!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com)
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

import pygtk
pygtk.require('2.0')
import gtk

from sugar.graphics.notebook import Notebook

window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())

nb = Notebook()
window.add(nb)

button1 = gtk.Button('Example 1')
button2 = gtk.Button('Example 2')
button3 = gtk.Button('Example 3')

nb.add_page('Testing label 1', button1)
nb.add_page('Testing label 2', button2)
nb.add_page('Testing label 3', button3)

window.show_all()
gtk.main()
