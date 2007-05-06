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

import gtk

class Notebook(gtk.Notebook):
    
    page_number = 0
    
    def __init__(self):
        gtk.Notebook.__init__(self)
        self.set_scrollable(True)

        t_width = gtk.gdk.screen_width()
        t_height = gtk.gdk.screen_height() * 83 / 100

        self.set_size_request(t_width, t_height)
        self.show()

    def _add_icon_to_button(self, button):
        iconBox = gtk.HBox(False, 0)
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        gtk.Button.set_relief(button, gtk.RELIEF_NONE)

        settings = gtk.Widget.get_settings (button)
        (w,h) = gtk.icon_size_lookup_for_settings (settings, gtk.ICON_SIZE_MENU)
        gtk.Widget.set_size_request (button, w + 4, h + 4)
        image.show()
        iconBox.pack_start(image, True, False, 0)
        button.add(iconBox)
        iconBox.show()

    def _create_custom_tab(self, text, child):
        eventBox = gtk.EventBox()
        tabBox = gtk.HBox(False, 2)
        tabLabel = gtk.Label(text)

        tabButton = gtk.Button()
        tabButton.connect('clicked', self.close_page, child)

        # Add a picture on a button
        self._add_icon_to_button(tabButton)
        iconBox = gtk.HBox(False, 0)

        eventBox.show()
        tabButton.show()
        tabLabel.show()

        tabBox.pack_start(tabLabel, False)
        tabBox.pack_start(tabButton, False)

        tabBox.show_all()
        eventBox.add(tabBox)
        
        return eventBox

    # Add a new page to the notebook
    def add_page(self, text_label, widget):
        eventBox = self._create_custom_tab(text_label, widget)
        self.append_page(widget, eventBox)

        # Set the new page
        pages = self.get_n_pages()
        self.set_current_page(pages - 1)
        return True

    # Remove a page from the notebook
    def close_page(self, button, child):
        page = self.page_num(child)

        if page != -1:
            self.remove_page(page)

        # Need to refresh the widget --
        # This forces the widget to redraw itself.
        self.queue_draw_area(0, 0, -1, -1)

