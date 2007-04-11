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
from ConfigParser import ConfigParser

from sugar import env

_PYTHON_FACTORY='sugar-activity-factory'

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
        self._name = None
        self._icon = None
        self._service_name = None
        self._show_launcher = True
        self._valid = True
        self._path = path
        self._activity_version = 0

        info_path = os.path.join(path, 'activity', 'activity.info')
        if os.path.isfile(info_path):
            self._parse_info(info_path)
        else:
            self._valid = False

        linfo_path = self._get_linfo_path()
        if linfo_path and os.path.isfile(linfo_path):
            self._parse_linfo(linfo_path)

    def _parse_info(self, info_path):
        cp = ConfigParser()
        cp.read([info_path])

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
            self._class = cp.get(section, 'class')
            self._exec = '%s --bundle-path="%s"' % (
              env.get_bin_path(_PYTHON_FACTORY), self.get_path())
        elif cp.has_option(section, 'exec'):
            self._class = None
            self._exec = cp.get(section, 'exec')
        else:
            self._exec = None
            self._valid = False
            logging.error('%s must specify exec or class' % self._path)

        if cp.has_option(section, 'show_launcher'):
            if cp.get(section, 'show_launcher') == 'no':
                self._show_launcher = False

        if cp.has_option(section, 'icon'):
            icon = cp.get(section, 'icon')
            activity_path = os.path.join(self._path, 'activity')
            self._icon = os.path.join(activity_path, icon + ".svg")

        if cp.has_option(section, 'activity_version'):
            self._activity_version = int(cp.get(section, 'activity_version'))

    def _parse_linfo(self, linfo_path):
        cp = ConfigParser()
        cp.read([linfo_path])

        section = 'Activity'

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')

    def _get_linfo_path(self):
        path = None
        lang = locale.getdefaultlocale()[0]
        if lang != None:
            path = os.path.join(self.get_locale_path(), lang)
            if not os.path.isdir(path):
                path = os.path.join(self._path, 'locale', lang[:2])
                if not os.path.isdir(path):
                    path = None

        if path:
            return os.path.join(path, 'activity.linfo')
        else:
            return None

    def is_valid(self):
        return self._valid

    def get_locale_path(self):
        """Get the locale path inside the activity bundle."""
        return os.path.join(self._path, 'locale')

    def get_path(self):
        """Get the activity bundle path."""
        return self._path

    def get_name(self):
        """Get the activity user visible name."""
        return self._name

    def get_service_name(self):
        """Get the activity service name"""
        return self._service_name

    def get_object_path(self):
        """Get the path to the service object"""
        return '/' + self._service_name.replace('.', '/')

    def get_default_type(self):
        """Get the type of the main network service which tracks presence
           and provides info about the activity, for example the title."""
        splitted = self.get_service_name().split('.')
        splitted.reverse()
        return '_' + '_'.join(splitted) + '._udp'

    def get_icon(self):
        """Get the activity icon name"""
        return self._icon

    def get_activity_version(self):
        """Get the activity version"""
        return self._activity_version

    def get_exec(self):
        """Get the command to execute to launch the activity factory"""
        return self._exec

    def get_class(self):
        """Get the main Activity class"""
        return self._class

    def get_show_launcher(self):
        """Get whether there should be a visible launcher for the activity"""
        return self._show_launcher
