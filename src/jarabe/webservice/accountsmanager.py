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

from jarabe import extensions
from jarabe.webservice.account import Account

_accounts = []


def get_all_accounts():
    ''' Returns a list of all installed online account managers '''
    global _accounts
    if len(_accounts) > 0:
        return _accounts

    webservices = _get_webservices()
    for dir_path in webservices:
        module = _load_module(dir_path)
        if module is not None:
            _accounts.append(module)
            _extend_icon_theme_search_path(dir_path)

    return _accounts


def _get_webservices():
    webservices = []
    for webservice_path in extensions.get_webservice_paths():
        try:
            for path in os.listdir(webservice_path):
                service_path = os.path.join(webservice_path, path)
                if os.path.isdir(service_path):
                    webservices.append(service_path)
        except OSError, e:
            logging.warning('listdir: %s: %s' % (webservice_path, e))
    return webservices


def _load_module(dir_path):
    module = None
    if os.path.isdir(dir_path):
        for file in os.listdir(dir_path):
            if file == 'account.py':
                module_name = file[:-3]
                logging.debug('OnlineAccountsManager loading %s %s' %
                              (dir_path, module_name))
                mod = extensions.load_module(dir_path, module_name)
                print mod
                if hasattr(mod, 'get_account'):
                    module = mod.get_account()
                    break
    return module


def _extend_icon_theme_search_path(dir_path):
    icon_theme = Gtk.IconTheme.get_default()
    icon_search_path = icon_theme.get_search_path()
    try:
        icon_path_dirs = os.listdir(dir_path)
    except OSError, e:
        icon_path_dirs = []
        logging.warning('listdir: %s: %s' % (dir_path, e))

    for file in icon_path_dirs:
        if file == 'icons':
            icon_path = os.path.join(dir_path, file)
            if os.path.isdir(icon_path) and \
                    icon_path not in icon_search_path:
                icon_theme.append_search_path(icon_path)


def get_configured_accounts():
    return [a for a in get_all_accounts()
            if a.get_token_state() in (Account.STATE_VALID,
                                       Account.STATE_EXPIRED)]


def get_active_accounts():
    return [a for a in get_all_accounts()
            if a.get_token_state() == Account.STATE_VALID]


def has_configured_accounts():
    return len(get_configured_accounts()) > 0
