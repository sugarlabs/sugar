from sugar.activity.bundle import Bundle

class BundleRegistry:
	"""Service that tracks the available activity bundles"""

	def __init__(self):
		self._bundles = {}
		self._search_path = []

	def get_bundle(self, service_name):
		"""Returns an bundle given his service name"""
		if self._bundles.has_key(service_name):
			return self._bundles[service_name]
		else:
			return None

	def append_search_path(self, path):
		"""Append a directory to the bundles search path"""
		self._search_path.append(path)
		self._scan_directory(path)
	
	def __iter__(self):
		return self._bundles.values()

	def _scan_directory(self, path):
		for bundle_dir in os.listdir(path):
			if os.path.isdir(bundle_dir):
				info_path = os.path.join(bundle_dir, activity_info)
				if os.path.isfile(info_path):
					bundle = Bundle(info_path)
					if bundle.is_valid():
						self._bundles.append(bundle)
