"""User settings/configuration loading"""
# Copyright (C) 2006-2007 Red Hat, Inc.
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
    """Local user's current options/profile information
    
    User settings are stored in an INI-style configuration
    file.  This object uses the ConfigParser module to load 
    the settings.  At the moment the only storage mechanism
    is in the set_server_registered method, which loads the 
    file directly from disk, then dumps it back out again 
    immediately, rather than using the class.
    
    The profile is also responsible for loading the user's
    public and private ssh keys from disk.
    
    Attributes:
    
        name -- child's name 
        color -- XoColor for the child's icon
        server -- school server with which the child is 
            associated 
        server_registered -- whether the child has registered 
            with the school server or not
        
        pubkey -- public ssh key
        privkey_hash -- SHA has of the child's public key 
    """
    def __init__(self):
        self.name = None
        self.color = None
        self.pubkey = None
        self.privkey_hash = None
        self.server = None
        self.server_registered = False
        self._load()

    def update(self):
        self._load()

    def _load(self):
        cp = ConfigParser()
        config_path = os.path.join(env.get_profile_path(), 'config')
        parsed = cp.read([config_path])

        if cp.has_option('Buddy', 'NickName'):
            name = cp.get('Buddy', 'NickName')
            # decode nickname from ascii-safe chars to unicode
            self.name = name.decode("utf-8")

        if cp.has_option('Buddy', 'Color'):
            self.color = XoColor(cp.get('Buddy', 'Color'))

        if cp.has_option('Server', 'Server'):
            self.server = cp.get('Server', 'Server')

        if cp.has_option('Server', 'Registered'):
            registered = cp.get('Server', 'Registered')
            if registered.lower() == "true":
                self.server_registered = True

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

def get_server():
    return _profile.server

def get_server_registered():
    return _profile.server_registered

def set_server_registered():
    _profile.server_registered = True

    cp = ConfigParser()

    config_path = os.path.join(env.get_profile_path(), 'config')
    cp.read([config_path])

    if not cp.has_section('Server'):
        cp.add_section('Server')
    cp.set('Server', 'Registered', True)
    cp.write(open(config_path, 'w'))

def update():
    _profile.update()

_profile = _Profile()
