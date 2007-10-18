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
import dbus.glib
import dbus.service
import os
import sys
import gtk
import gobject

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(__file__) + '/lib')
sys.path.append(os.path.dirname(__file__) + '/interface')

CONSOLE_BUS = 'org.laptop.sugar.Console'
CONSOLE_PATH = '/org/laptop/sugar/Console'
CONSOLE_IFACE = 'org.laptop.sugar.Console'

class Console:
    
    def __init__(self):
        # Main Window
        self.window = gtk.Window()
        self.window.set_title('Developer console')
        self.window.connect("delete-event", self._delete_event_cb)
        
        self.default_width = gtk.gdk.screen_width() * 95 / 100
        self.default_height = gtk.gdk.screen_height() * 95 / 100
        
        self.window.set_default_size(self.default_width, self.default_height)
        
        self.window.realize()
        self.window.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        
        # Notebook
        self.notebook = gtk.Notebook()

        self._load_interface('xo', 'XO Resources')
        self._load_interface('network', 'Network')
        self._load_interface('xserver', 'X Server')
        self._load_interface('memphis', 'Memphis')
        self._load_interface('logviewer', 'Log Viewer')
        self._load_interface('ps_watcher', 'Presence')
        
        main_hbox = gtk.HBox()
        main_hbox.pack_start(self.notebook, True, True, 0)
        main_hbox.show()
        
        self.notebook.show()
        self.window.add(main_hbox)

    def _load_interface(self, interface, label):
        mod = __import__(interface)
        widget = mod.Interface().widget
        widget.show()

        self.notebook.append_page(widget, gtk.Label(label))
    
    def _delete_event_cb(self, window, gdkevent):
        gtk.main_quit()
    
class Service(dbus.service.Object):
    def __init__(self, bus, object_path=CONSOLE_PATH):
        dbus.service.Object.__init__(self, bus, object_path)
        self._console = Console()
 
    @dbus.service.method(CONSOLE_IFACE)
    def ToggleVisibility(self):
        window = self._console.window
        if not window.props.visible:
            window.present()
        else:
            window.hide()

bus = dbus.SessionBus()
name = dbus.service.BusName(CONSOLE_BUS, bus)

obj = Service(name)

gtk.main()
