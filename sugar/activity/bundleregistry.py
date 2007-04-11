# Copyright (C) 2007, Red Hat, Inc.
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

import gobject

from sugar.activity.bundle import Bundle
from sugar import env
from sugar import util

# http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
def _get_data_dirs():
    if os.environ.has_key('XDG_DATA_DIRS'):
        return os.environ['XDG_DATA_DIRS'].split(':')
    else:
        return [ '/usr/local/share/', '/usr/share/' ]

class _ServiceManager(object):
    """Internal class responsible for creating dbus service files
    
    DBUS services are defined in files which bind a service name 
    to the name of an executable which provides the service name.
    
    In Sugar, the service files are automatically generated from 
    the activity registry (by this class).  When an activity's 
    dbus launch service is requested, dbus will launch the 
    specified executable in order to allow it to provide the 
    requested activity-launching service.
    
    In the case of activities which provide a "class", instead of 
    an "exec" attribute in their activity.info, the 
    sugar-activity-factory script is used with an appropriate 
    argument to service that bundle.
    """
    SERVICE_DIRECTORY = '~/.local/share/dbus-1/services'
    def __init__(self):
        service_dir = os.path.expanduser(self.SERVICE_DIRECTORY)
        if not os.path.isdir(service_dir):
            os.makedirs(service_dir)

        self._path = service_dir

    def add(self, bundle):
        util.write_service(bundle.get_service_name(),
                           bundle.get_exec(), self._path)

class BundleRegistry(gobject.GObject):
    """Service that tracks the available activity bundles"""

    __gsignals__ = {
        'bundle-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        
        self._bundles = {}
        self._search_path = []
        self._service_manager = _ServiceManager()

    def find_bundle(self, key):
        """Find a bundle in the registry"""
        key = key.lower()

        for bundle in self._bundles.values():
            name = bundle.get_name().lower()
            service_name = bundle.get_service_name().lower()
            if name.find(key) != -1 or service_name.find(key) != -1:
                return bundle

        return None

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
                    self.add_bundle(bundle_dir)

    def add_bundle(self, bundle_path):
        bundle = Bundle(bundle_path)
        if bundle.is_valid():
            self._bundles[bundle.get_service_name()] = bundle
            self._service_manager.add(bundle)
            self.emit('bundle-added', bundle)
            return True
        else:
            return False

def get_registry():
    return _bundle_registry

_bundle_registry = BundleRegistry()

for path in _get_data_dirs():
    bundles_path = os.path.join(path, 'activities')
    _bundle_registry.add_search_path(bundles_path)

_bundle_registry.add_search_path(env.get_user_activities_path())
