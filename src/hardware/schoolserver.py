from sugar.profile import get_profile
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

    profile = get_profile()

    try:
        server = ServerProxy(url)
        data = server.register(sn, profile.nick_name, uuid, profile.pubkey)
        if data['success'] != 'OK':
            print >> sys.stderr, "Error registering laptop: " + data['error']
            return False

        profile.jabber_server = data['jabberserver']
        profile.backup1 = data['backupurl']
        profile.save()
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
