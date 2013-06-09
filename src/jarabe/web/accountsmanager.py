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
import logging

from gi.repository import Gtk

from jarabe import config
from sugar3.web.account import Account

_accounts = []


def get_all_accounts():
    ''' Returns a list of all installed online account managers '''
    global _accounts
    if len(_accounts) > 0:
        return _accounts

    web_path = os.path.join(config.ext_path, 'web')
    try:
        web_path_dirs = os.listdir(web_path)
    except OSError, e:
        web_path_dirs = []
        logging.warning('listdir: %s: %s' % (web_path, e))

    for d in web_path_dirs:
        dir_path = os.path.join(web_path, d)
        module = _load_module(dir_path)
        if module is not None:
            _accounts.append(module)
            _extend_icon_theme_search_path(dir_path)

    return _accounts


def _load_module(dir_path):
    module = None
    if os.path.isdir(dir_path):
        for f in os.listdir(dir_path):
            if f == 'account.py':
                module_name = f[:-3]
                logging.debug('OnlineAccountsManager loading %s' %
                              (module_name))
                module_path = 'web.%s.%s' % (os.path.basename(dir_path),
                                             module_name)
                try:
                    mod = __import__(module_path, globals(), locals(),
                                     [module_name])
                    if hasattr(mod, 'get_account'):
                        module = mod.get_account()

                except Exception as e:
                    logging.exception('Exception while loading %s: %s' %
                                      (module_name, str(e)))

    return module


def _extend_icon_theme_search_path(dir_path):
    icon_theme = Gtk.IconTheme.get_default()
    icon_search_path = icon_theme.get_search_path()

    try:
        icon_path_dirs = os.listdir(dir_path)
    except OSError, e:
        icon_path_dirs = []
        logging.warning('listdir: %s: %s' % (dir_path, e))

    for f in icon_path_dirs:
        if f == 'icons':
            icon_path = os.path.join(dir_path, f)
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
