import time

from conf import conf
import ui
import windows
import irc

COMMAND_PREFIX = conf.get('command_prefix', '/')

NICK_SUFFIX = r"`_-\|0123456789"

_hextochr = dict(('%02x' % i, chr(i)) for i in range(256))
def unquote(url, rurl=""):

    while '%' in url:
        url, char = url.rsplit('%', 1)
        
        chars = char[:2].lower()

        if chars in _hextochr:
            rurl = '%s%s%s' % (_hextochr[chars], char[2:], rurl)
        else:
            rurl = "%s%s%s" % ('%', char, rurl)
            
    return url + rurl

#for getting a list of alternative nicks to try on a network
def _nick_generator(network):
    for nick in network.nicks[1:]:
        yield nick
    if network._nick_error:
        nick = 'ircperson'
    else:
        nick = network.nicks[0]
    import itertools
    for i in itertools.count(1):
        for j in xrange(len(NICK_SUFFIX)**i):
            suffix = ''.join(NICK_SUFFIX[(j/(len(NICK_SUFFIX)**x))%len(NICK_SUFFIX)] for x in xrange(i))
            if network._nick_max_length:
                yield nick[0:network._nick_max_length-i]+suffix
            else:
                yield nick+suffix

def setdownRaw(e):
    if not e.done:
        if not e.network.got_nick:
            if e.msg[1] in ('432','433','436','437'): #nickname unavailable
                failednick = e.msg[3]
                nicks = list(e.network.nicks)
                
                if hasattr(e.network,'_nick_generator'):
                    if len(failednick) < len(e.network._next_nick):
                        e.network._nick_max_length = len(failednick)
                    e.network._next_nick = e.network._nick_generator.next()
                    e.network.raw('NICK %s' % e.network._next_nick)
                    e.network._nick_error |= (e.msg[1] == '432')
                else:
                    e.network._nick_error = (e.msg[1] == '432')
                    if len(failednick) < len(e.network.nicks[0]):
                        e.network._nick_max_length = len(failednick)
                    else:
                        e.network._nick_max_length = 0
                    e.network._nick_generator = _nick_generator(e.network)
                    e.network._next_nick = e.network._nick_generator.next()
                    e.network.raw('NICK %s' % e.network._next_nick)
            
            elif e.msg[1] == '431': #no nickname given--this shouldn't happen
                pass
            
            elif e.msg[1] == '001':
                e.network.got_nick = True
                if e.network.me != e.msg[2]:
                    core.events.trigger(
                        'Nick', network=e.network, window=e.window,
                        source=e.network.me, target=e.msg[2], address='',
                        text=e.msg[2]
                        )
                    e.network.me = e.msg[2]
                if hasattr(e.network,'_nick_generator'):
                    del e.network._nick_generator, e.network._nick_max_length, e.network._next_nick
                
        if e.msg[1] == "PING":
            e.network.raw("PONG :%s" % e.msg[-1])
            e.done = True
        
        elif e.msg[1] == "JOIN":
            e.channel = e.target
            e.requested = e.network.norm_case(e.channel) in e.network.requested_joins
            core.events.trigger("Join", e)
            e.done = True
        
        elif e.msg[1] == "PART":
            e.channel = e.target
            e.requested = e.network.norm_case(e.channel) in e.network.requested_parts
            e.text = ' '.join(e.msg[3:])
            core.events.trigger("Part", e)
            e.done = True
        
        elif e.msg[1] in "MODE":
            e.channel = e.target
            e.text = ' '.join(e.msg[3:])
            core.events.trigger("Mode", e)
            e.done = True
            
        elif e.msg[1] == "QUIT":
            core.events.trigger('Quit', e)
            e.done = True
            
        elif e.msg[1] == "KICK":
            e.channel = e.msg[2]
            e.target = e.msg[3]
            core.events.trigger('Kick', e)
            e.done = True
            
        elif e.msg[1] == "NICK":
            core.events.trigger('Nick', e)
            if e.network.me == e.source:
                e.network.me = e.target

            e.done = True
            
        elif e.msg[1] == "PRIVMSG":
            core.events.trigger('Text', e)
            e.done = True
        
        elif e.msg[1] == "NOTICE":
            core.events.trigger('Notice', e)
            e.done = True
        
        elif e.msg[1] == "TOPIC":
            core.events.trigger('Topic', e)
            e.done = True
        
        elif e.msg[1] in ("376", "422"): #RPL_ENDOFMOTD
            if e.network.status == irc.INITIALIZING:
                e.network.status = irc.CONNECTED
                core.events.trigger('Connect', e)
            e.done = True
        
        elif e.msg[1] == "470": #forwarded from channel X to channel Y
            if e.network.norm_case(e.msg[3]) in e.network.requested_joins:
                e.network.requested_joins.discard(e.network.norm_case(e.msg[3]))
                e.network.requested_joins.add(e.network.norm_case(e.msg[4]))
        
        elif e.msg[1] == "005": #RPL_ISUPPORT
            for arg in e.msg[3:]:
                if ' ' not in arg: #ignore "are supported by this server"
                    if '=' in arg:
                        name, value = arg.split('=', 1)
                        if value.isdigit():
                            value = int(value)
                    else:
                        name, value = arg, ''

                    #Workaround for broken servers (bahamut on EnterTheGame)
                    if name == 'PREFIX' and value[0] != '(':
                        continue

                    #in theory, we're supposed to replace \xHH with the
                    # corresponding ascii character, but I don't think anyone
                    # really does this
                    e.network.isupport[name] = value
                    
                    if name == 'PREFIX':
                        new_prefixes = {}
                        modes, prefixes = value[1:].split(')')
                        for mode, prefix in zip(modes, prefixes):
                            new_prefixes[mode] = prefix
                            new_prefixes[prefix] = mode
                        e.network.prefixes = new_prefixes

def setupSocketConnect(e):
    e.network.got_nick = False
    e.network.isupport = {
        'NETWORK': e.network.server, 
        'PREFIX': '(ohv)@%+',
        'CHANMODES': 'b,k,l,imnpstr',
    }
    e.network.prefixes = {'o':'@', 'h':'%', 'v':'+', '@':'o', '%':'h', '+':'v'}
    e.network.connect_timestamp = time.time()
    e.network.requested_joins.clear()
    e.network.requested_parts.clear()
    e.network.on_channels.clear()
    if hasattr(e.network,'_nick_generator'):
        del e.network._nick_generator, e.network._nick_max_length, e.network._next_nick
    if not e.done:
        #this needs to be tested--anyone have a server that uses PASS?
        if e.network.password:
            e.network.raw("PASS :%s" % e.network.password)
        e.network.raw("NICK %s" % e.network.nicks[0])
        e.network.raw("USER %s %s %s :%s" %
              (e.network.username, "8", "*", e.network.fullname))
              #per rfc2812 these are username, user mode flags, unused, realname
        
        #e.network.me = None
        e.done = True

def onDisconnect(e):
    if hasattr(e.network,'_reconnect_source'):
        e.network._reconnect_source.unregister()
        del e.network._reconnect_source
    if hasattr(e.network,'connect_timestamp'):
        if e.error and conf.get('autoreconnect',True):
            delay = time.time() - e.network.connect_timestamp > 30 and 30 or 120
            def do_reconnect():
                if not e.network.status:
                    server(network=e.network)
            def do_announce_reconnect():
                if not e.network.status:
                    windows.get_default(e.network).write("* Will reconnect in %s seconds.." % delay)
                    e.network._reconnect_source = ui.register_timer(delay*1000,do_reconnect)
            e.network._reconnect_source = ui.register_idle(do_announce_reconnect)

def onCloseNetwork(e):
    e.network.quit()
    if hasattr(e.network,'_reconnect_source'):
        e.network._reconnect_source.unregister()
        del e.network._reconnect_source

def setdownDisconnect(e):
    if hasattr(e.network,'connect_timestamp'):
        del e.network.connect_timestamp

def setupInput(e):
    if not e.done:
        if e.text.startswith(COMMAND_PREFIX) and not e.ctrl:
            command = e.text[len(COMMAND_PREFIX):]
        else:
            command = 'say - %s' % e.text

        core.events.run(command, e.window, e.network)
        
        e.done = True

def onCommandSay(e):
    if isinstance(e.window, windows.ChannelWindow) or isinstance(e.window, windows.QueryWindow):
        e.network.msg(e.window.id, ' '.join(e.args))
    else:
        raise core.events.CommandError("There's no one here to speak to.")

def onCommandMsg(e):
    e.network.msg(e.args[0], ' '.join(e.args[1:]))

def onCommandNotice(e):
    e.network.notice(e.args[0], ' '.join(e.args[1:]))

def onCommandQuery(e):
    windows.new(windows.QueryWindow, e.network, e.args[0], core).activate()
    if len(e.args) > 1:
        message = ' '.join(e.args[1:])
        if message: #this is false if you do "/query nickname " 
            e.network.msg(e.args[0], ' '.join(e.args[1:]))

def setupJoin(e):
    if e.source == e.network.me:
        chan = e.network.norm_case(e.channel)
        e.network.on_channels.add(chan)
        e.network.requested_joins.discard(chan)

def setdownPart(e):
    if e.source == e.network.me:
        chan = e.network.norm_case(e.channel)
        e.network.on_channels.discard(chan)
        e.network.requested_parts.discard(chan)

def setdownKick(e):
    if e.target == e.network.me:
        chan = e.network.norm_case(e.channel)
        e.network.on_channels.discard(chan)

def ischan(network, channel):
    return network.norm_case(channel) in network.on_channels

# make /nick work offline
def change_nick(network, nick):
    if not network.status:
        core.events.trigger(
            'Nick',
            network=network, window=windows.get_default(network),
            source=network.me, target=nick, address='', text=nick
            )
        network.nicks[0] = nick
        network.me = nick
    else:
        network.raw('NICK :%s' % nick)

def onCommandNick(e):
    default_nick = irc.default_nicks()[0]
    if 't' not in e.switches and e.network.me == default_nick:
        conf['nick'] = e.args[0]
        import conf as _conf
        _conf.save()
        for network in set(w.network for w in core.manager):
            if network.me == default_nick:
                change_nick(network, e.args[0])
    else:
        change_nick(e.network, e.args[0])

def setdownNick(e):
    if e.source != e.network.me:
        window = windows.get(windows.QueryWindow, e.network, e.source)
        if window:
            window.id = e.target

# make /quit always disconnect us
def onCommandQuit(e):
    if e.network.status:
        e.network.quit(' '.join(e.args))
    else:
        raise core.events.CommandError("We're not connected to a network.")

def onCommandRaw(e):
    if e.network.status >= irc.INITIALIZING:
        e.network.raw(' '.join(e.args))
    else:
        raise core.events.CommandError("We're not connected to a network.")

onCommandQuote = onCommandRaw

def onCommandJoin(e):
    if e.args:
        if e.network.status >= irc.INITIALIZING:
            e.network.join(' '.join(e.args), requested = 'n' not in e.switches)
        else:
            raise core.events.CommandError("We're not connected.")
    elif isinstance(e.window, windows.ChannelWindow):
        e.window.network.join(e.window.id, requested = 'n' not in e.switches)
    else:
        raise core.events.CommandError("You must supply a channel.")

def onCommandPart(e):
    if e.args:
        if e.network.status >= irc.INITIALIZING:
            e.network.part(' '.join(e.args), requested = 'n' not in e.switches)
        else:
            raise core.events.CommandError("We're not connected.")
    elif isinstance(e.window, windows.ChannelWindow):
        e.window.network.part(e.window.id, requested = 'n' not in e.switches)
    else:
        raise core.events.CommandError("You must supply a channel.")

def onCommandHop(e):
    if e.args:
        if e.network.status >= irc.INITIALIZING:
            e.network.part(e.args[0], requested = False)
            e.network.join(' '.join(e.args), requested = False)
        else:
            raise core.events.CommandError("We're not connected.")
    elif isinstance(e.window, windows.ChannelWindow):
        e.window.network.part(e.window.id, requested = False)
        e.window.network.join(e.window.id, requested = False)
    else:
        raise core.events.CommandError("You must supply a channel.")

#this should be used whereever a new irc.Network may need to be created
def server(server=None,port=6667,network=None,connect=True):
    network_info = {}
    
    if server:
        network_info["name"] = server
        network_info["server"] = server
        if port:
            network_info["port"] = port
        get_network_info(server, network_info)
    
    if not network:
        network = irc.Network(**network_info)
        windows.new(windows.StatusWindow, network, "status").activate()
    else:
        if "server" in network_info:
            network.name = network_info['name']
            network.server = network_info['server']
            if not network.status:
                #window = windows.get_default(network)
                window = core.window
                if window:
                    window.update()
        if "port" in network_info:
            network.port = network_info["port"]
    
    if network.status:
        network.quit()
    if connect:
        network.connect()
        core.window.write("* Connecting to %s on port %s" % (network.server, network.port))
        #windows.get_default(network).write(
        #            "* Connecting to %s on port %s" % (network.server, network.port)
        #    )
    
    return network

def onCommandServer(e):
    host = port = None
    
    if e.args:
        host = e.args[0]

        if ':' in host:
            host, port = host.rsplit(':', 1)
            port = int(port)
            
        elif len(e.args) > 1:
            port = int(e.args[1])

        else:
            port = 6667
    
    if 'm' in e.switches:    
        network = None
    else:
        network = e.network
    
    server(server=host, port=port, network=network, connect='o' not in e.switches)

#see http://www.w3.org/Addressing/draft-mirashi-url-irc-01.txt
def onCommandIrcurl(e):
    url = e.args[0]
    
    if url.startswith('irc://'):
        url = url[6:]
        
        if not url.startswith('/'):
            host, target = url.rsplit('/',1)
            if ':' in host:
                host, port = host.rsplit(':',1)
            else:
                port = 6667
        else:
            host = None
            port = 6667
            target = url
        
        if host:
            if e.network and e.network.server == host:
                network = e.network
            else:
                for w in list(windows.manager):
                    if w.network and w.network.server == host:
                        network = w.network
                        break
                else:
                    for w in list(windows.manager):
                        if w.network and w.network.server == 'irc.default.org':
                            network = server(host,port,w.network)
                            break
                    else:
                        network = server(host,port)
        
        if ',' in target:
            target, modifiers = target.split(',',1)
            action = ''
        else:
            target = unquote(target)
            if target[0] not in '#&+':
                target = '#'+target
            action = 'join %s' % target
        
        if network.status == irc.CONNECTED:
            core.events.run(action, windows.get_default(network), network)
        else:
            if not hasattr(network,'temp_perform'):
                network.temp_perform = [action]
            else:
                network.temp_perform.append(action)

#commands that we need to add a : to but otherwise can send unchanged
#the dictionary contains the number of arguments we take without adding the :
trailing = {
    'away':0,
    'cnotice':2,
    'cprivmsg':2,
    'kick':2,
    'kill':1,
    'part':1,
    'squery':1,
    'squit':1,
    'topic':1,
    'wallops':0,
    }

needschan = {
    'topic':0,
    'invite':1,
    'kick':0,
#    'mode':0, #this is commonly used for channels, but can apply to users
#    'names':0, #with no parameters, this is supposed to give a list of all users; we may be able to safely ignore that.
    }
    
def setupCommand(e):
    if not e.done: 
        if e.name in needschan and isinstance(e.window, windows.ChannelWindow):
            valid_chan_prefixes = e.network.isupport.get('CHANTYPES', '#&+')
            chan_pos = needschan[e.name]
            
            if len(e.args) > chan_pos:
                if not e.args[chan_pos] or e.args[chan_pos][0] not in valid_chan_prefixes:
                    e.args.insert(chan_pos, e.window.id)
            else:
                e.args.append(e.window.id)
        
        if e.name in trailing:
            trailing_pos = trailing[e.name]
        
            if len(e.args) > trailing_pos:
                e.args[trailing_pos] = ':%s' % e.args[trailing_pos]
        
        e.text = '%s %s' % (e.name, ' '.join(e.args))

def setdownCommand(e):
    if not e.done and e.network.status >= irc.INITIALIZING:
        e.network.raw(e.text)
        e.done = True
        
def get_network_info(name, network_info):
    conf_info = conf.get('networks', {}).get(name)

    if conf_info:
        network_info['server'] = name
        network_info.update(conf_info)

def onStart(e):
    for network in conf.get('start_networks', []):
        server(server=network)

def onConnect(e):
    network_info = conf.get('networks', {}).get(e.network.name, {})

    for command in network_info.get('perform', []):
        while command.startswith(COMMAND_PREFIX):
            command = command[len(COMMAND_PREFIX):]
        core.events.run(command, e.window, e.network)
    
    tojoin = ','.join(network_info.get('join', []))
    if tojoin:
        core.events.run('join -n %s' % tojoin, e.window, e.network)
    
    if hasattr(e.network,'temp_perform'):
        for command in e.network.temp_perform:
            core.events.run(command, e.window, e.network)
        del e.network.temp_perform

def isautojoin(network, channel):
    try:
        joinlist = conf['networks'][network.name]['join']
    except KeyError:
        return False
    normchannel = network.norm_case(channel)
    for chan in joinlist:
        if normchannel == network.norm_case(chan):
            return True
    return False

def setautojoin(network, channel):
    if 'networks' not in conf:
        conf['networks'] = networks = {}
    else:
        networks = conf['networks']
    if network.name not in networks:
        networks[network.name] = network_settings = {}
        if 'start_networks' not in conf:
            conf['start_networks'] = []
        conf['start_networks'].append(network.name)
    else:
        network_settings = networks[network.name]
    
    if 'join' not in network_settings:
        network_settings['join'] = [channel]
    else:
        network_settings['join'].append(channel)

def unsetautojoin(network, channel):
    try:
        joinlist = conf['networks'][network.name]['join']
    except KeyError:
        return False
    normchannel = network.norm_case(channel)
    for i, chan in enumerate(joinlist[:]):
        if normchannel == network.norm_case(chan):
            joinlist.pop(i)

def onChannelMenu(e):
    def toggle_join():
        if isautojoin(e.network, e.channel):
            unsetautojoin(e.network, e.channel)
        else:
            setautojoin(e.network, e.channel)
    
    e.menu.append(('Autojoin', isautojoin(e.network, e.channel), toggle_join))
