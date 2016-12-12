# Copyright (C) 2007, One Laptop Per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import tempfile
import shutil

import json
import dbus

from sugar3.bundle.bundle import Bundle, MalformedBundleException

from jarabe.journal import model


class JournalEntryBundle(Bundle):
    """A Journal entry bundle

    See http://wiki.laptop.org/go/Journal_entry_bundles for details
    """

    MIME_TYPE = 'application/vnd.olpc-journal-entry'

    _zipped_extension = '.xoj'
    _unzipped_extension = None
    _infodir = None

    def __init__(self, path, uid=None):
        """
        Instantiate a Journal Entry Bundle from the given path to a xoj file.
        If provided, the specified uid will be used as the uid of the journal
        entry if/when this bundle is later installed.
        """
        Bundle.__init__(self, path)
        self._uid = uid

    def install(self):
        if 'SUGAR_ACTIVITY_ROOT' in os.environ:
            install_dir = os.path.join(os.environ['SUGAR_ACTIVITY_ROOT'],
                                       'data')
        else:
            install_dir = tempfile.gettempdir()
        bundle_dir = os.path.join(install_dir, self._zip_root_dir)
        temp_uid = self._zip_root_dir
        self._unzip(install_dir)
        try:
            metadata = self._read_metadata(bundle_dir)
            metadata['uid'] = self._uid if self._uid else temp_uid

            preview = self._read_preview(temp_uid, bundle_dir)
            if preview is not None:
                metadata['preview'] = dbus.ByteArray(preview)

            file_path = os.path.join(bundle_dir, temp_uid)
            model.write(metadata, file_path)
        finally:
            shutil.rmtree(bundle_dir, ignore_errors=True)

    def get_bundle_id(self):
        return None

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
        return json.loads(json_data)

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
