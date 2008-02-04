"""Calculates file-paths for the Sugar working environment"""
# Copyright (C) 2006-2007 Red Hat, Inc.
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

def get_prefix_path(base, path=None):
    if os.environ.has_key('SUGAR_PREFIX'):
        prefix = os.environ['SUGAR_PREFIX']
    else:
        raise RuntimeError("The SUGAR_PREFIX environment variable is not set.")

    if path:
        return os.path.join(prefix, base, path)
    else:
        return os.path.join(prefix, base)

def _get_sugar_path(base, path=None):
    if os.environ.has_key('SUGAR_PATH'):
        sugar_path = os.environ['SUGAR_PATH']
    else:
        raise RuntimeError("The SUGAR_PATH environment variable is not set.")

    if path:
        return os.path.join(sugar_path, base, path)
    else:
        return os.path.join(sugar_path, base)

def is_emulator():
    if os.environ.has_key('SUGAR_EMULATOR'):
        if os.environ['SUGAR_EMULATOR'] == 'yes':
            return True
    return False

def get_profile_path(path=None):
    if os.environ.has_key('SUGAR_PROFILE'):
        profile_id = os.environ['SUGAR_PROFILE']
    else:
        profile_id = 'default'

    base = os.path.join(os.path.expanduser('~/.sugar'), profile_id)
    if not os.path.isdir(base):
        try:
            os.makedirs(base, 0770)
        except OSError, exc:
            print "Could not create user directory."

    if path != None:
        return os.path.join(base, path)
    else:
        return base

def get_logs_path(path=None):
    base = get_profile_path('logs')
    if path != None:
        return os.path.join(base, path)
    else:
        return base

def get_user_activities_path():
    return os.path.expanduser('~/Activities')

def get_user_library_path():
    return os.path.expanduser('~/Library')

def get_locale_path(path=None):
    return get_prefix_path('share/locale', path)

def get_service_path(name):
    return _get_sugar_path('services', name)

def get_shell_path(path=None):
    return _get_sugar_path('shell', path)

def get_data_path(path=None):
    return _get_sugar_path('data', path)
