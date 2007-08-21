import gtk

import windows
from conf import conf

if 'networks' not in conf:
    conf['networks'] = {}

def server_get_data(network_info):
    if 'port' in network_info:
        return "%s:%s" % (
            network_info.get('server', '') , network_info.get('port')
            )
    else:
        return network_info.get('server', '')
        
def server_set_data(text, network_info):
    if ':' in text:
        network_info['server'], port = text.rsplit(':',1)
        network_info['port'] = int(port)
    else:
        network_info['server'] = text
        network_info.pop('port', None)
            
def channels_get_data(network_info):
    return '\n'.join(network_info.get('join', ()))
            
def channels_set_data(text, network_info):
    network_info['join'] = []
    
    for line in text.split('\n'):
        for chan in line.split(','):
            if chan:
                network_info['join'].append(chan.strip())
    
def perform_get_data(network_info):
    return '\n'.join(network_info.get('perform', ()))
            
def perform_set_data(text, network_info):
    network_info['perform'] = [line for line in text.split('\n') if line]
    
def autoconnect_set_data(do_autoconnect, network): 
    if 'start_networks' not in conf:
        conf['start_networks'] = []

    # note (n in C) != w
    if (network in conf.get('start_networks')) != do_autoconnect:
        if do_autoconnect:
            conf.get('start_networks').append(network)
        else:
            conf.get('start_networks').remove(network)
