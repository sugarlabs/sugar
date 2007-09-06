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

"""Metadata description of a given application/activity"""

import logging
import locale
import os
import zipfile
from ConfigParser import ConfigParser
import StringIO
import tempfile

import dbus

from sugar import env
from sugar import activity
from sugar.bundle.bundle import AlreadyInstalledException, \
     NotInstalledException, InvalidPathException, ZipExtractException, \
     RegistrationException, MalformedBundleException

_PYTHON_FACTORY='sugar-activity-factory'

_DBUS_SHELL_SERVICE = "org.laptop.Shell"
_DBUS_SHELL_PATH = "/org/laptop/Shell"
_DBUS_ACTIVITY_REGISTRY_IFACE = "org.laptop.Shell.ActivityRegistry"

class Bundle:
    """Metadata description of a given application/activity
    
    The metadata is normally read from an activity.info file,
    which is an INI-style configuration file read using the 
    standard Python ConfigParser module.
    
    The format reference for the Bundle definition files is 
    available for further reference:
    
        http://wiki.laptop.org/go/Activity_bundles
    """
    def __init__(self, path):
        self._init_with_path(path)

    def _init_with_path(self, path):
        self.activity_class = None
        self.bundle_exec = None

        self._name = None
        self._icon = None
        self._service_name = None
        self._mime_types = None
        self._show_launcher = True
        self._valid = True
        self._path = path
        self._activity_version = 0

        info_file = self._get_info_file()
        if info_file:
            self._parse_info(info_file)
        else:
            self._valid = False

        linfo_file = self._get_linfo_file()
        if linfo_file:
            self._parse_linfo(linfo_file)

    def _get_info_file(self):
        info_file = None

        if os.path.isdir(self._path):
            info_path = os.path.join(self._path, 'activity', 'activity.info')
            if os.path.isfile(info_path):
                info_file = open(info_path)
        else:
            zip_file = zipfile.ZipFile(self._path)
            file_names = zip_file.namelist()
            root_dir = self._get_bundle_root_dir(file_names)
            info_path = os.path.join(root_dir, 'activity', 'activity.info')
            if info_path in file_names:
                info_data = zip_file.read(info_path)
                info_file = StringIO.StringIO(info_data)
            zip_file.close()

        return info_file

    def _parse_info(self, info_file):
        cp = ConfigParser()
        cp.readfp(info_file)

        section = 'Activity'

        if cp.has_option(section, 'service_name'):
            self._service_name = cp.get(section, 'service_name')
        else:
            self._valid = False
            logging.error('%s must specify a service name' % self._path)

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')
        else:
            self._valid = False
            logging.error('%s must specify a name' % self._path)

        if cp.has_option(section, 'class'):
            self.activity_class = cp.get(section, 'class')
        elif cp.has_option(section, 'exec'):
            self.bundle_exec = cp.get(section, 'exec')
        else:
            self._valid = False
            logging.error('%s must specify exec or class' % self._path)

        if cp.has_option(section, 'mime_types'):
            mime_list = cp.get(section, 'mime_types')
            self._mime_types = mime_list.strip(';').split(';')

        if cp.has_option(section, 'show_launcher'):
            if cp.get(section, 'show_launcher') == 'no':
                self._show_launcher = False

        if cp.has_option(section, 'icon'):
            self._icon = cp.get(section, 'icon')

        if cp.has_option(section, 'activity_version'):
            version = cp.get(section, 'activity_version')
            try:
                self._activity_version = int(version)
            except ValueError:
                self._valid = False

    def _parse_linfo(self, linfo_file):
        cp = ConfigParser()
        cp.readfp(linfo_file)

        section = 'Activity'

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')

    def _get_linfo_file(self):
        linfo_file = None

        lang = locale.getdefaultlocale()[0]
        if not lang:
            return None

        if os.path.isdir(self._path):
            linfo_path = os.path.join(self.get_locale_path(), lang, 'activity.linfo')
            if not os.path.isfile(linfo_path):
                linfo_path = os.path.join(self.get_locale_path(), lang[:2], 'activity.linfo')
            if os.path.isfile(linfo_path):
                linfo_file = open(linfo_path)
        else:
            zip_file = zipfile.ZipFile(self._path)
            file_names = zip_file.namelist()
            root_dir = self._get_bundle_root_dir(file_names)
            linfo_path = os.path.join(root_dir, 'locale', lang, 'activity.linfo')
            if not linfo_path in file_names:
                linfo_path = os.path.join(root_dir, 'locale', lang[:2], 'activity.linfo')
            if linfo_path in zip_file.namelist():                
                linfo_data = zip_file.read(linfo_path)
                linfo_file = StringIO.StringIO(linfo_data)

            zip_file.close()

        return linfo_file

    def is_valid(self):
        return self._valid

    def get_locale_path(self):
        """Get the locale path inside the activity bundle."""
        return os.path.join(self._path, 'locale')

    def get_icons_path(self):
        """Get the icons path inside the activity bundle."""
        return os.path.join(self._path, 'icons')

    def get_path(self):
        """Get the activity bundle path."""
        return self._path

    def get_name(self):
        """Get the activity user visible name."""
        return self._name

    def get_service_name(self):
        """Get the activity service name"""
        return self._service_name

    def get_icon(self):
        """Get the activity icon name"""
        if os.path.isdir(self._path):
            activity_path = os.path.join(self._path, 'activity')
            return os.path.join(activity_path, self._icon + '.svg')
        else:
            zip_file = zipfile.ZipFile(self._path)
            file_names = zip_file.namelist()
            root_dir = self._get_bundle_root_dir(file_names)
            icon_path = os.path.join(root_dir, 'activity', self._icon + '.svg')
            if icon_path in file_names:
                icon_data = zip_file.read(icon_path)
                temp_file, temp_file_path = tempfile.mkstemp(suffix='.svg', prefix=self._icon)
                os.write(temp_file, icon_data)
                os.close(temp_file)
                return temp_file_path
            else:
                return None

    def get_activity_version(self):
        """Get the activity version"""
        return self._activity_version

    def get_command(self):
        """Get the command to execute to launch the activity factory"""
        if self.bundle_exec:
            command = os.path.join(self._path, self.bundle_exec)
            command = command.replace('$SUGAR_BUNDLE_PATH', self._path)
            command = os.path.expandvars(command)
        else:
            command = '%s --bundle-path="%s"' % (
                  env.get_bin_path(_PYTHON_FACTORY), self._path)

        return command

    def get_class(self):
        """Get the main Activity class"""
        return self._class

    def get_mime_types(self):
        """Get the MIME types supported by the activity"""
        return self._mime_types

    def get_show_launcher(self):
        """Get whether there should be a visible launcher for the activity"""
        return self._show_launcher

    def is_installed(self):
        if self._valid and activity.get_registry().get_activity(self._service_name):
            return True
        else:
            return False

    def _get_bundle_root_dir(self, file_names):
        """
        We check here that all the files in the .xo are inside one only dir
        (bundle_root_dir).
        """
        bundle_root_dir = None
        for file_name in file_names:
            if not bundle_root_dir:
                bundle_root_dir = file_name.split('/')[0]
                if not bundle_root_dir.endswith('.activity'):
                    raise MalformedBundleException(
                            'The activity directory name must end with .activity')
            else:
                if not file_name.startswith(bundle_root_dir):
                    raise MalformedBundleException(
                        'All files in the bundle must be inside the activity directory')

        return bundle_root_dir

    def install(self):
        if self.is_installed():
            raise AlreadyInstalledException

        ext = os.path.splitext(self._path)[1]
        if not os.path.isfile(self._path):
            raise InvalidPathException

        bundle_dir = env.get_user_activities_path()
        if not os.path.isdir(bundle_dir):
            os.mkdir(bundle_dir)

        zip_file = zipfile.ZipFile(self._path)
        file_names = zip_file.namelist()
        bundle_root_dir = self._get_bundle_root_dir(file_names)
        bundle_path = os.path.join(bundle_dir, bundle_root_dir)

        if os.spawnlp(os.P_WAIT, 'unzip', 'unzip', self._path, '-d', bundle_dir):
            raise ZipExtractException

        self._init_with_path(bundle_path)

        if not activity.get_registry().add_bundle(bundle_path):
            raise RegistrationException

    def deinstall(self):
        if not self.is_installed():
            raise NotInstalledException

        ext = os.path.splitext(self._path)[1]
        if not os.path.isfile(self._path) or ext != '.activity':
            raise InvalidPathException

        for root, dirs, files in os.walk(self._path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self._path)

        self._init_with_path(None)

        # TODO: notify shell

