import os
import info

INTERNALS = {
			'PLGNAME': "cpu",
			'TABNAME': None,
			'AUTHOR': "Eduardo Silva",
			'DESC': "Print CPU usage",

			# Plugin API
			'Plg': None, # Plugin object
			'current_plg': None, # Current plugin object
			'current_page': None, # Current page number

			# Top process view requirements
			'top_data': [int], # Top data types needed by memphis core plugin
			'top_cols': ["%CPU "] # Column names
		}

# Get CPU frequency 
cpu_hz = os.sysconf(2)

pids_ujiffies = {}
