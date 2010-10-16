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
import xmlrpclib
import socket
import httplib
import os
from string import ascii_uppercase
import random
import time
import uuid

import gconf

from sugar import env
from sugar.profile import get_profile

REGISTER_URL = 'http://schoolserver:8080/'
REGISTER_TIMEOUT = 8


def generate_serial_number():
    """  Generates a serial number based on 3 random uppercase letters
    and the last 8 digits of the current unix seconds. """

    serial_part1 = []

    for y_ in range(3):
        serial_part1.append(random.choice(ascii_uppercase))

    serial_part1 = ''.join(serial_part1)
    serial_part2 = str(int(time.time()))[-8:]
    serial = serial_part1 + serial_part2

    return serial


def store_identifiers(serial_number, uuid, backup_url):
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
    uuid_file.write(uuid)
    uuid_file.close()

    if os.path.exists(os.path.join(identifier_path, 'backup_url')):
        os.remove(os.path.join(identifier_path, 'backup_url'))
    backup_url_file = open(os.path.join(identifier_path, 'backup_url'), 'w')
    backup_url_file.write(backup_url)
    backup_url_file.close()


class RegisterError(Exception):
    pass


class TimeoutHTTP(httplib.HTTP):

    def __init__(self, host='', port=None, strict=None, timeout=None):
        if port == 0:
            port = None
        # FIXME: Depending on undocumented internals that can break between
        # Python releases. Please have a look at SL #2350
        self._setup(self._connection_class(host,
                 port, strict, timeout=REGISTER_TIMEOUT))


class TimeoutTransport(xmlrpclib.Transport):

    def make_connection(self, host):
        host, extra_headers, x509 = self.get_host_info(host)
        return TimeoutHTTP(host, timeout=REGISTER_TIMEOUT)


def register_laptop(url=REGISTER_URL):

    profile = get_profile()
    client = gconf.client_get_default()

    if have_ofw_tree():
        sn = read_ofw('mfg-data/SN')
        uuid_ = read_ofw('mfg-data/U#')
        sn = sn or 'SHF00000000'
        uuid_ = uuid_ or '00000000-0000-0000-0000-000000000000'
    else:
        sn = generate_serial_number()
        uuid_ = str(uuid.uuid1())

    setting_name = '/desktop/sugar/collaboration/jabber_server'
    jabber_server = client.get_string(setting_name)
    store_identifiers(sn, uuid_, jabber_server)

    if jabber_server:
        url = 'http://' + jabber_server + ':8080/'

    nick = client.get_string('/desktop/sugar/user/nick')

    server = xmlrpclib.ServerProxy(url, TimeoutTransport())
    try:
        data = server.register(sn, nick, uuid_, profile.pubkey)
    except (xmlrpclib.Error, TypeError, socket.error):
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
