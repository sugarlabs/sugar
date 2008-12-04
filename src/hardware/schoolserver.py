import logging
from gettext import gettext as _
from xmlrpclib import ServerProxy, Error
import socket
import os

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

    server = ServerProxy(url)
    try:
        data = server.register(sn, profile.nick_name, uuid, profile.pubkey)
    except (Error, socket.error), e:
        logging.error('Registration: cannot connect to server: %s' % e)
        raise RegisterError(_('Cannot connect to the server.'))        
        
    if data['success'] != 'OK':
        logging.error('Registration: server could not complete request: %s' % 
                      data['error'])
        raise RegisterError(_('The server could not complete the request.'))

    profile.jabber_server = data['jabberserver']
    profile.backup1 = data['backupurl']
    profile.save()

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
