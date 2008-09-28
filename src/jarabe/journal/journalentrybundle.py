# Copyright (C) 2007, One Laptop Per Child
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
import tempfile
import shutil

import json

import dbus
from sugar.datastore import datastore
from sugar.bundle.bundle import Bundle, MalformedBundleException

class JournalEntryBundle(Bundle):
    """A Journal entry bundle

    See http://wiki.laptop.org/go/Journal_entry_bundles for details
    """

    MIME_TYPE = 'application/vnd.olpc-journal-entry'

    _zipped_extension = '.xoj'
    _unzipped_extension = None
    _infodir = None

    def __init__(self, path):
        Bundle.__init__(self, path)

    def install(self):
        if os.environ.has_key('SUGAR_ACTIVITY_ROOT'):
            install_dir = os.path.join(os.environ['SUGAR_ACTIVITY_ROOT'],
                                       'data')
        else:
            install_dir = tempfile.gettempdir()
        bundle_dir = os.path.join(install_dir, self._zip_root_dir)
        uid = self._zip_root_dir
        self._unzip(install_dir)
        try:
            metadata = self._read_metadata(bundle_dir)
            jobject = datastore.create()
            try:
                for key, value in metadata.iteritems():
                    jobject.metadata[key] = value

                preview = self._read_preview(uid, bundle_dir)
                if preview is not None:
                    jobject.metadata['preview'] = dbus.ByteArray(preview)

                jobject.metadata['uid'] = ''
                jobject.file_path = os.path.join(bundle_dir, uid)
                datastore.write(jobject)
            finally:
                jobject.destroy()
        finally:
            shutil.rmtree(bundle_dir, ignore_errors=True)

    def _read_metadata(self, bundle_dir):
        metadata_path = os.path.join(bundle_dir, '_metadata.json')
        if not os.path.exists(metadata_path):
            raise MalformedBundleException(
                    'Bundle must contain the file "_metadata.json"')
        f = open(metadata_path, 'r')
        try:
            json_data = f.read()
        finally:
            f.close()
        return json.read(json_data)

    def _read_preview(self, uid, bundle_dir):
        preview_path = os.path.join(bundle_dir, 'preview', uid)
        if not os.path.exists(preview_path):
            return ''
        f = open(preview_path, 'r')
        try:
            preview_data = f.read()
        finally:
            f.close()
        return preview_data

    def is_installed(self):
        # These bundles can be reinstalled as many times as desired.
        return False

