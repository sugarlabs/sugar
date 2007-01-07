#!/usr/bin/env python

# Copyright (C) 2006, Eduardo Silva (edsiper@gmail.com).
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

import dbus
import dbus.service
import os
import sys
import gtk
import gobject

sys.path.append(os.path.dirname(__file__) + '/lib')
sys.path.append(os.path.dirname(__file__) + '/interface')

DBUS_BUS = 'org.freedesktop.DBus'
DBUS_PATH = '/org/freedesktop/DBus'

CONSOLE_BUS = 'org.laptop.Sugar.DeveloperConsole'
CONSOLE_PATH = '/org/laptop/Sugar/DeveloperConsole'
CONSOLE_IFACE = 'org.laptop.Sugar.DeveloperConsole'

class Console:
    
    def __init__(self):
        
        # Main Window
        self.window = gtk.Window()
        self.window.set_title('Developer console')
        self.window.connect("delete-event", self._minimize_main_window)
        
        self.default_width = gtk.gdk.screen_width() * 95 / 100
        self.default_height = gtk.gdk.screen_height() * 95 / 100
        self.default_mini_width = 150
        self.default_mini_height = 30
        
        self.window.set_default_size(self.default_width, self.default_height)
        
        self.window.realize()
        self.window.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        
        # Minimize Window
        self.mini_fixed = gtk.Fixed()
        
        # Minimize buttons
        button_restore = gtk.Button('Restore')
        button_restore.connect("clicked", self._restore_window)
        
        button_quit = gtk.Button('Quit')
        button_quit.connect("clicked", gtk.main_quit)
        
        mini_hbox = gtk.HBox()
        mini_hbox.pack_start(button_restore, True, True, 0)
        mini_hbox.pack_start(button_quit, True, True, 0)
        self.mini_fixed.add(mini_hbox)
                
        # Notebook
        self.notebook = gtk.Notebook()
        
        self._load_interface('xo', 'XO Resources')
        self._load_interface('memphis', 'Memphis')
        self._load_interface('logviewer', 'Log Viewer')
        self._load_interface('terminal', 'Terminal')
        
        main_hbox = gtk.HBox()
        main_hbox.pack_start(self.notebook, True, True, 0)
        main_hbox.pack_start(self.mini_fixed, True, True, 0)
        main_hbox.show()
        
        self.notebook.show()
        self.window.add(main_hbox)
        self.window.show()
        
        self.mini_fixed.hide()
        
    def _load_interface(self, interface, label):
        mod = __import__(interface)
        widget = mod.Interface().widget
        widget.show()
        
        self.notebook.append_page(widget, gtk.Label(label))

    
    def _restore_window(self, button):
        self.mini_fixed.hide_all()
        self.window.resize(self.default_mini_width, self.default_mini_height)
        self.notebook.show_all()
                        
    def _minimize_main_window(self, window, gdkevent):
        self.notebook.hide_all()
        window.resize(self.default_mini_width, self.default_mini_height)
        self.mini_fixed.show_all()
        return True
    
# We're using a DBUS-Service to avoid open devconsole more than one time
class Init_Service(dbus.service.Object):
    
    def __init__(self, bus, object_path=CONSOLE_PATH):
        dbus.service.Object.__init__(self, bus, object_path)
        CS = Console()
    
bus = dbus.SessionBus()
obj = bus.get_object(DBUS_BUS, DBUS_PATH)

dbus_iface = dbus.Interface(obj, DBUS_BUS)
services = dbus_iface.ListNames()

# A temporal way to check if the service is running
if not CONSOLE_BUS in services:    
    name = dbus.service.BusName(CONSOLE_BUS, bus)
    obj = Init_Service(name)
    gtk.main()
else:
    sys.exit(1)
    