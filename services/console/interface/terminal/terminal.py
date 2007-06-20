# Copyright (C) 2006, Red Hat, Inc.
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


# Modified by Eduardo Silva, edsiper@gmail.com

import ConfigParser
import os.path

import gtk
import vte
import pango

import sugar.env

class Terminal(gtk.HBox):
    def __init__(self):
        gtk.HBox.__init__(self, False, 4)

        self._vte = vte.Terminal()
        self._configure_vte()
        self._vte.set_size(30, 5)
        self._vte.set_size_request(200, 450)
        self._vte.show()
        self.pack_start(self._vte)

        self._scrollbar = gtk.VScrollbar(self._vte.get_adjustment())
        self._scrollbar.show()
        self.pack_start(self._scrollbar, False, False, 0)

        self._vte.connect("child-exited", lambda term: term.fork_command())

        self._vte.fork_command()
                
    def _configure_vte(self):
        conf = ConfigParser.ConfigParser()

        conf_file = os.path.join(sugar.env.get_profile_path(), 'terminalrc')
        
        if os.path.isfile(conf_file):
            f = open(conf_file, 'r')
            conf.readfp(f)
            f.close()
        else:
            conf.add_section('terminal')

        if conf.has_option('terminal', 'font'):
            font = conf.get('terminal', 'font')
        else:
            font = 'Monospace 8'
            conf.set('terminal', 'font', font)
        self._vte.set_font(pango.FontDescription(font))

        if conf.has_option('terminal', 'fg_color'):
            fg_color = conf.get('terminal', 'fg_color')
        else:
            fg_color = '#000000'
            conf.set('terminal', 'fg_color', fg_color)
        if conf.has_option('terminal', 'bg_color'):
            bg_color = conf.get('terminal', 'bg_color')
        else:
            bg_color = '#FFFFFF'
            conf.set('terminal', 'bg_color', bg_color)
        self._vte.set_colors(gtk.gdk.color_parse (fg_color),
                            gtk.gdk.color_parse (bg_color),
                            [])
                            
        if conf.has_option('terminal', 'cursor_blink'):
            blink = conf.getboolean('terminal', 'cursor_blink')
        else:
            blink = False
            conf.set('terminal', 'cursor_blink', blink)
        
        self._vte.set_cursor_blinks(blink)

        if conf.has_option('terminal', 'bell'):
            bell = conf.getboolean('terminal', 'bell')
        else:
            bell = False
            conf.set('terminal', 'bell', bell)
        self._vte.set_audible_bell(bell)
        
        if conf.has_option('terminal', 'scrollback_lines'):
            scrollback_lines = conf.getint('terminal', 'scrollback_lines')
        else:
            scrollback_lines = 1000
            conf.set('terminal', 'scrollback_lines', scrollback_lines)
            
        self._vte.set_scrollback_lines(scrollback_lines)
        
        self._vte.set_allow_bold(True)
        
        if conf.has_option('terminal', 'scroll_on_keystroke'):
            scroll_key = conf.getboolean('terminal', 'scroll_on_keystroke')
        else:
            scroll_key = False
            conf.set('terminal', 'scroll_on_keystroke', scroll_key)
        self._vte.set_scroll_on_keystroke(scroll_key)
        
        if conf.has_option('terminal', 'scroll_on_output'):
            scroll_output = conf.getboolean('terminal', 'scroll_on_output')
        else:
            scroll_output = False
            conf.set('terminal', 'scroll_on_output', scroll_output)
        self._vte.set_scroll_on_output(scroll_output)
        
        if conf.has_option('terminal', 'emulation'):
            emulation = conf.get('terminal', 'emulation')
        else:
            emulation = 'xterm'
            conf.set('terminal', 'emulation', emulation)
        self._vte.set_emulation(emulation)
        
        if conf.has_option('terminal', 'visible_bell'):
            visible_bell = conf.getboolean('terminal', 'visible_bell')
        else:
            visible_bell = False
            conf.set('terminal', 'visible_bell', visible_bell)
        self._vte.set_visible_bell(visible_bell)
        
        conf.write(open(conf_file, 'w'))
        
    def on_gconf_notification(self, client, cnxn_id, entry, what):
        self.reconfigure_vte()

    def on_vte_button_press(self, term, event):
        if event.button == 3:
            self.do_popup(event)
            return True

    def on_vte_popup_menu(self, term):
        pass

class Multiple:
    
    page_number = 0
    
    def __init__(self):
        self.notebook = gtk.Notebook()
        t_width = gtk.gdk.screen_width()
        t_height = gtk.gdk.screen_height() * 83 / 100
        self.notebook.set_size_request(t_width, t_height)

        self.add_new_terminal()
        
        open_terminal = gtk.Button('Open a new terminal')
        open_terminal.connect("clicked", self.add_new_terminal)
        open_terminal.show()
                
        self.notebook.show()
        
        self.main_vbox = gtk.VBox(False, 3)
        self.main_vbox.pack_start(open_terminal, True, True, 2)
        self.main_vbox.pack_start(self.notebook, True, True, 2)

        self.main_vbox.show_all()
    
    # Remove a page from the notebook
    def close_terminal(self, button, child):
        page = self.notebook.page_num(child)

        if page != -1:
            self.notebook.remove_page(page)
        
        
        pages = self.notebook.get_n_pages()
        if pages <= 0:
            self.page_number = 0
            self.add_new_terminal()
            
        # Need to refresh the widget --
        # This forces the widget to redraw itself.
        self.notebook.queue_draw_area(0, 0, -1, -1)

    def add_icon_to_button(self, button):
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

    def add_new_terminal(self, *arguments, **keywords):
        self.page_number += 1

        terminal = Terminal()
        terminal.show()

        eventBox = self.create_custom_tab("Term %d" % self.page_number, terminal)
        self.notebook.append_page(terminal, eventBox)

        # Set the new page
        pages = gtk.Notebook.get_n_pages(self.notebook)
        self.notebook.set_current_page(pages - 1)
        return True

    def create_custom_tab(self, text, child):
        eventBox = gtk.EventBox()
        tabBox = gtk.HBox(False, 2)
        tabLabel = gtk.Label(text)

        tabButton = gtk.Button()
        tabButton.connect('clicked', self.close_terminal, child)

        # Add a picture on a button
        self.add_icon_to_button(tabButton)
        iconBox = gtk.HBox(False, 0)

        eventBox.show()
        tabButton.show()
        tabLabel.show()

        tabBox.pack_start(tabLabel, False)
        tabBox.pack_start(tabButton, False)

        tabBox.show_all()
        eventBox.add(tabBox)
        
        return eventBox

class Interface:

    def __init__(self):
        multiple = Multiple()
        self.widget = multiple.main_vbox
        
