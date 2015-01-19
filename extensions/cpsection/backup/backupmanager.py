# Copyright (c) 2013 Gonzalo Odiard
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
import logging
from importlib import import_module

from jarabe.model import shell
from jarabe import config

# we need import the backends from the extensions path
sys.path.append(config.ext_path)

BACKENDS_MODULE = 'cpsection.backup.backends'


OPERATION_BACKUP = 'backup'
OPERATION_RESTORE = 'restore'


class BackupManager():

    def __init__(self):
        manager_path = os.path.dirname(os.path.abspath(
            sys.modules[BackupManager.__module__].__file__))
        self._backends = []
        self._selected_backend = None

        # look for available backends
        backends_path = os.path.join(manager_path, 'backends')
        for file_name in os.listdir(backends_path):
            if file_name.endswith('.py'):
                module_name = file_name[:-3]  # remove '.py'
                module = _load_module(module_name)
                if module is not None:
                    if hasattr(module, 'get_name'):
                        logging.error('FOUND BACKEND %s', module.get_name())
                        self._backends.append(module)

    def get_backends(self):
        return self._backends

    def get_selected_backend(self):
        return self._selected_backend

    def set_selected_backend(self, selected_backend):
        self._selected_backend = selected_backend

    def need_stop_activities(self):
        return len(shell.get_model()) > 1


def _load_module(module):
    try:
        module = import_module('%s.%s' % (BACKENDS_MODULE, module))
    except ImportError as e:
        module = None
        logging.error('ImportError: %s' % (e))
    return module
