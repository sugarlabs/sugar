import logging
import os

from ConfigParser import ConfigParser

class Bundle:
	"""Info about an activity bundle. Wraps the activity.info file."""
	def __init__(self, path):
		self._name = None
		self._icon = None
		self._service_name = None
		self._show_launcher = False
		self._valid = True
		self._path = path

		info_path = os.path.join(path, 'activity', 'activity.info')
		if os.path.isfile(info_path):
			self._parse_info(info_path)
		else:
			self._valid = False

	def _parse_info(self, info_path):
		cp = ConfigParser()
		cp.read([info_path])

		section = 'Activity'

		if cp.has_option(section, 'service_name'):
			self._service_name = cp.get(section, 'service_name')
		else:
			self._valid = False
			logging.error('%s must specify a service name' % self._path)

		if cp.has_option(section, 'name'):
			self._name = cp.get(section, 'name')
		else:
			self._valid = False
			logging.error('%s must specify a name' % self._path)

		if cp.has_option(section, 'exec'):
			self._exec = cp.get(section, 'exec')
		else:
			self._valid = False
			logging.error('%s must specify an exec' % self._path)

		if cp.has_option(section, 'show_launcher'):
			if cp.get(section, 'show_launcher') == 'yes':
				self._show_launcher = True

		if cp.has_option(section, 'icon'):
			self._icon = cp.get(section, 'icon')

	def is_valid(self):
		return self._valid

	def get_path(self):
		"""Get the activity bundle path."""
		return self._path

	def get_name(self):
		"""Get the activity user visible name."""
		return self._name

	def get_service_name(self):
		"""Get the activity service name"""
		return self._service_name

	def get_icon(self):
		"""Get the activity icon name"""
		return self._icon

	def get_exec(self):
		"""Get the command to execute to launch the activity factory"""
		return self._exec

	def get_show_launcher(self):
		"""Get whether there should be a visible launcher for the activity"""
		return self._show_launcher

	# Compatibility with the old activity registry, remove after BTest-1
	def get_id(self):
		return self._service_name
