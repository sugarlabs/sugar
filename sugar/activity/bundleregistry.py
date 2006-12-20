import os
from ConfigParser import ConfigParser

from sugar.activity.bundle import Bundle
from sugar import env
from sugar import util

class _ServiceManager(object):
    def __init__(self):
        self._path = env.get_user_service_dir()

    def add(self, bundle):
        name = bundle.get_service_name()

        # FIXME evil hack. Probably need to fix Exec spec
        full_exec = env.get_shell_bin_dir() + '/' + bundle.get_exec()
        full_exec += ' ' + bundle.get_path()

        util.write_service(name, full_exec, self._path)

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

    def find_by_default_type(self, default_type):
        """Find a bundle by the network service default type"""
        for bundle in self._bundles.values():
            if bundle.get_default_type() == default_type:
                return bundle
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
