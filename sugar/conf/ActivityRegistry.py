import logging
import os
from ConfigParser import ConfigParser
from ConfigParser import NoOptionError

from sugar import env

def get_default_type(activity_type):
	"""Get the activity default type.

	   It's the type of the main network service which tracks presence
       and provides info about the activity, for example the title."""
	splitted_id = activity_type.split('.')
	splitted_id.reverse()
	return '_' + '_'.join(splitted_id) + '._udp'

class ActivityModule:
	"""Info about an activity module. Wraps a .activity file."""
	
	def __init__(self, name, activity_id, directory):
		self._name = name
		self._icon = None
		self._id = activity_id
		self._directory = directory
		self._show_launcher = False	

	def get_name(self):
		"""Get the activity user visible name."""
		return self._name

	def get_id(self):
		"""Get the activity identifier"""
		return self._id

	def get_icon(self):
		"""Get the activity icon name"""
		return self._icon

	def set_icon(self, icon):
		"""Set the activity icon name"""
		self._icon = icon

	def get_directory(self):
		"""Get the path to activity directory."""
		return self._directory
		
	def get_default_type(self):
		"""Get the the type of the default activity service."""
		return get_default_type(self._id)

	def set_default_type(self, default_type):
		"""Set the the type of the default activity service."""
		self._default_type = default_type

	def get_show_launcher(self):
		"""Get whether there should be a visible launcher for the activity"""
		return self._show_launcher

	def set_show_launcher(self, show_launcher):
		"""Set whether there should be a visible launcher for the activity"""
		self._show_launcher = show_launcher

class _ActivityRegistry:
	"""Service that tracks the available activities"""

	def __init__(self):
		self._activities = []
		self.scan_directory(env.get_activities_dir())

	def get_activity(self, activity_id):
		"""Returns an activity given his identifier"""
		for activity in self._activities:
			if activity.get_id() == activity_id:
				return activity
		return None
	
	def get_activity_from_type(self, default_type):
		"""Returns an activity given his default type"""
		for activity in self._activities:
			if activity.get_default_type() == default_type:
				return activity
		return None
	
	def scan_directory(self, path):
		"""Scan a directory for activities and add them to the registry.""" 
		if os.path.isdir(path):
			for f in os.listdir(path):
				if f.endswith(".activity"):
					self.add(os.path.join(path, f))

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

		module = ActivityModule(name, activity_id, directory)
		self._activities.append(module)

		if cp.has_option('Activity', 'show_launcher'):
			module.set_show_launcher(True)

		if cp.has_option('Activity', 'icon'):
			module.set_icon(cp.get('Activity', 'icon'))

		return True

	def list_activities(self):
		"""Enumerate the registered activities as an ActivityModule list."""
		return self._activities
