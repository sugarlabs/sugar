# Copyright (C) 2007, Red Hat, Inc.
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

import gtk

from sugar.graphics.toolbutton import ToolButton

class Test(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)

class TestPalette(Test):
    def __init__(self):
        Test.__init__(self)

        toolbar = gtk.Toolbar()

        button = ToolButton('stop')
        toolbar.insert(button, -1)
        button.show()

        self.pack_start(toolbar, False)
        toolbar.show()

class TestRunner(object):
    def run(self, test):
        window = gtk.Window()
        window.connect("destroy", lambda w: gtk.main_quit())
        window.add(test)
        test.show()

        window.show()

def main(test):
    runner = TestRunner()
    runner.run(test)

    gtk.main()
