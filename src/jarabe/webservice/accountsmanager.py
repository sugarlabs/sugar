# Copyright (c) 2013 Walter Bender
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

from gi.repository import Gtk

from jarabe import config
from jarabe.webservice.account import Account

_ACCOUNT_MODULE_NAME = 'account'

_module_repository = {}


def get_all_accounts():
    ''' Build repository of the online account managers and related
    service modules and return a list of the accounts'''
    global _module_repository

    _append_sys_path()

    webservices = _get_webservices()
    for dir_path in webservices:
        service_name = _get_service_name(dir_path)
        if service_name in _module_repository:
            continue

        service_module = _load_service_module(dir_path, service_name)
        if service_module is None:
            continue

        _module_repository[service_name] = {'service': service_module}

        account_module = None
        module = _load_account_module(dir_path)

        if module is not None and hasattr(module, 'get_account'):
            try:
                account_module = module.get_account()
            except ImportError, e:
                logging.error('Could not get_account() %s' % (e))
            except AttributeError, e:
                logging.error('Could not get_account() %s' % (e))

        if account_module is not None:
            _module_repository[service_name]['account'] = account_module
            _extend_icon_theme_search_path(dir_path)
        else:
            del _module_repository[service_name]

    accounts = []
    for key in _module_repository.keys():
        accounts.append(_module_repository[key]['account'])

    return accounts


def _get_service_name(service_path):
    ''' service path is of the form:
    /usr/share/sugar/extensions/webservice/my_service/my_service '''
    parts = service_path.split('/')
    return parts[parts.index('webservice') + 1]


def _get_webservices():
    webservices = []
    for webservice_path in _get_webservice_paths():
        try:
            for path in os.listdir(webservice_path):
                service_path = os.path.join(webservice_path, path)
                if os.path.isdir(service_path):
                    webservices.append(service_path)
        except OSError, e:
            logging.warning('listdir: %s: %s' % (webservice_path, e))
    return webservices


def _find_module(path, module):
    mod = None
    if 'extensions' not in path:
        return ''

    parts = []
    while 'extensions' not in parts:
        path, base = os.path.split(path)
        parts.append(base)

    parts.reverse()
    path = '.'.join(parts[1:])

    return '%s.%s' % (path, module)


def _load_account_module(dir_path):
    module = None
    if os.path.isdir(dir_path):
        if '%s.py' % _ACCOUNT_MODULE_NAME in os.listdir(dir_path):
            module = __import__(
                _find_module(dir_path, _ACCOUNT_MODULE_NAME),
                globals(),
                locals(),
                [_ACCOUNT_MODULE_NAME])

    return module


def _load_service_module(dir_path, service_name):
    module = None
    if os.path.isdir(dir_path):
        if service_name in os.listdir(dir_path):
            module = __import__(
                _find_module(os.path.join(dir_path, service_name),
                             service_name),
                globals(),
                locals(),
                [service_name])

    return module


def _extend_icon_theme_search_path(dir_path):
    icon_theme = Gtk.IconTheme.get_default()
    icon_search_path = icon_theme.get_search_path()
    try:
        icon_path_dirs = os.listdir(dir_path)
    except OSError, e:
        icon_path_dirs = []
        logging.warning('listdir: %s: %s' % (dir_path, e))

    if 'icons' in icon_path_dirs:
        icon_path = os.path.join(dir_path, 'icons')
        if os.path.isdir(icon_path) and \
                icon_path not in icon_search_path:
            icon_theme.append_search_path(icon_path)


def _append_sys_path():
    for path in [os.path.join(os.path.expanduser('~'), '.sugar', 'extensions'),
                 config.ext_path]:
        if os.path.exists(path):
            if path not in sys.path:
                sys.path.append(path)


def _get_webservice_paths():
    paths = []
    for path in [os.path.join(os.path.expanduser('~'), '.sugar', 'extensions',
                              'local', 'webservice'),
                 os.path.join(config.ext_path, 'webservice')]:
        if os.path.exists(path):
            paths.append(path)
    return paths


def get_webaccount_paths():
    paths = []
    for path in [os.path.join(os.path.expanduser('~'), '.sugar', 'extensions',
                              'local', 'cpsection', 'webaccount'),
                 os.path.join(config.ext_path, 'cpsection', 'webaccount')]:
        if os.path.exists(path):
            paths.append(path)
    return paths


def get_account(service_name):
    if service_name in _module_repository:
        return _module_repository[service_name]['account']
    else:
        return None


def get_service(service_name):
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
