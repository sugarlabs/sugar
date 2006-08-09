#!/usr/bin/python

import os
import sys
import shutil
import logging
from ConfigParser import ConfigParser
from ConfigParser import NoOptionError

class ServiceParser(ConfigParser):
	def optionxform(self, option):
		return option

def setup_activity(source, dest_path, bin):
	"""Copy an activity to the destination path and setup it"""
	filename = os.path.basename(source)
	dest = os.path.join(dest_path, filename)
	print 'Install ' + filename + ' ...'
	shutil.copyfile(source, dest)

	cp = ConfigParser()
	cp.read([source])

	try:
		activity_id = cp.get('Activity', 'id')
	except NoOptionError:
		logging.error('%s miss the required id option' % (path))
		return False
	
	if cp.has_option('Activity', 'exec'):
		activity_exec = cp.get('Activity', 'exec')
	elif cp.has_option('Activity', 'python_module'):
		python_module = cp.get('Activity', 'python_module')
		python_module = cp.get('Activity', 'python_module')
		activity_exec = '%s %s %s' % (bin, activity_id, python_module)
	else:
		logging.error('%s must specifiy exec or python_module' % (source))
		return False
	
	service_cp = ServiceParser()
	section = 'D-BUS Service'	
	service_cp.add_section(section)
	service_cp.set(section, 'Name', activity_id + '.Factory')
	service_cp.set(section, 'Exec', activity_exec)

	fileobject = open(os.path.join(dest_path, activity_id + '.service'), 'w')
	service_cp.write(fileobject)
	fileobject.close()

def setup_activities(source_path, dest_path, bin):
	"""Scan a directory for activities and install them.""" 
	if os.path.isdir(source_path):
		for filename in os.listdir(source_path):
			activity_dir = os.path.join(source_path, filename)
			if os.path.isdir(activity_dir):
				for filename in os.listdir(activity_dir):
					if filename.endswith(".activity"):
						source = os.path.join(activity_dir, filename)
						setup_activity(source, dest_path, bin)

if __name__=='__main__':
	setup_activities(sys.argv[1], sys.argv[2], sys.argv[3])
