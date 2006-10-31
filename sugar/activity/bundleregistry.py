import os
from ConfigParser import ConfigParser

from sugar.activity.bundle import Bundle

class _ServiceParser(ConfigParser):
	def optionxform(self, option):
		return option

class _ServiceManager(object):
	def __init__(self):
		self._path = '/tmp/sugar-services'

		if not os.path.isdir(self._path):
			os.mkdir(self._path)

	def add(self, bundle):
		name = bundle.get_service_name()

		service_cp = _ServiceParser()

		section = 'D-BUS Service'
		service_cp.add_section(section)
		service_cp.set(section, 'Name', name)
		service_cp.set(section, 'Exec', bundle.get_exec())

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

	def _add_bundle(self, bundle_dir):
		info_path = os.path.join(bundle_dir, 'activity', 'activity.info')
		if os.path.isfile(info_path):
			bundle = Bundle(info_path)
			if bundle.is_valid():
				self._bundles[bundle.get_service_name()] = bundle
				self._service_manager.add(bundle)
