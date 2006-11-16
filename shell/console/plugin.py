###############################################
# Memphis Plugin Support
###############################################

import sys, os, time
import gtk, gobject

from procmem import proc, proc_smaps, analysis

class Plugin:

	# Plugin list
	list = []
	proc = proc.ProcInfo()
	
	internal_plugin = "memphis_init"
	plg_path = os.path.dirname(os.path.abspath(__file__)) + "/plugins"
	
	# Frequency timer, managed by main program
	freq_timer = 0
	
	def __init__(self):
		
		sys.path.insert(0, self.plg_path)
		
		# Including memphis plugin
		self.list.append(__import__(self.internal_plugin))
		
		if os.path.isdir(self.plg_path):
			# around dir entries
			for plg in os.listdir(self.plg_path):
				
				if plg == self.internal_plugin:
					continue
				
				if os.path.isdir(self.plg_path + "/" + plg):
					p = __import__(plg)
					self.list.append(__import__(plg))
			
	# Parse /proc/PID/smaps information
	def proc_get_smaps(self, pid):
		return proc_smaps.ProcSmaps(pid)
	
	# Parse /proc/PID/maps information
	def proc_get_maps(self, pid):
		return proc_smaps.ProcMaps(pid)

	def proc_analysis(self, pid):
		return analysis.Analysis(pid)
	