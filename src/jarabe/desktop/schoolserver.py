# Copyright (C) 2007, 2008 One Laptop Per Child
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

import logging
from gettext import gettext as _
from xmlrpclib import ServerProxy, Error
import socket
import os
import gconf

from sugar.profile import get_profile

REGISTER_URL = 'http://schoolserver:8080/'

class RegisterError(Exception):
    pass

def register_laptop(url=REGISTER_URL):
    if not have_ofw_tree():
        logging.error('Registration: Cannot obtain data needed to register.')
        raise RegisterError(_('Cannot obtain data needed for registration.'))

    sn = read_ofw('mfg-data/SN')
    uuid = read_ofw('mfg-data/U#')
    sn = sn or 'SHF00000000'
    uuid = uuid or '00000000-0000-0000-0000-000000000000'

    profile = get_profile()

    client = gconf.client_get_default()
    nick = client.get_string('/desktop/sugar/user/nick')

    server = ServerProxy(url)
    try:
        data = server.register(sn, nick, uuid, profile.pubkey)
    except (Error, socket.error):
        logging.exception('Registration: cannot connect to server')
        raise RegisterError(_('Cannot connect to the server.'))        
        
    if data['success'] != 'OK':
        logging.error('Registration: server could not complete request: %s',
                      data['error'])
        raise RegisterError(_('The server could not complete the request.'))

    client.set_string('/desktop/sugar/collaboration/jabber_server',
                      data['jabberserver'])
    client.set_string('/desktop/sugar/backup_url', data['backupurl'])

    return True

def have_ofw_tree():
    return os.path.exists('/ofw')

def read_ofw(path):
    path = os.path.join('/ofw', path)
    if not os.path.exists(path):
        return None
    fh = open(path, 'r')
    data = fh.read().rstrip('\0\n')
    fh.close()
    return data
