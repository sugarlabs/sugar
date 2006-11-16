#!/usr/bin/env python

import sys, os
import string
import wnck
import plugin

from procmem import proc

try:
	import gtk
	import gtk.gdk
	import gobject
except:
	sys.exit(1)

class Interface:
	
	store_data_types = []
	store_data_types_details = []
	
	def __init__(self):	
		
		# Our GtkTree (Treeview)
		self.treeview = gtk.TreeView()
		self.widget = self.treeview
		
		# Loading plugins
		self.plg = plugin.Plugin()
				
		# TOP data types (columns)
		self.store_data_types = []
		
		for plg in self.plg.list:
			plg_data = plg.INTERNALS
			
			# Give plugin object to plugin
			plg.INTERNALS['Plg'] = self.plg

		# Creating a store model and loading process data to Treeview
		# self.store_data_types, ex [int, str, str, str, int,...]
		#self.store = gtk.TreeStore(*self.store_data_types)
		self.data = Data(self.treeview, self.plg.list)
	
class Data:

	treeview = None
	last_col_index = 0

	store_data_cols = []
	store_data_types = []
	store_data_types_details = []
	
	def __init__(self, treeview, plg_list):
		
		# Top data types
		self.plg_list = plg_list
		
		for plg in self.plg_list:

			if plg.INTERNALS['top_data'] != None:
				last_dt = len(self.store_data_types)
	
				if last_dt > 0:
					last_dt -= 1
	
				len_dt = len(plg.INTERNALS['top_data'])
	
				self.store_data_types_details.append({"plugin": plg, "init": last_dt, "end": last_dt + len_dt})
				
				for dt in plg.INTERNALS['top_data']:
					self.store_data_types.append(dt)

				for col in plg.INTERNALS['top_cols']:
					self.store_data_cols.append(col)
		
		# Set global treeview
		self.treeview = treeview
		
		# Basic columns 
		index = 0
		for column_name in self.store_data_cols:
			self.add_column(column_name, index)
			index += 1
		
		self.store = gtk.TreeStore(*self.store_data_types)
		treeview.set_model(self.store)

		# Update information every 1 second
		gobject.timeout_add(500, self.load_data, treeview)

	# Add a new column to the main treeview 
	def add_column(self, column_name, index):
		cell = gtk.CellRendererText()
		col_tv = gtk.TreeViewColumn(column_name, cell, text=index)
		col_tv.set_resizable(True)
		col_tv.connect('clicked', self.sort_column_clicked)
		col_tv.set_property('clickable', True)
		
		self.treeview.append_column(col_tv)
		
		# Set the last column index added
		self.last_col_index = index

	# Sorting 
	def sort_column_clicked(self, TreeViewColumn):
		cols = self.treeview.get_columns()

		# Searching column index
		index = 0
		for col in cols:
			if col == TreeViewColumn:
				break
			
			index += 1

		self.store.set_sort_column_id(index, gtk.SORT_DESCENDING)
		
	def load_data(self, treeview):
		self.store.clear()
		
		# Getting procfs data
		self.procdata = proc.ProcInfo()
		self.process_list = []

		pids = []
		screen = wnck.screen_get_default()
		windows =  screen.get_windows()
	
		current_pid = os.getpid()
		
		for win in windows:
			pid = int(win.get_pid())
			if current_pid != pid:
				pids.append(pid)
	
		self.process_list = set(pids)
		
		# Sort rows using pid
		#self.process_list.sort(key=operator.itemgetter('pid'))
		self.process_iter = []
	
		for pid in self.process_list:
			pi = self.build_row(self.store, None, self.procdata, pid)
			self.process_iter.append(pi)
	
		treeview.set_rules_hint(True)
		treeview.expand_all()

		return True
	
	def build_row(self, store, parent_iter, proc_data, pid):
		data = []
	
		pinfo = proc_data.MemoryInfo(pid)
			
		# Look for plugins that need to update the top data treeview
		for plg in self.plg_list:
			plg_data = []
			
			if plg.INTERNALS['top_data'] != None:
				# data = [xxx, yyy,zzz,...]
				plg_data = plg.info.plg_on_top_data_refresh(plg, pinfo)
								
			for field in plg_data:
				data.append(field)
										
		pi = self.insert_row(store, parent_iter, data)
	
		return pi
		
	# Insert a Row in our TreeView
	def insert_row(self, store, parent, row_data):
		iter = store.insert_after(parent, None)

		index = 0
		
		for data in row_data:
			store.set_value(iter, index , data)
			index += 1
			
		return iter
