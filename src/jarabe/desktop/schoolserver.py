# Copyright (C) 2007, 2008 One Laptop Per Child
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

import logging
from gettext import gettext as _
import xmlrpclib
import socket
import httplib
import os
from string import ascii_uppercase
import random
import time
import uuid
import sys

from gi.repository import Gio

from sugar3 import env
from sugar3.profile import get_profile
from sugar3.profile import get_nick_name

_REGISTER_URL = 'http://schoolserver:8080/'
_REGISTER_TIMEOUT = 8
_OFW_TREE = '/ofw'
_PROC_TREE = '/proc/device-tree'
_MFG_SN = 'mfg-data/SN'
_MFG_UUID = 'mfg-data/U#'


def _generate_serial_number():
    """  Generates a serial number based on 3 random uppercase letters
    and the last 8 digits of the current unix seconds. """

    serial_part1 = []

    for y_ in range(3):
        serial_part1.append(random.choice(ascii_uppercase))

    serial_part1 = ''.join(serial_part1)
    serial_part2 = str(int(time.time()))[-8:]
    serial = serial_part1 + serial_part2

    return serial


def _store_identifiers(serial_number, uuid_, backup_url):
    """  Stores the serial number, uuid and backup_url
    in the identifier folder inside the profile directory
    so that these identifiers can be used for backup. """

    identifier_path = os.path.join(env.get_profile_path(), 'identifiers')
    if not os.path.exists(identifier_path):
        os.mkdir(identifier_path)

    if os.path.exists(os.path.join(identifier_path, 'sn')):
        os.remove(os.path.join(identifier_path, 'sn'))
    serial_file = open(os.path.join(identifier_path, 'sn'), 'w')
    serial_file.write(serial_number)
    serial_file.close()

    if os.path.exists(os.path.join(identifier_path, 'uuid')):
        os.remove(os.path.join(identifier_path, 'uuid'))
    uuid_file = open(os.path.join(identifier_path, 'uuid'), 'w')
    uuid_file.write(uuid_)
    uuid_file.close()

    if os.path.exists(os.path.join(identifier_path, 'backup_url')):
        os.remove(os.path.join(identifier_path, 'backup_url'))
    backup_url_file = open(os.path.join(identifier_path, 'backup_url'), 'w')
    backup_url_file.write(backup_url)
    backup_url_file.close()


class RegisterError(Exception):
    pass


class _TimeoutHTTP(httplib.HTTP):

    def __init__(self, host='', port=None, strict=None, timeout=None):
        if port == 0:
            port = None
        # FIXME: Depending on undocumented internals that can break between
        # Python releases. Please have a look at SL #2350
        self._setup(
            self._connection_class(host,
                                   port, strict, timeout=_REGISTER_TIMEOUT))


class _TimeoutTransport(xmlrpclib.Transport):

    def make_connection(self, host):
        host, extra_headers, x509_ = self.get_host_info(host)
        return _TimeoutHTTP(host, timeout=_REGISTER_TIMEOUT)


def register_laptop(url=_REGISTER_URL):

    profile = get_profile()

    if _have_ofw_tree():
        sn = _read_mfg_data(os.path.join(_OFW_TREE, _MFG_SN))
        uuid_ = _read_mfg_data(os.path.join(_OFW_TREE, _MFG_UUID))
    elif _have_proc_device_tree():
        sn = _read_mfg_data(os.path.join(_PROC_TREE, _MFG_SN))
        uuid_ = _read_mfg_data(os.path.join(_PROC_TREE, _MFG_UUID))
    else:
        sn = _generate_serial_number()
        uuid_ = str(uuid.uuid1())
    sn = sn or 'SHF00000000'
    uuid_ = uuid_ or '00000000-0000-0000-0000-000000000000'

    nick = get_nick_name()

    settings = Gio.Settings('org.sugarlabs.collaboration')
    jabber_server = settings.get_string('jabber-server')
    _store_identifiers(sn, uuid_, jabber_server)

    if jabber_server:
        url = 'http://' + jabber_server + ':8080/'

    if sys.hexversion < 0x2070000:
        server = xmlrpclib.ServerProxy(url, _TimeoutTransport())
    else:
        socket.setdefaulttimeout(_REGISTER_TIMEOUT)
        server = xmlrpclib.ServerProxy(url)
    try:
        data = server.register(sn, nick, uuid_, profile.pubkey)
    except (xmlrpclib.Error, TypeError, socket.error):
        logging.exception('Registration: cannot connect to server')
        raise RegisterError(_('Cannot connect to the server.'))
    finally:
        socket.setdefaulttimeout(None)

    if data['success'] != 'OK':
        logging.error('Registration: server could not complete request: %s',
                      data['error'])
        raise RegisterError(_('The server could not complete the request.'))

    settings.set_string('jabber-server', data['jabberserver'])
    settings = Gio.Settings('org.sugarlabs')
    settings.set_string('backup-url', data['backupurl'])

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()
    client.set_string(
        '/desktop/sugar/collaboration/jabber_server', data['jabberserver'])
    client.set_string('/desktop/sugar/backup_url', data['backupurl'])

    return True


def _have_ofw_tree():
    return os.path.exists(_OFW_TREE)


def _have_proc_device_tree():
    return os.path.exists(_PROC_TREE)


def _read_mfg_data(path):
    if not os.path.exists(path):
        return None
    fh = open(path, 'r')
    data = fh.read().rstrip('\0\n')
    fh.close()
    return data
