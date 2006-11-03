import os
from ConfigParser import ConfigParser

from sugar.activity.bundle import Bundle
from sugar import env

class _ServiceParser(ConfigParser):
	def optionxform(self, option):
		return option

class _ServiceManager(object):
	def __init__(self):
		if env.get_dbus_version() < '0.95':
			self._path = '/tmp/sugar-services'
		else:
			self._path = os.path.expanduser('~/.local/share/dbus-1/services')

		if not os.path.isdir(self._path):
			os.makedirs(self._path)

	def add(self, bundle):
		name = bundle.get_service_name()

		service_cp = _ServiceParser()

		section = 'D-BUS Service'
		service_cp.add_section(section)

		# Compatibility with the old activity registry, remove after BTest-1
		# service_cp.set(section, 'Name', name)
		service_cp.set(section, 'Name', name + '.Factory')

		# FIXME total hack
		full_exec = env.get_shell_bin_dir() + '/' + bundle.get_exec()
		full_exec += ' ' + bundle.get_path()
		service_cp.set(section, 'Exec', full_exec)

		dest = os.path.join(self._path, name + '.service')
		fileobject = open(dest, 'w')
		service_cp.write(fileobject)
		fileobject.close()

class BundleRegistry:
	"""Service that tracks the available activity bundles"""

	def __init__(self):
		self._bundles = {}
		self._search_path = []
		self._service_manager = _ServiceManager()

	def get_bundle(self, service_name):
		"""Returns an bundle given his service name"""
		if self._bundles.has_key(service_name):
			return self._bundles[service_name]
		else:
			return None

	def add_search_path(self, path):
		"""Add a directory to the bundles search path"""
		self._search_path.append(path)
		self._scan_directory(path)
	
	def __iter__(self):
		return self._bundles.values().__iter__()

	def _scan_directory(self, path):
		if os.path.isdir(path):
			for f in os.listdir(path):
				bundle_dir = os.path.join(path, f)
				if os.path.isdir(bundle_dir) and \
				   bundle_dir.endswith('.activity'):
					self._add_bundle(bundle_dir)

	def _add_bundle(self, bundle_path):
		bundle = Bundle(bundle_path)
		if bundle.is_valid():
			self._bundles[bundle.get_service_name()] = bundle
			self._service_manager.add(bundle)
