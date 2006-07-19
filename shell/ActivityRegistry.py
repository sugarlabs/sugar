import logging
import os
from ConfigParser import ConfigParser
from ConfigParser import NoOptionError

from sugar import env

class ActivityModule:
	"""Info about an activity module. Wraps a .activity file."""
	
	def __init__(self, name, activity_id, activity_exec, directory):
		self._name = name
		self._id = activity_id
		self._directory = directory
		self._exec = activity_exec
	
	def get_name(self):
		"""Get the activity user visible name."""
		return self._name

	def get_id(self):
		"""Get the activity identifier"""
		return self._id

	def get_exec(self):
		"""Get the activity executable"""
		return self._exec

	def get_directory(self):
		"""Get the path to activity directory."""
		return self._directory
		
	def get_default_type(self):
		"""Get the the type of the default activity service."""
		return self._default_type

	def set_default_type(self, default_type):
		"""Set the the type of the default activity service."""
		self._default_type = default_type

class ActivityRegistry:
	"""Service that tracks the available activities"""

	def __init__(self):
		self._activities = []
	
	def get_activity(self, default_type):
		"""Returns an activity given his default type"""
		for activity in self._activities:
			if activity.get_default_type() == default_type:
				return activity
		return None
	
	def scan_directory(self, path):
		"""Scan a directory for activities and add them to the registry.""" 
		if os.path.isdir(path):
			for filename in os.listdir(path):
				activity_dir = os.path.join(path, filename)
				if os.path.isdir(activity_dir):
					for filename in os.listdir(activity_dir):
						if filename.endswith(".activity"):
							self.add(os.path.join(activity_dir, filename))

	def add(self, path):
		"""Add an activity to the registry. The path points to a .activity file."""
		cp = ConfigParser()
		cp.read([path])

		directory = os.path.dirname(path)

		try:
			activity_id = cp.get('Activity', 'id')
		except NoOptionError:
			logging.error('%s miss the required id option' % (path))
			return False

		try:
			name = cp.get('Activity', 'name')
		except NoOptionError:
			logging.error('%s miss the required name option' % (path))
			return False

		if cp.has_option('Activity', 'default_type'):
			default_type = cp.get('Activity', 'default_type')
		else:
			default_type = None

		if cp.has_option('Activity', 'exec'):
			activity_exec = cp.get('Activity', 'exec')
		elif cp.has_option('Activity', 'python_module'):
			python_module = cp.get('Activity', 'python_module')
			python_module = cp.get('Activity', 'python_module')
			activity_exec = '%s %s %s' % ('sugar-activity',
							   			  activity_id, python_module)
			if default_type:
				activity_exec += ' ' + default_type
			env.add_to_python_path(directory)
		else:
			logging.error('%s must specifiy exec or python_module' % (path))
			return False

		module = ActivityModule(name, activity_id, activity_exec, directory)
		self._activities.append(module)

		module.set_default_type(default_type)

		return True

	def list_activities(self):
		"""Enumerate the registered activities as an ActivityModule list."""
		return self._activities
