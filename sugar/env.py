# Copyright (C) 2006, Red Hat, Inc.
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
import sys
import pwd

try:
    from sugar.__uninstalled__ import *
except ImportError:
    from sugar.__installed__ import *

def get_bundle_path():
    if os.environ.has_key('SUGAR_BUNDLE_PATH'):
        return os.environ['SUGAR_BUNDLE_PATH']
    else:
        return None

def get_profile_path():
    if os.environ.has_key('SUGAR_PROFILE'):
        profile_id = os.environ['SUGAR_PROFILE']
    else:
        profile_id = 'default'

    path = os.path.join(os.path.expanduser('~/.sugar'), profile_id)
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError, exc:
            print "Could not create user directory."

    return path

def get_data_dir():
    return sugar_data_dir

def get_services_dir():
    return sugar_services_dir

def get_shell_bin_dir():
    return sugar_shell_bin_dir

# http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
def get_data_dirs():
    if os.environ.has_key('XDG_DATA_DIRS'):
        return os.environ['XDG_DATA_DIRS'].split(':')
    else:
        return [ '/usr/local/share/', '/usr/share/' ]

def get_user_service_dir():
    service_dir = os.path.expanduser('~/.local/share/dbus-1/services')
    if not os.path.isdir(service_dir):
        os.makedirs(service_dir)
    return service_dir
