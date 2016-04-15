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
import sys
import urllib2
import re
import json
import subprocess

from gi.repository import Gio

from sugar3 import env
from sugar3.profile import get_profile
from sugar3.profile import get_nick_name

_REGISTER_URL = 'http://schoolserver:8080/'
_SERVER_DB_URL = 'http://schoolserver:5000/'
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


def _get_history_for_serial(serial_number):
    identifier_path = os.path.join(env.get_profile_path(), 'identifiers')
    if not os.path.exists(identifier_path):
        os.mkdir(identifier_path)

    file_path = os.path.join(identifier_path, 'server_history')
    if os.path.exists(file_path):
        json_file = open(file_path, 'r')
        data = json.loads(json_file.read())
        json_file.close()
        if serial_number in data:
            return (True, data[serial_number])
        else:
            return (False, None)
    else:
        return (False, None)


def _store_identifiers(serial_number, uuid_, jabber_server, backup_url):
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
    backup_url_file.write(jabber_server)
    backup_url_file.close()

    file_path = os.path.join(identifier_path, 'server_history')
    if os.path.exists(file_path):
        server_history_file = open(file_path, "r")
        data = json.load(server_history_file)
        server_history_file.close()
        data[serial_number] = {}
        data[serial_number]["uuid"] = uuid_
        data[serial_number]["backup_url"] = backup_url
    else:
        data = {}
        data[serial_number] = {}
        data[serial_number]["uuid"] = uuid_
        data[serial_number]["backup_url"] = backup_url
    server_history_file = open(file_path, 'w+')
    server_history_file.write(json.dumps(data))
    server_history_file.close()


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


def register_laptop(url=_REGISTER_URL, db_url=_SERVER_DB_URL):

    profile = get_profile()
    new_registration_required = True
    backup_url = ''
    server_html = ''

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

    # Check server for registration
    if jabber_server:
        db_url = 'http://' + jabber_server + ':5000/'
        url = 'http://' + jabber_server + ':8080/'
    try:
        response = urllib2.urlopen(db_url)
        server_html = response.read()
    except (urllib2.URLError, urllib2.HTTPError):
        logging.exception('Registration: cannot connect to xs-authserver')

    if server_html and profile.pubkey in server_html:
        new_registration_required = False
        registered_laptops = re.findall(r'{.+}', server_html)
        for laptop in registered_laptops:
            if profile.pubkey in laptop:
                string_for_json = laptop.replace("&#39;", "\"").replace(
                    " u\"", "\"")
                data = json.loads(string_for_json)
                history_found, data_ = _get_history_for_serial(data["serial"])
                new_registration_required = not history_found
                if history_found:
                    uuid_ = data_["uuid"]
                    sn = data["serial"]
                    backup_url = data_["backup_url"]
                    try:
                        jabber_server = re.search(r'\@(.*)\:',
                                                  backup_url).group(1)
                    except AttributeError:
                        pass

    if new_registration_required:
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

        # Registration Successful, hence we can add the identification of this
        # server to our known_host file.
        command = "ssh-keyscan -H -t ecdsa " + jabber_server
        output = subprocess.check_output(command, shell=True)
        os.system("mkdir -p ~/.ssh")
        command = "echo \"%s\" >> ~/.ssh/known_hosts" % output.rstrip('\n')
        os.system(command)

        jabber_server = data['jabberserver']
        backup_url = data['backupurl']

    _store_identifiers(sn, uuid_, jabber_server, backup_url)
    settings.set_string('jabber-server', jabber_server)
    settings = Gio.Settings('org.sugarlabs')
    settings.set_string('backup-url', backup_url)

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()
    client.set_string(
        '/desktop/sugar/collaboration/jabber_server', jabber_server)
    client.set_string('/desktop/sugar/backup_url', backup_url)
    client.set_string('/desktop/sugar/soas_serial', sn)

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
