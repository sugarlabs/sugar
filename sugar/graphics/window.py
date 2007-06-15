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
import hippo

class Window(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self.connect('realize', self._window_realize_cb)

        self.toolbox = None
        self.canvas = None
    
        self._vbox = gtk.VBox()
        self.add(self._vbox)        
        self._vbox.show()

    def set_canvas(self, canvas):
        if self.canvas:
            self._vbox.remove(self.canvas)

        self._vbox.pack_start(canvas)
        self._vbox.reorder_child(canvas, -1)
        
        self.canvas = canvas

    def set_toolbox(self, toolbox):
        if self.toolbox:
            self._vbox.remove(self.toolbox)

        self._vbox.pack_start(toolbox, False)
        self._vbox.reorder_child(toolbox, 0)
        
        self.toolbox = toolbox
        
    def _window_realize_cb(self, window):
        group = gtk.Window()
        group.realize()
        window.window.set_group(group.window)

    def get_canvas_screenshot(self):
        if not self.canvas:
            return None

        window = self.canvas.window
        width, height = window.get_size()

        screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False,
                                    bits_per_sample=8, width=width, height=height)
        screenshot.get_from_drawable(window, window.get_colormap(), 0, 0, 0, 0,
                                     width, height)
        return screenshot
