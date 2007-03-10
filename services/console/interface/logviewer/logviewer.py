#!/usr/bin/env python

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
    def __init__(self, path):
        self._active_log = None
        self._iters = []
                
        # Creating Main treeview with Actitivities list
        tv_menu = gtk.TreeView()
        tv_menu.connect('cursor-changed', self._load_log)
        tv_menu.set_rules_hint(True)
        
        # Set width
        box_width = gtk.gdk.screen_width() * 80 / 100
        tv_menu.set_size_request(box_width*25/100, 0)
    
        self.store_menu = gtk.TreeStore(str)
        tv_menu.set_model(self.store_menu)

        self._add_column(tv_menu, 'Sugar logs', 0)
        self._logs_path = os.path.join(env.get_profile_path(), 'logs')
        self._activity = {}

        # Activities menu
        self.hbox = gtk.HBox(False, 3)
        self.hbox.pack_start(tv_menu, True, True, 0)
        
        # Activity log, set width
        self._view = LogView()
        self._view.set_size_request(box_width*75/100, 0)
        
        self.hbox.pack_start(self._view, True, True, 0)		
        self.hbox.show_all()
        
        gobject.timeout_add(1000, self._update, tv_menu)
    
    # Load the log information in View (textview)
    def _load_log(self, treeview):
        treeselection = treeview.get_selection()

        treestore, iter = treeselection.get_selected()
        
        # Get current selection
        act_log = self.store_menu.get_value(iter, 0)
        
        # Set buffer and scroll down
        self._view.textview.set_buffer(self._activity[act_log])
        self._view.textview.scroll_to_mark(self._activity[act_log].get_insert(), 0);
        self._active_log = act_log
            
    def _update(self, tv_menu):
        # Searching log files
        for logfile in os.listdir(self._logs_path):

            if not self._activity.has_key(logfile):
                self._add_activity(logfile)
                full_log_path = os.path.join(self._logs_path, logfile)
                model = LogBuffer(full_log_path)
                self._activity[logfile] = model
                
            self._activity[logfile].update()
            written = self._activity[logfile]._written
                
            # Load the first iter
            if self._active_log == None:
                self._active_log = logfile
                iter = tv_menu.get_model().get_iter_root()
                tv_menu.get_selection().select_iter(iter)
                self._load_log(tv_menu)
                
            if written > 0 and self._active_log == logfile:
                self._view.textview.scroll_to_mark(self._activity[logfile].get_insert(), 0);

        return True
            
    def _add_activity(self, name):
        self._insert_row(self.store_menu, None, name)
        
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
        viewer = MultiLogView(path)
        self.widget = viewer.hbox

