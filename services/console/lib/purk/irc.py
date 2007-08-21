import socket
import sys

from conf import conf
import ui
import windows
import info

DISCONNECTED = 0
CONNECTING = 1
INITIALIZING = 2
CONNECTED = 3

def parse_irc(msg, server):
    msg = msg.split(' ')
    
    # if our very first character is :
    # then this is the source, 
    # otherwise insert the server as the source
    if msg and msg[0].startswith(':'):
        msg[0] = msg[0][1:]
    else:
        msg.insert(0, server)
    
    # loop through the msg until we find 
    # something beginning with :
    for i, token in enumerate(msg):
        if token.startswith(':'):
            # remove the :
            msg[i] = msg[i][1:]
            
            # join up the rest
            msg[i:] = [' '.join(msg[i:])]
            break
    
    # filter out the empty pre-":" tokens and add on the text to the end
    return [m for m in msg[:-1] if m] + msg[-1:]
    
    # note: this sucks and makes very little sense, but it matches the BNF
    #       as far as we've tested, which seems to be the goal

def default_nicks():
    try:
        nicks = [conf.get('nick')] + conf.get('altnicks',[])
        if not nicks[0]:
            import getpass
            nicks = [getpass.getuser()]
    except:
        nicks = ["mrurk"]
    return nicks

class Network(object):
    socket = None
    
    def __init__(self, core, server="irc.default.org", port=6667, nicks=[], 
                    username="", fullname="", name=None, **kwargs):
        self.core = core
        self.manager = core.manager
        self.server = server
        self.port = port
        self.events = core.events

        self.name = name or server
        
        self.nicks = nicks or default_nicks()
        self.me = self.nicks[0]
        
        self.username = username or "urk"
        self.fullname = fullname or conf.get("fullname", self.username)
        self.password = ''
        
        self.isupport = {
            'NETWORK': server, 
            'PREFIX': '(ohv)@%+',
            'CHANMODES': 'b,k,l,imnpstr',
        }
        self.prefixes = {'o':'@', 'h':'%', 'v':'+', '@':'o', '%':'h', '+':'v'}
        
        self.status = DISCONNECTED
        self.failedhosts = [] #hosts we've tried and failed to connect to
        self.channel_prefixes = '&#+$'   # from rfc2812
        
        self.on_channels = set()
        self.requested_joins = set()
        self.requested_parts = set()
        
        self.buffer = ''
    
    #called when we get a result from the dns lookup
    def on_dns(self, result, error):
        if error:
            self.disconnect(error=error[1])
        else:
            #import os
            #import random
            #random.seed()
            #random.shuffle(result)
            if socket.has_ipv6: #prefer ipv6
                result = [(f, t, p, c, a) for (f, t, p, c, a) in result if f == socket.AF_INET6]+result
            elif hasattr(socket,"AF_INET6"): #ignore ipv6
                result = [(f, t, p, c, a) for (f, t, p, c, a) in result if f != socket.AF_INET6]
            
            self.failedlasthost = False
            
            for f, t, p, c, a in result:
                if (f, t, p, c, a) not in self.failedhosts:
                    try:
                        self.socket = socket.socket(f, t, p)
                    except:
                        continue
                    self.source = ui.fork(self.on_connect, self.socket.connect, a)
                    self.failedhosts.append((f, t, p, c, a))
                    if set(self.failedhosts) >= set(result):
                        self.failedlasthost = True
                    break
            else:
                self.failedlasthost = True
                if len(result):
                    self.failedhosts[:] = (f, t, p, c, a),
                    f, t, p, c, a = result[0]
                    try:
                        self.socket = socket.socket(f, t, p)
                        self.source = ui.fork(self.on_connect, self.socket.connect, a)
                    except:
                        self.disconnect(error="Couldn't find a host we can connect to")
                else:
                    self.disconnect(error="Couldn't find a host we can connect to")
    
    #called when socket.open() returns
    def on_connect(self, result, error):
        if error:
            self.disconnect(error=error[1])
            #we should immediately retry if we failed to open the socket and there are hosts left
            if self.status == DISCONNECTED and not self.failedlasthost:
                windows.get_default(self, self.core.manager).write("* Retrying with next available host")
                self.connect()
        else:
            self.source = source = ui.Source()
            self.status = INITIALIZING
            self.failedhosts[:] = ()
            
            self.events.trigger('SocketConnect', network=self)
            
            if source.enabled:
                self.source = ui.fork(self.on_read, self.socket.recv, 8192)
        
        # Auto join channels on connect
        for channel in self.core.channels:
            self.core.run_command("/join %s" % channel)

    #called when we read data or failed to read data
    def on_read(self, result, error):
        if error:
            self.disconnect(error=error[1])
        elif not result:
            self.disconnect(error="Connection closed by remote host")
        else:
            self.source = source = ui.Source()
            
            self.buffer = (self.buffer + result).split("\r\n")
            
            for line in self.buffer[:-1]:
                self.got_msg(line)
            
            if self.buffer:
                self.buffer = self.buffer[-1]
            else:
                self.buffer = ''
            
            if source.enabled:
                self.source = ui.fork(self.on_read, self.socket.recv, 8192)    

    def raw(self, msg):
        self.events.trigger("OwnRaw", network=self, raw=msg)
        
        if self.status >= INITIALIZING:
            self.socket.send(msg + "\r\n")
        
    def got_msg(self, msg):
        pmsg = parse_irc(msg, self.server)
    
        e_data = self.events.data(
                    raw=msg,
                    msg=pmsg,
                    text=pmsg[-1],
                    network=self,
                    window=windows.get_default(self, self.manager)
                    )
        
        if "!" in pmsg[0]:
            e_data.source, e_data.address = pmsg[0].split('!',1)
            
        else:
            e_data.source, e_data.address = pmsg[0], ''
        
        if len(pmsg) > 2:
            e_data.target = pmsg[2]
        else:
            e_data.target = pmsg[-1]
        
        self.events.trigger('Raw', e_data)
    
    def connect(self):
        if not self.status:
            self.status = CONNECTING
            
            self.source = ui.fork(self.on_dns, socket.getaddrinfo, self.server, self.port, 0, socket.SOCK_STREAM)
            
            self.events.trigger('Connecting', network=self)
    
    def disconnect(self, error=None):
        if self.socket:
            self.socket.close()
        
        if self.source:
            self.source.unregister()
            self.source = None
        
        self.socket = None
        
        self.status = DISCONNECTED
        
        #note: connecting from onDisconnect is probably a Bad Thing
        self.events.trigger('Disconnect', network=self, error=error)
        
        #trigger a nick change if the nick we want is different from the one we
        # had.
        if self.me != self.nicks[0]:
            self.events.trigger(
                'Nick', network=self, window=windows.get_default(self),
                source=self.me, target=self.nicks[0], address='',
                text=self.nicks[0]
                )
            self.me = self.nicks[0]
        
    def norm_case(self, string):
        return string.lower()
    
    def quit(self, msg=None):
        if self.status:
            try:
                if msg == None:
                    msg = conf.get('quitmsg', "%s - %s" % (info.long_version, info.website))
                self.raw("QUIT :%s" % msg)
            except:
                pass
            self.disconnect()
        
    def join(self, target, key='', requested=True):
        if key:
            key = ' '+key
        self.raw("JOIN %s%s" % (target,key))
        if requested:
            for chan in target.split(' ',1)[0].split(','):
                if chan == '0':
                    self.requested_parts.update(self.on_channels)
                else:
                    self.requested_joins.add(self.norm_case(chan))
        
    def part(self, target, msg="", requested=True):
        if msg:
            msg = " :" + msg
        
        self.raw("PART %s%s" % (target, msg))
        if requested:
            for chan in target.split(' ',1)[0].split(','):
                self.requested_parts.add(self.norm_case(target))
        
    def msg(self, target, msg):
        self.raw("PRIVMSG %s :%s" % (target, msg))
        
        self.events.trigger(
            'OwnText', source=self.me, target=str(target), text=msg,
            network=self, window=windows.get_default(self, self.manager)
            )

    def notice(self, target, msg):
        self.raw("NOTICE %s :%s" % (target, msg))
        
        self.events.trigger(
            'OwnNotice', source=self.me, target=str(target), text=msg,
            network=self, window=windows.get_default(self)
            )

#a Network that is never connected
class DummyNetwork(Network):
    def __nonzero__(self):
        return False    
    
    def __init__(self, core):
        Network.__init__(self, core)
        
        self.name = self.server = self.isupport['NETWORK'] = "None"
    
    def connect(self):
        raise NotImplementedError, "Cannot connect dummy network."
    
    def raw(self, msg):
        raise NotImplementedError, "Cannot send %s over the dummy network." % repr(msg)

#dummy_network = DummyNetwork()

#this was ported from srvx's tools.c
def match_glob(text, glob, t=0, g=0):
    while g < len(glob):
        if glob[g] in '?*':
            star_p = q_cnt = 0
            while g < len(glob):
                if glob[g] == '*':
                    star_p = True
                elif glob[g] == '?':
                    q_cnt += 1
                else:
                    break
                g += 1
            t += q_cnt
            if t > len(text):
                return False
            if star_p:
                if g == len(glob):
                    return True
                for i in xrange(t, len(text)):
                    if text[i] == glob[g] and match_glob(text, glob, i+1, g+1):
                        return True
                return False
            else:
                if t == len(text) and g == len(glob):
                    return True
        if t == len(text) or g == len(glob) or text[t] != glob[g]:
            return False
        t += 1
        g += 1
    return t == len(text)
