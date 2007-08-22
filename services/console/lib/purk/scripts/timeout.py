import time

import ui
from conf import conf

def setupRaw(e):
    e.network._message_timeout = False

def onSocketConnect(e):
    timeout = conf.get("server_traffic_timeout", 120)*1000
    e.network._message_timeout = False
    if timeout:
        e.network._message_timeout_source = ui.register_timer(timeout, check_timeout, e.network)
    else:
        e.network._message_timeout_source = None

def check_timeout(network):
    if network._message_timeout:
        network.raw("PING %s" % network.me)
        timeout = conf.get("server_death_timeout", 240)*1000
        network._message_timeout_source = ui.register_timer(timeout, check_death_timeout, network)
        return False
    else:
        network._message_timeout = True
        return True # call this function again

def check_death_timeout(network):
    if network._message_timeout:
        network.raw("QUIT :Server missing, presumed dead")
        network.disconnect(error="The server seems to have stopped talking to us")
    else:
        network._message_timeout = False
        timeout = conf.get("server_traffic_timeout", 120)*1000
        if timeout:
            network._message_timeout_source = ui.register_timer(timeout, check_timeout, network)
        else:
            network._message_timeout_source = None

def onDisconnect(e):
    try:
        if e.network._message_timeout_source:
            e.network._message_timeout_source.unregister()
            e.network._message_timeout_source = None
    except AttributeError:
        pass
