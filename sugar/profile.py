# Copyright (C) 2006, Red Hat, Inc.
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
import logging
from ConfigParser import ConfigParser

from sugar import env
from sugar import util
from sugar.graphics.xocolor import XoColor

class _Profile(object):
    def __init__(self):
        self.name = None
        self.color = None
        self.pubkey = None
        self.privkey_hash = None
        self._load()

    def update(self):
        self._load()

    def _load(self):
        cp = ConfigParser()
        config_path = os.path.join(env.get_profile_path(), 'config')
        parsed = cp.read([config_path])

        if cp.has_option('Buddy', 'NickName'):
            self.name = cp.get('Buddy', 'NickName')

        if cp.has_option('Buddy', 'Color'):
            self.color = XoColor(cp.get('Buddy', 'Color'))

        del cp

        self._load_pubkey()
        self._hash_private_key()

    def _load_pubkey(self):
        self.pubkey = None

        key_path = os.path.join(env.get_profile_path(), 'owner.key.pub')
        try:
            f = open(key_path, "r")
            lines = f.readlines()
            f.close()
        except IOError, e:
            logging.error("Error reading public key: %s" % e)
            return

        magic = "ssh-dss "
        for l in lines:
            l = l.strip()
            if not l.startswith(magic):
                continue
            self.pubkey = l[len(magic):]
            break
        if not self.pubkey:
            logging.error("Error parsing public key.")

    def _hash_private_key(self):
        self.privkey_hash = None
        
        key_path = os.path.join(env.get_profile_path(), 'owner.key')
        try:
            f = open(key_path, "r")
            lines = f.readlines()
            f.close()
        except IOError, e:
            logging.error("Error reading private key: %s" % e)
            return

        key = ""
        for l in lines:
            l = l.strip()
            if l.startswith("-----BEGIN DSA PRIVATE KEY-----"):
                continue
            if l.startswith("-----END DSA PRIVATE KEY-----"):
                continue
            key += l
        if not len(key):
            logging.error("Error parsing public key.")

        # hash it
        key_hash = util._sha_data(key)
        self.privkey_hash = util.printable_hash(key_hash)

def get_nick_name():
    return _profile.name

def get_color():
    return _profile.color

def get_pubkey():
    return _profile.pubkey

def get_private_key_hash():
    return _profile.privkey_hash

def update():
    _profile.update()

_profile = _Profile()
