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

"""Sugar activity bundles"""

from ConfigParser import ConfigParser
import locale
import os
import tempfile

from sugar.bundle.bundle import Bundle, MalformedBundleException
from sugar import activity
from sugar import env

class ActivityBundle(Bundle):
    """A Sugar activity bundle
    
    See http://wiki.laptop.org/go/Activity_bundles for details
    """

    MIME_TYPE = 'application/vnd.olpc-sugar'
    DEPRECATED_MIME_TYPE = 'application/vnd.olpc-x-sugar'

    _zipped_extension = '.xo'
    _unzipped_extension = '.activity'
    _infodir = 'activity'

    def __init__(self, path):
        Bundle.__init__(self, path)
        self.activity_class = None
        self.bundle_exec = None
        
        self._name = None
        self._icon = None
        self._service_name = None
        self._mime_types = None
        self._show_launcher = True
        self._activity_version = 0

        info_file = self._get_file('activity/activity.info')
        if info_file is None:
            raise MalformedBundleException('No activity.info file')
        self._parse_info(info_file)

        linfo_file = self._get_linfo_file()
        if linfo_file:
            self._parse_linfo(linfo_file)

    def _parse_info(self, info_file):
        cp = ConfigParser()
        cp.readfp(info_file)

        section = 'Activity'

        if cp.has_option(section, 'service_name'):
            self._service_name = cp.get(section, 'service_name')
        else:
            raise MalformedBundleException(
                'Activity bundle %s does not specify a service name' %
                self._path)

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')
        else:
            raise MalformedBundleException(
                'Activity bundle %s does not specify a name' % self._path)

        # FIXME class is deprecated
        if cp.has_option(section, 'class'):
            self.activity_class = cp.get(section, 'class')
        elif cp.has_option(section, 'exec'):
            self.bundle_exec = cp.get(section, 'exec')
        else:
            raise MalformedBundleException(
                'Activity bundle %s must specify either class or exec' %
                self._path)

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
                raise MalformedBundleException(
                    'Activity bundle %s has invalid version number %s' %
                    (self._path, version))

    def _get_linfo_file(self):
        lang = locale.getdefaultlocale()[0]
        if not lang:
            return None

        linfo_path = os.path.join('locale', lang, 'activity.linfo')
        linfo_file = self._get_file(linfo_path)
        if linfo_file is not None:
            return linfo_file

        linfo_path = os.path.join('locale', lang[:2], 'activity.linfo')
        linfo_file = self._get_file(linfo_path)
        if linfo_file is not None:
            return linfo_file

        return None

    def _parse_linfo(self, linfo_file):
        cp = ConfigParser()
        cp.readfp(linfo_file)

        section = 'Activity'

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')

    def get_locale_path(self):
        """Get the locale path inside the (installed) activity bundle."""
        if not self._unpacked:
            raise NotInstalledException
        return os.path.join(self._path, 'locale')

    def get_icons_path(self):
        """Get the icons path inside the (installed) activity bundle."""
        if not self._unpacked:
            raise NotInstalledException
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

    # FIXME: this should return the icon data, not a filename, so that
    # we don't need to create a temp file in the zip case
    def get_icon(self):
        """Get the activity icon name"""
        icon_path = os.path.join('activity', self._icon + '.svg')
        if self._unpacked:
            return os.path.join(self._path, icon_path)
        else:
            icon_data = self._get_file(icon_path).read()
            temp_file, temp_file_path = tempfile.mkstemp(self._icon)
            os.write(temp_file, icon_data)
            os.close(temp_file)
            return temp_file_path

    def get_activity_version(self):
        """Get the activity version"""
        return self._activity_version

    def get_command(self):
        """Get the command to execute to launch the activity factory"""
        if self.bundle_exec:
            command = os.path.expandvars(self.bundle_exec)
        else:
            command = 'sugar-activity ' + self.activity_class

        return command


    def get_mime_types(self):
        """Get the MIME types supported by the activity"""
        return self._mime_types

    def get_show_launcher(self):
        """Get whether there should be a visible launcher for the activity"""
        return self._show_launcher

    def is_installed(self):
        if activity.get_registry().get_activity(self._service_name):
            return True
        else:
            return False

    def install(self):
        if self.is_installed():
            raise AlreadyInstalledException

        install_dir = env.get_user_activities_path()
        self._unzip(install_dir)

        install_path = os.path.join(install_dir, self._zip_root_dir)

        xdg_data_home = os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))

        mime_path = os.path.join(install_path, 'activity', 'mimetypes.xml')
        if os.path.isfile(mime_path):
            mime_dir = os.path.join(xdg_data_home, 'mime')
            mime_pkg_dir = os.path.join(mime_dir, 'packages')
            if not os.path.isdir(mime_pkg_dir):
                os.makedirs(mime_pkg_dir)
            installed_mime_path = os.path.join(mime_pkg_dir, '%s.xml' % self._service_name)
            os.symlink(mime_path, installed_mime_path)
            os.spawnlp(os.P_WAIT, 'update-mime-database',
                       'update-mime-database', mime_dir)

        mime_types = self.get_mime_types()
        if mime_types is not None:
            installed_icons_dir = os.path.join(xdg_data_home,
                                               'icons/sugar/scalable/mimetypes')
            if not os.path.isdir(installed_icons_dir):
                os.makedirs(installed_icons_dir)

            for mime_type in mime_types:
                mime_icon_base = os.path.join(install_path, 'activity',
                                              mime_type.replace('/', '-'))
                svg_file = mime_icon_base + '.svg'
                info_file = mime_icon_base + '.icon'
                if os.path.isfile(svg_file):
                    os.symlink(svg_file,
                               os.path.join(installed_icons_dir,
                                            os.path.basename(svg_file)))
                if os.path.isfile(info_file):
                    os.symlink(info_file,
                               os.path.join(installed_icons_dir,
                                            os.path.basename(info_file)))

        if not activity.get_registry().add_bundle(install_path):
            raise RegistrationException

    def uninstall(self):
        if self._unpacked:
            install_path = self._path
        else:
            if not self.is_installed():
                raise NotInstalledException
            install_path = os.path.join(env.get_user_activities_path(),
                                        self._zip_root_dir)

        xdg_data_home = os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))

        mime_dir = os.path.join(xdg_data_home, 'mime')
        installed_mime_path = os.path.join(mime_dir, 'packages', '%s.xml' % self._service_name)
        if os.path.exists(installed_mime_path):
            os.remove(installed_mime_path)
            os.spawnlp(os.P_WAIT, 'update-mime-database',
                       'update-mime-database', mime_dir)

        mime_types = self.get_mime_types()
        if mime_types is not None:
            installed_icons_dir = os.path.join(xdg_data_home,
                                               'icons/sugar/scalable/mimetypes')
            for file in os.listdir(installed_icons_dir):
                path = os.path.join(installed_icons_dir, file)
                if os.path.islink(path) and \
                   os.readlink(path).startswith(install_path):
                    os.remove(path)

        self._uninstall(install_path)
        
        if not activity.get_registry().remove_bundle(install_path):
            raise RegistrationException

