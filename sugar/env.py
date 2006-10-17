# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os
import sys
import pwd

try:
	from sugar.__uninstalled__ import *
except ImportError:
	from sugar.__installed__ import *

import sugar.setup

def setup_python_path():
	for path in sugar_python_path:
		if os.environ.has_key('PYTHONPATH'):
			old_path = os.environ['PYTHONPATH']
			os.environ['PYTHONPATH'] = path + ':' + old_path 
		else:
			os.environ['PYTHONPATH'] = path

def setup_system():
	setup_python_path()

	for path in sugar_bin_path:
		if os.environ.has_key('PATH'):
			old_path = os.environ['PATH']
			os.environ['PATH'] = path + ':' + old_path
		else:
			os.environ['PATH'] = path

	if sugar_source_dir:
		source = os.path.join(sugar_source_dir, 'activities')
		runner = os.path.join(sugar_source_dir, 'shell/sugar-activity-factory')
		sugar.setup.setup_activities(source, sugar_activities_dir, runner)
		
		bin = os.path.join(sugar_source_dir,
						  'services/presence/sugar-presence-service')
		sugar.setup.write_service('org.laptop.Presence', bin,
								  sugar_activities_dir)

def get_profile_path():
	if os.environ.has_key('SUGAR_PROFILE'):
		profile_id = os.environ['SUGAR_PROFILE']
	else:
		profile_id = 'default'

	path = os.path.join(os.path.expanduser('~/.sugar'), profile_id)
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except OSError, exc:
			print "Could not create user directory."

	return path

def get_data_dir():
	return sugar_data_dir

def get_activities_dir():
	return sugar_activities_dir

def get_services_dir():
	return sugar_services_dir

def get_dbus_config():
	return sugar_dbus_config
