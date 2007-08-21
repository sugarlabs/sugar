import irc
import ui
import windows
import irc_script
from conf import conf

# FIXME: meh still might want rid of these, I'm not sure yet

def onActive(e):
    e.window.activity = None

    ui.register_idle(windows.manager.set_title)

def setupNick(e):
    if e.source == e.network.me:
        for w in windows.get_with(core.manager, network=e.network):
            try:
                w.nick_label.update(e.target)
            except AttributeError:
                pass    

def onExit(e):
    for n in set(w.network for w in windows.manager):
        if n:
            n.quit()

def setupJoin(e):
    if e.source == e.network.me:
        window = windows.get(windows.StatusWindow, e.network, 'status', core)
        
        if window and not conf.get('status'):
            window.mutate(windows.ChannelWindow, e.network, e.target)
        else:
            window = windows.new(windows.ChannelWindow, e.network, e.target, core)
        
        if e.requested:
            window.activate()

    e.window = windows.get(windows.ChannelWindow, e.network, e.target, core) or e.window

def setupText(e):
    if e.target == e.network.me:
        e.window = windows.new(windows.QueryWindow, e.network, e.source, core)
    else:
        e.window = \
            windows.get(windows.ChannelWindow, e.network, e.target, core) or \
            windows.get(windows.QueryWindow, e.network, e.source, core) or \
            e.window

setupAction = setupText

def setupNotice(e):
    if e.target != e.network.me:
        e.window = \
            windows.get(windows.ChannelWindow, e.network, e.target, core) or e.window

def setupOwnText(e):
    e.window = \
        windows.get(windows.ChannelWindow, e.network, e.target, core) or \
        windows.get(windows.QueryWindow, e.network, e.target, core) or \
        e.window

setupOwnAction = setupOwnText

def setdownPart(e):
    if e.source == e.network.me:
        window = windows.get(windows.ChannelWindow, e.network, e.target, core)        
        
        if window:
            cwindows = list(windows.get_with(
                                network=window.network,
                                wclass=windows.ChannelWindow
                                ))
                            
            if len(cwindows) == 1 and not list(windows.get_with(network=window.network, wclass=windows.StatusWindow)):
                window.mutate(windows.StatusWindow, e.network, 'status')
                if e.requested:
                    window.activate()
            elif e.requested:
                window.close()

def onClose(e):
    nwindows = list(windows.get_with(core.manager, network=e.window.network))
    
    if isinstance(e.window, windows.ChannelWindow): 
        cwindows = list(windows.get_with(core.manager,
                            network=e.window.network,
                            wclass=windows.ChannelWindow
                            ))
        
        #if we only have one window for the network, don't bother to part as
        # we'll soon be quitting anyway
        if len(nwindows) != 1 and irc_script.ischan(e.window.network, e.window.id):
            e.window.network.part(e.window.id) 
    
    if len(nwindows) == 1:
        core.events.trigger("CloseNetwork", window=e.window, network=e.window.network)
    
    elif isinstance(e.window, windows.StatusWindow) and conf.get('status'):
        core.events.trigger("CloseNetwork", window=e.window, network=e.window.network)
        for window in nwindows:
            if window != e.window:
                window.close()
        
    if len(core.manager) == 1:
        windows.new(windows.StatusWindow, irc.Network(), "status", core)

def onConnecting(e):
    return
    window = windows.get_default(e.network)
    if window:
        window.update()

onDisconnect = onConnecting

def setupPart(e):
    e.window = windows.get(windows.ChannelWindow, e.network, e.target, core) or e.window

setupTopic = setupPart

def setupKick(e):
    e.window = windows.get(windows.ChannelWindow, e.network, e.channel, core) or e.window

def setupMode(e):
    if e.target != e.network.me:
        e.window = windows.get(windows.ChannelWindow, e.network, e.target, core) or e.window

def onWindowMenu(e):
    if isinstance(e.window, windows.ChannelWindow):
        e.channel = e.window.id
        e.network = e.window.network
        core.events.trigger('ChannelMenu', e)
