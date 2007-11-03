# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import logging

import gobject

from sugar.bundle.activitybundle import ActivityBundle
from sugar.bundle.bundle import MalformedBundleException
from sugar import env
from sugar import util

# http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
def _get_data_dirs():
    if os.environ.has_key('XDG_DATA_DIRS'):
        return os.environ['XDG_DATA_DIRS'].split(':')
    else:
        return [ '/usr/local/share/', '/usr/share/' ]

def _load_mime_defaults():
    defaults = {}

    f = open(env.get_data_path('mime.defaults'), 'r')
    for line in f.readlines():
        line = line.strip()
        if line and not line.startswith('#'):
            mime = line[:line.find(' ')]
            handler = line[line.rfind(' ') + 1:]
            defaults[mime] = handler
    f.close()

    return defaults

class BundleRegistry(gobject.GObject):
    """Service that tracks the available activity bundles"""

    __gsignals__ = {
        'bundle-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'bundle-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        
        self._bundles = []
        self._search_path = []
        self._mime_defaults = _load_mime_defaults()

    def get_bundle(self, bundle_id):
        """Returns an bundle given his service name"""
        for bundle in self._bundles:
            if bundle.get_bundle_id() == bundle_id:
                return bundle
        return None

    def add_search_path(self, path):
        """Add a directory to the bundles search path"""
        self._search_path.append(path)
        self._scan_directory(path)
    
    def __iter__(self):
        return self._bundles.__iter__()

    def _scan_directory(self, path):
        if not os.path.isdir(path):
            return

        # Sort by mtime to ensure a stable activity order
        bundles = {}
        for f in os.listdir(path):
            if not f.endswith('.activity'):
                continue
            try:
                bundle_dir = os.path.join(path, f)
                if os.path.isdir(bundle_dir):
                    bundles[bundle_dir] = os.stat(bundle_dir).st_mtime
            except Exception, e:
                logging.error('Error while processing installed activity ' \
                              'bundle: %s, %s, %s' % (f, e.__class__, e))

        bundle_dirs = bundles.keys()
        bundle_dirs.sort(lambda d1,d2: cmp(bundles[d1], bundles[d2]))
        for dir in bundle_dirs:
            try:
                self.add_bundle(dir)
            except Exception, e:
                logging.error('Error while processing installed activity ' \
                              'bundle: %s, %s, %s' % (dir, e.__class__, e))

    def add_bundle(self, bundle_path):
        try:
            bundle = ActivityBundle(bundle_path)
        except MalformedBundleException:
            return False

        self._bundles.append(bundle)
        self.emit('bundle-added', bundle)
        return True

    def remove_bundle(self, bundle_path):
        for bundle in self._bundles:
            if bundle.get_path() == bundle_path:
                self._bundles.remove(bundle)
                self.emit('bundle-removed', bundle)
                return True
        return False

    def get_activities_for_type(self, mime_type):
        result = []
        for bundle in self._bundles:
            if bundle.get_mime_types() and mime_type in bundle.get_mime_types():
                if self.get_default_for_type(mime_type) == bundle.get_bundle_id():
                    result.insert(0, bundle)
                else:
                    result.append(bundle)
        return result

    def get_default_for_type(self, mime_type):
        if self._mime_defaults.has_key(mime_type):
            return self._mime_defaults[mime_type]
        else:
            return None

def get_registry():
    return _bundle_registry

_bundle_registry = BundleRegistry()

for path in _get_data_dirs():
    bundles_path = os.path.join(path, 'activities')
    _bundle_registry.add_search_path(bundles_path)

_bundle_registry.add_search_path(env.get_user_activities_path())
