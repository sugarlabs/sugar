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


# Rewritten by Eduardo Silva, edsiper@gmail.com

import os

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

from sugar import env

class MultiLogView(gtk.VBox):
    def __init__(self, path, extra_files):
        self._active_log = None
        self._extra_files = extra_files

        # Creating Main treeview with Actitivities list
        self._tv_menu = gtk.TreeView()
        self._tv_menu.connect('cursor-changed', self._load_log)
        self._tv_menu.set_rules_hint(True)
        
        # Set width
        box_width = gtk.gdk.screen_width() * 80 / 100
        self._tv_menu.set_size_request(box_width*25/100, 0)
    
        self._store_menu = gtk.TreeStore(str)
        self._tv_menu.set_model(self._store_menu)

        self._add_column(self._tv_menu, 'Sugar logs', 0)
        self._logs_path = os.path.join(env.get_profile_path(), 'logs')
        self._activity = {}

        # Activities menu
        self.hbox = gtk.HBox(False, 3)
        self.hbox.pack_start(self._tv_menu, True, True, 0)
        
        # Activity log, set width
        self._view = LogView()
        self._view.set_size_request(box_width*75/100, 0)
        
        self.hbox.pack_start(self._view, True, True, 0)		
        self.hbox.show_all()
        
        gobject.timeout_add(1000, self._update)
    
    # Load the log information in View (textview)
    def _load_log(self, treeview):
        treeselection = treeview.get_selection()
        treestore, iter = treeselection.get_selected()

        # Get current selection
        act_log = self._store_menu.get_value(iter, 0)

        # Set buffer and scroll down
        self._view.textview.set_buffer(self._activity[act_log])
        self._view.textview.scroll_to_mark(self._activity[act_log].get_insert(), 0);
        self._active_log = act_log

    def _update(self):
        # Searching log files
        for logfile in os.listdir(self._logs_path):
            full_log_path = os.path.join(self._logs_path, logfile)
            self._add_log_file(full_log_path)

        for ext in self._extra_files:
            self._add_log_file(ext)

        return True

    def _get_filename_from_path(self, path):
        return path.split('/')[-1]

    def _add_log_file(self, path):
        if os.path.isdir(path):
            return False

        if not os.path.exists(path):
            print "ERROR: %s don't exists"
            return False

        logfile = self._get_filename_from_path(path)

        if not self._activity.has_key(logfile):
            self._add_activity(logfile)
            model = LogBuffer(path)
            self._activity[logfile] = model

        self._activity[logfile].update()
        written = self._activity[logfile]._written

        # Load the first iter
        if self._active_log == None:
            self._active_log = logfile
            iter = self._tv_menu.get_model().get_iter_root()
            self._tv_menu.get_selection().select_iter(iter)
            self._load_log(self._tv_menu)

        if written > 0 and self._active_log == logfile:
            self._view.textview.scroll_to_mark(self._activity[logfile].get_insert(), 0)


    def _add_activity(self, name):
        self._insert_row(self._store_menu, None, name)
        
    # Add a new column to the main treeview, (code from Memphis)
    def _add_column(self, treeview, column_name, index):
        cell = gtk.CellRendererText()
        col_tv = gtk.TreeViewColumn(column_name, cell, text=index)
        col_tv.set_resizable(True)
        col_tv.set_property('clickable', True)
        
        treeview.append_column(col_tv)
        
        # Set the last column index added
        self.last_col_index = index

    # Insert a Row in our TreeView
    def _insert_row(self, store, parent, name):
        iter = store.insert_before(parent, None)
        index = 0
        store.set_value(iter, index , name)
            
        return iter

class LogBuffer(gtk.TextBuffer):
    def __init__(self, logfile):
        gtk.TextBuffer.__init__(self)

        self._logfile = logfile
        self._pos = 0
        self.update()

    def update(self):
        f = open(self._logfile, 'r')

        init_pos = self._pos
    
        f.seek(self._pos)
        self.insert(self.get_end_iter(), f.read())
        self._pos = f.tell()
    
        f.close()
    
        self._written = (self._pos - init_pos)
        return True

class LogView(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.textview = gtk.TextView()
        self.textview.set_wrap_mode(gtk.WRAP_WORD)
        
        font = pango.FontDescription('Sans 8')
        font.set_weight(pango.WEIGHT_LIGHT)
        self.textview.modify_font(font)
        
        # Set background color
        bgcolor = gtk.gdk.color_parse("#FFFFFF")
        self.textview.modify_base(gtk.STATE_NORMAL, bgcolor)

        self.textview.set_editable(False)

        self.add(self.textview)
        self.textview.show()

class Interface:
    def __init__(self):
        path = None
        xserver_logfile = self._get_xserver_logfile_path()
        
        # Aditional files to watch in logviewer
        ext_files = []
        ext_files.append(xserver_logfile)
        ext_files.append("/var/log/syslog")
        ext_files.append("/var/log/messages")

        viewer = MultiLogView(path, ext_files)
        self.widget = viewer.hbox

    # Get the Xorg log file path, we have two ways to get the path: do a system
    # call and exec a 'xset -q' or just read directly the file that we know 
    # always be the right one for a XO machine...
    def _get_xserver_logfile_path(self):
        path = "/var/log/Xorg.0.log"
        return path
