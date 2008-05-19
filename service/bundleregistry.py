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
import simplejson

from sugar.bundle.activitybundle import ActivityBundle
from sugar.bundle.bundle import MalformedBundleException
from sugar import env

import config

class BundleRegistry(gobject.GObject):
    """Service that tracks the available activity bundles"""

    __gsignals__ = {
        'bundle-added':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT])),
        'bundle-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT])),
        'bundle-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._mime_defaults = self._load_mime_defaults()

        self._bundles = []
        for activity_dir in self._get_activity_directories():
            self._scan_directory(activity_dir)

        self._last_defaults_mtime = -1
        self._favorite_bundles = self._load_favorites()
        self._merge_default_favorites()

    def _get_activity_directories(self):
        directories = []
        if os.environ.has_key('SUGAR_ACTIVITIES'):
            directories.extend(os.environ['SUGAR_ACTIVITIES'].split(':'))

        directories.append(env.get_user_activities_path())

        return directories

    def _load_mime_defaults(self):
        defaults = {}

        f = open(os.path.join(config.data_path, 'mime.defaults'), 'r')
        for line in f.readlines():
            line = line.strip()
            if line and not line.startswith('#'):
                mime = line[:line.find(' ')]
                handler = line[line.rfind(' ') + 1:]
                defaults[mime] = handler
        f.close()

        return defaults

    def _load_favorites(self):
        favorite_bundles = []
        favorites_path = env.get_profile_path('favorite_activities')
        if os.path.exists(favorites_path):
            try:
                favorites_data = simplejson.load(open(favorites_path))
            except ValueError, e:
                logging.error('Error while loading favorite_activities: %r.' %
                              e)
            else:
                # Old structure used to be a list, instead of a dictionary.
                if isinstance(favorites_data, list):
                    favorite_bundles = favorites_data
                else:
                    favorite_bundles = favorites_data['favorites']
                    self._last_defaults_mtime = favorites_data['defaults-mtime']

        return favorite_bundles

    def _merge_default_favorites(self):
        default_activities = []
        defaults_path = os.path.join(config.data_path, 'activities.defaults')
        if os.path.exists(defaults_path):
            file_mtime = os.stat(defaults_path).st_mtime
            if file_mtime > self._last_defaults_mtime:
                f = open(defaults_path, 'r')
                for line in f.readlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        default_activities.append(line)
                f.close()
                self._last_defaults_mtime = file_mtime

        if not default_activities:
            return

        for bundle_id in default_activities:
            max_version = -1
            for bundle in self._bundles:
                if bundle.get_bundle_id() == bundle_id and \
                        max_version < bundle.get_activity_version():
                    max_version = bundle.get_activity_version()

            if max_version > -1 and \
                    (bundle_id, max_version) not in self._favorite_bundles:
                self._favorite_bundles.append([bundle_id, max_version])

        logging.debug('After merging: %r' % self._favorite_bundles)

        self._write_favorites_file()

    def get_bundle(self, bundle_id):
        """Returns an bundle given his service name"""
        for bundle in self._bundles:
            if bundle.get_bundle_id() == bundle_id:
                return bundle
        return None
    
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
        bundle_dirs.sort(lambda d1, d2: cmp(bundles[d1], bundles[d2]))
        for folder in bundle_dirs:
            try:
                self.add_bundle(folder)
            except Exception, e:
                logging.error('Error while processing installed activity ' \
                              'bundle: %s, %s, %s' % (folder, e.__class__, e))

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
                if self.get_default_for_type(mime_type) == \
                        bundle.get_bundle_id():
                    result.insert(0, bundle)
                else:
                    result.append(bundle)
        return result

    def get_default_for_type(self, mime_type):
        if self._mime_defaults.has_key(mime_type):
            return self._mime_defaults[mime_type]
        else:
            return None

    def _find_bundle(self, bundle_id, version):
        for bundle in self._bundles:
            if bundle.get_bundle_id() == bundle_id and \
                    bundle.get_activity_version() == version:
                return bundle
        raise ValueError('No bundle %r with version %r exists.' % \
                (bundle_id, version))

    def set_bundle_favorite(self, bundle_id, version, favorite):
        bundle = self._find_bundle(bundle_id, version)
        if favorite and not [bundle_id, version] in self._favorite_bundles:
            self._favorite_bundles.append([bundle_id, version])
            self.emit('bundle-changed', bundle)
            self._write_favorites_file()
        elif not favorite and [bundle_id, version] in self._favorite_bundles:
            self._favorite_bundles.remove([bundle_id, version])
            self.emit('bundle-changed', bundle)
            self._write_favorites_file()

    def is_bundle_favorite(self, bundle_id, version):
        return [bundle_id, version] in self._favorite_bundles

    def _write_favorites_file(self):
        path = env.get_profile_path('favorite_activities')
        favorites_data = {'defaults-mtime': self._last_defaults_mtime,
                          'favorites': self._favorite_bundles}
        simplejson.dump(favorites_data, open(path, 'w'))

_instance = None

def get_registry():
    global _instance
    if not _instance:
        _instance = BundleRegistry()
    return _instance

