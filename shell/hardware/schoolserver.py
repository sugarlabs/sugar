#!/usr/bin/env python
from sugar import profile
from xmlrpclib import ServerProxy, Error
import sys
import os

REGISTER_URL = 'http://schoolserver:8080/'

def register_laptop(url=REGISTER_URL):
    if not have_ofw_tree():
        return False

    sn = read_ofw('mfg-data/SN')
    uuid = read_ofw('mfg-data/U#')
    sn = sn or 'SHF00000000'
    uuid = uuid or '00000000-0000-0000-0000-000000000000'

    nick = profile.get_nick_name()
    pubkey = profile.get_pubkey()

    try:
        server = ServerProxy(url)
        data = server.register(sn, nick, uuid, pubkey)
        if data['success'] != 'OK':
            print >> sys.stderr, "Error registering laptop: " + data['error']
            return False
        backupurl = data['backupurl']
        jserver = data['jabberserver']
        profile.set_server(jserver)
        profile.set_trial2_backup(backupurl)
    except Error, e:
        print >> sys.stderr, "Error registering laptop: " + str(e)
        return False

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

if __name__ == "__main__":
    url = REGISTER_URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    register_laptop(url)
