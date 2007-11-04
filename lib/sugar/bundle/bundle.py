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

"""Sugar bundle file handler"""

import os
import StringIO
import zipfile

class AlreadyInstalledException(Exception): pass
class NotInstalledException(Exception): pass
class InvalidPathException(Exception): pass
class ZipExtractException(Exception): pass
class RegistrationException(Exception): pass
class MalformedBundleException(Exception): pass

class Bundle:
    """A Sugar activity, content module, etc.
    
    The bundle itself may be either a zip file or a directory
    hierarchy, with metadata about the bundle stored various files
    inside it.

    This is an abstract base class. See ActivityBundle and
    ContentBundle for more details on those bundle types.
    """
    def __init__(self, path):
        self._path = path

        if os.path.isdir(self._path):
            self._unpacked = True
        else:
            self._unpacked = False
            self._check_zip_bundle()

        # manifest = self._get_file(self._infodir + '/contents')
        # if manifest is None:
        #     raise MalformedBundleException('No manifest file')
        # 
        # signature = self._get_file(self._infodir + '/contents.sig')
        # if signature is None:
        #     raise MalformedBundleException('No signature file')

    def _check_zip_bundle(self):
        zip_file = zipfile.ZipFile(self._path)
        file_names = zip_file.namelist()
        if len(file_names) == 0:
            raise MalformedBundleException('Empty zip file')

        if file_names[0] == 'mimetype':
            del file_names[0]

        self._zip_root_dir = file_names[0].split('/')[0]
        if self._unzipped_extension is not None:
            (name, ext) = os.path.splitext(self._zip_root_dir)
            if ext != self._unzipped_extension:
                raise MalformedBundleException(
                    'All files in the bundle must be inside a single ' +
                    'directory whose name ends with "%s"' %
                    self._unzipped_extension)

        for file_name in file_names:
            if not file_name.startswith(self._zip_root_dir):
                raise MalformedBundleException(
                    'All files in the bundle must be inside a single ' +
                    'top-level directory')

    def _get_file(self, filename):
        file = None

        if self._unpacked:
            path = os.path.join(self._path, filename)
            if os.path.isfile(path):
                file = open(path)
        else:
            zip_file = zipfile.ZipFile(self._path)
            path = os.path.join(self._zip_root_dir, filename)
            try:
                data = zip_file.read(path)
                file = StringIO.StringIO(data)
            except KeyError:
                # == "file not found"
                pass
            zip_file.close()

        return file

    def get_path(self):
        """Get the bundle path."""
        return self._path

    def _unzip(self, install_dir):
        if self._unpacked:
            raise AlreadyInstalledException

        if not os.path.isdir(install_dir):
            os.mkdir(install_dir)

        # zipfile provides API that in theory would let us do this
        # correctly by hand, but handling all the oddities of
        # Windows/UNIX mappings, extension attributes, deprecated
        # features, etc makes it impractical.
        # FIXME: use manifest
        if os.spawnlp(os.P_WAIT, 'unzip', 'unzip', '-o', self._path,
                      '-x', 'mimetype', '-d', install_dir):
            raise ZipExtractException

    def _zip(self, bundle_path):
        if not self._unpacked:
            raise NotInstalledException

        # FIXME: use manifest
        zip = zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(self._path):
            for name in files:
                zip.write(filename, os.path.join(base_dir, filename))
        zip.close()

    def _uninstall(self, install_path):
        if not os.path.isdir(install_path):
            raise InvalidPathException
        if self._unzipped_extension is not None:
            ext = os.path.splitext(install_path)[1]
            if ext != self._unzipped_extension:
                raise InvalidPathException

        for root, dirs, files in os.walk(install_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(install_path)
