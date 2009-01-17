# Copyright (C) 2008 One Laptop Per Child
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

from sugar.graphics import style

class CanvasTextView(hippo.CanvasWidget):
    def __init__(self, text, **kwargs):
        hippo.CanvasWidget.__init__(self, **kwargs)
        self.text_view_widget = gtk.TextView()
        self.text_view_widget.props.buffer.props.text = text
        self.text_view_widget.props.left_margin = style.DEFAULT_SPACING
        self.text_view_widget.props.right_margin = style.DEFAULT_SPACING
        self.text_view_widget.props.wrap_mode = gtk.WRAP_WORD
        self.text_view_widget.show()
        
        # TODO: These fields should expand vertically instead of scrolling
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_shadow_type(gtk.SHADOW_OUT)
        scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled_window.add(self.text_view_widget)
        
        self.props.widget = scrolled_window
