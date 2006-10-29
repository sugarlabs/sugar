import logging
from ConfigParser import ConfigParser

class Bundle:
	"""Info about an activity bundle. Wraps the activity.info file."""
	def __init__(self, info_path):
		self._name = None
		self._icon = None
		self._service_name = None
		self._show_launcher = False
		self._valid = True

		cp = ConfigParser()
		cp.read([info_path])

		if cp.has_option('Activity', 'service_name'):
			self._service_name = cp.get('Activity', 'service_name')
		else:
			self._valid = False
			logging.error('%s must specify a service name' % info_path)

		if cp.has_option('Activity', 'name'):
			self._service_name = cp.get('Activity', 'name')
		else:
			self._valid = False
			logging.error('%s must specify a name' % info_path)

		if cp.has_option('Activity', 'show_launcher'):
			if cp.get('Activity', 'show_launcher') == 'yes':
				self._show_launcher = True

		if cp.has_option('Activity', 'icon'):
			self._icon = cp.get('Activity', 'icon')

	def is_valid(self):
		return self._valid

	def get_name(self):
		"""Get the activity user visible name."""
		return self._name

	def get_service_name(self):
		"""Get the activity service name"""
		return self._id

	def get_icon(self):
		"""Get the activity icon name"""
		return self._icon

	def get_show_launcher(self):
		"""Get whether there should be a visible launcher for the activity"""
		return self._show_launcher
