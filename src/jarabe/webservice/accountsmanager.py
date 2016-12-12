# Copyright (c) 2013 Walter Bender
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
import sys
import logging
import traceback
from importlib import import_module

from gi.repository import Gtk

from sugar3 import env

from jarabe import config
from jarabe.webservice.account import Account

_ACCOUNT_MODULE_NAME = 'account'
_user_extensions_path = os.path.join(env.get_profile_path(), 'extensions')

_module_repository = None


def _extend_sys_path():
    for path in [_user_extensions_path, config.ext_path]:
        if path not in sys.path and os.path.exists(path):
            sys.path.append(path)


def _get_webservice_paths():
    paths = []
    for path in [os.path.join(_user_extensions_path, 'webservice'),
                 os.path.join(config.ext_path, 'webservice')]:
        if os.path.exists(path):
            paths.append(path)
    return paths


def _get_webaccount_paths():
    paths = []
    for path in [os.path.join(_user_extensions_path, 'cpsection',
                              'webaccount'),
                 os.path.join(config.ext_path, 'cpsection', 'webaccount')]:
        if os.path.exists(path):
            paths.append(path)
    return paths


def _ensure_module_repository():
    ''' Ensure we have built a repository of the online account
    managers and related service modules.'''
    global _module_repository

    if _module_repository is not None:
        return

    _module_repository = {}

    _extend_sys_path()

    for path in _get_webservice_module_paths():
        service_name = _get_service_name(path)
        if service_name in _module_repository:
            continue

        service_module = _load_service_module(path, service_name)
        if service_module is None:
            continue

        _module_repository[service_name] = {'service': service_module}

        account_module = None
        module = _load_account_module(path)

        if module is not None and hasattr(module, 'get_account'):
            try:
                account_module = module.get_account()
            except Exception as e:
                logging.error('%s.get_account() failed: %s' %
                              (service_name, e))
                traceback.format_exc()

        if account_module is not None:
            _module_repository[service_name]['account'] = account_module
            _extend_icon_theme_search_path(path)
        else:
            del _module_repository[service_name]


def get_all_accounts():
    _ensure_module_repository()

    accounts = []
    for service, service_info in _module_repository.iteritems():
        accounts.append(service_info['account'])

    return accounts


def _get_service_name(service_path):
    ''' service path is of the form:
    /usr/share/sugar/extensions/webservice/my_service/my_service '''
    return os.path.basename(service_path)


def _get_webservice_module_paths():
    webservice_module_paths = []
    for webservice_path in _get_webservice_paths():
        for path in os.listdir(webservice_path):
            service_path = os.path.join(webservice_path, path)
            if os.path.isdir(service_path):
                webservice_module_paths.append(service_path)
    return webservice_module_paths


def _load_module(path, module):
    try:
        module = import_module(_convert_path_to_module_name(path, module),
                               [module])
    except ImportError as e:
        module = None
        logging.debug('ImportError: %s' % (e))

    return module


def _convert_path_to_module_name(path, module):
    if 'extensions' not in path:
        return ''

    parts = []
    while 'extensions' not in parts:
        path, base = os.path.split(path)
        parts.append(base)

    parts.reverse()

    return '%s.%s' % ('.'.join(parts[1:]), module)


def _load_account_module(path):
    module = None
    if os.path.isdir(path):
        if '%s.py' % _ACCOUNT_MODULE_NAME in os.listdir(path):
            module = _load_module(path, _ACCOUNT_MODULE_NAME)

    return module


def _load_service_module(path, service_name):
    module = None
    if os.path.isdir(path):
        if service_name in os.listdir(path):
            module = _load_module(os.path.join(path, service_name),
                                  service_name)

    return module


def _extend_icon_theme_search_path(path):
    icon_theme = Gtk.IconTheme.get_default()
    icon_search_path = icon_theme.get_search_path()
    try:
        icon_path_dirs = os.listdir(path)
    except OSError as e:
        icon_path_dirs = []
        logging.warning('listdir: %s: %s' % (path, e))

    for file in icon_path_dirs:
        if file == 'icons':
            icon_path = os.path.join(path, file)
            if os.path.isdir(icon_path) and \
                    icon_path not in icon_search_path:
                icon_theme.append_search_path(icon_path)


def get_account(service_name):
    _ensure_module_repository()

    if service_name in _module_repository:
        return _module_repository[service_name]['account']
    else:
        return None


def get_service(service_name):
    _ensure_module_repository()

    if service_name in _module_repository:
        return _module_repository[service_name]['service']
    else:
        return None


def get_configured_accounts():
    return [a for a in get_all_accounts()
            if a.get_token_state() in (Account.STATE_VALID,
                                       Account.STATE_EXPIRED)]


def get_active_accounts():
    return [a for a in get_all_accounts()
            if a.get_token_state() == Account.STATE_VALID]


def has_configured_accounts():
    return len(get_configured_accounts()) > 0


def get_webaccount_services():
    _ensure_module_repository()

    service_paths = []
    for path in _get_webaccount_paths():
        service_paths.append(os.path.join(path, 'services'))

    services = []
    for service_path in service_paths:
        if not os.path.exists(service_path):
            continue

        folders = os.listdir(service_path)
        for folder in folders:
            if not os.path.isdir(os.path.join(service_path, folder)):
                continue

            if not os.path.exists(os.path.join(
                    service_path, folder, 'service.py')):
                continue

            module = _load_module(os.path.join(service_path, folder),
                                  'service')
            if hasattr(module, 'get_service'):
                services.append(module.get_service())

    return services
