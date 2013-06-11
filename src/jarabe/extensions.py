# Copyright (C) 2013, Sugar Labs
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
import imp
import logging

from jarabe import config


def get_paths():
    # TODO: add os.path.join(os.path.expanduser('~'), '.sugar',
    # 'extensions') but first we need to figure out why the imports
    # fail with multiple paths.
    return [config.ext_path]


def get_cpsection_paths():
    return [os.path.join(path, 'cpsection') for path in get_paths()]


def get_deviceicon_paths():
    return [os.path.join(path, 'deviceicon') for path in get_paths()]


def get_globalkey_paths():
    return [os.path.join(path, 'globalkey') for path in get_paths()]


def get_webservice_paths():
    return [os.path.join(path, 'webservice') for path in get_paths()]


def load_module(path, module):
    mod = None
    fd = None

    try:
        fd, fpath, desc = imp.find_module(module, [path])
        mod = imp.load_module(module, fd, fpath, desc)
        logging.debug(mod)
    except IOError, e:
        logging.debug('IOError: %s' % (e))
    except ImportError, e:
        logging.debug('ImportError: %s' % (e))
    finally:
        if fd is not None:
            fd.close()

    return mod
