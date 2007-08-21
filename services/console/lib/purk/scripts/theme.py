import time

import windows
import widgets
import chaninfo

from conf import conf

textareas = {}
if 'font' in conf:
    textareas['font'] = conf['font']
if 'bg_color' in conf:
    textareas['bg'] = conf['bg_color']
if 'fg_color' in conf:
    textareas['fg'] = conf['fg_color']

widgets.set_style("view", textareas)
widgets.set_style("nicklist", textareas)

#copied pretty directly from something that was probably copied from wine sources
def RGBtoHSL(r, g, b):
    maxval = max(r, g, b)
    minval = min(r, g, b)
    
    luminosity = ((maxval + minval) * 240 + 255) // 510
    
    if maxval == minval:
        saturation = 0
        hue = 160
    else:
        delta = maxval - minval
        
        if luminosity <= 120:
            saturation = ((maxval+minval)//2 + delta*240) // (maxval + minval)
        else:
            saturation = ((150-maxval-minval)//2 + delta*240) // (150-maxval-minval)
        
        #sigh..
        rnorm = (delta//2 + maxval*40 - r*40)//delta
        gnorm = (delta//2 + maxval*40 - g*40)//delta
        bnorm = (delta//2 + maxval*40 - b*40)//delta
        
        if r == maxval:
            hue = bnorm-gnorm
        elif g == maxval:
            hue = 80+rnorm-bnorm
        else:
            hue = 160+gnorm-rnorm
        hue = hue % 240
    return hue, saturation, luminosity

#copied from the same place
def huetoRGB(hue, mid1, mid2):
    hue = hue % 240
    
    if hue > 160:
        return mid1
    elif hue > 120:
        hue = 160 - hue
    elif hue > 40:
        return mid2
    return ((hue * (mid2 - mid1) + 20) // 40) + mid1

#this too
def HSLtoRGB(hue, saturation, luminosity):
    if saturation != 0:
        if luminosity > 120:
            mid2 = saturation + luminosity - (saturation * luminosity + 120)//240
        else:
            mid2 = ((saturation + 240) * luminosity + 120)//240
        
        mid1 = luminosity * 2 - mid2
        
        return tuple((huetoRGB(hue+x, mid1, mid2) * 255 + 120) // 240 for x in (80,0,-80))
    else:
        value = luminosity * 255 // 240
        return value, value, value

def gethashcolor(string):
    h = hash(string)
    rgb = HSLtoRGB(h%241, 100-h//241%61, 90)
    return "%02x%02x%02x" % rgb

#take an event e and trigger the highlight event if necessary
def hilight_text(e):
    if not hasattr(e, 'Highlight'):
        e.Highlight = []
        core.events.trigger('Highlight', e)

#hilight own nick
def onHighlight(e):
    lowertext = e.text.lower()
    for word in conf.get('highlight_words', []) + [e.network.me] + e.network.nicks:
        lowerword = word.lower()
        pos = lowertext.find(lowerword, 0)
        while pos != -1:
            e.Highlight.append((pos, pos+len(word)))
            pos = lowertext.find(lowerword, pos+1)

def prefix(e):
    return time.strftime(conf.get('timestamp', ''))

def getsourcecolor(e):
    address = getattr(e, "address", "")
    if address:
        if e.network.me == e.source:
            e.network._my_address = address
    elif e.network.me == e.source:
        address = getattr(e.network, "_my_address", "")
    if '@' in address:
        address = address.split('@')[1]
    if not address:
        address = e.source
    return "\x04%s" % gethashcolor(address)

def format_source(e):
    highlight = getattr(e, "Highlight", "") and '\x02' or ''
    return "%s\x04%s%s" % (highlight, getsourcecolor(e), e.source)

def format_info_source(e):
    if e.source == e.network.me:
        return "\x04%sYou" % (getsourcecolor(e))
    else:
        return "\x04%s%s" % (getsourcecolor(e), e.source)

def address(e):
    #if e.source != e.network.me:
    #    return "%s " % info_in_brackets(e.address)
    #else:
    #    return ""
    return ""

def text(e):
    if e.text:
        #return " %s" % info_in_brackets(e.text)
        return ": \x0F%s" % e.text
    else:
        return ""
        
def info_in_brackets(text):
    return "(\x044881b6%s\x0F)" % text

def pretty_time(secs):
    times = (
        #("years", "year", 31556952),
        ("weeks", "week", 604800),
        ("days", "day", 86400),
        ("hours", "hour", 3600),
        ("minutes", "minute", 60),
        ("seconds", "second", 1),
        )
    if secs == 0:
        return "0 seconds"
    result = ""
    for plural, singular, amount in times:
        n, secs = divmod(secs, amount)
        if n == 1:
            result = result + " %s %s" % (n, singular)
        elif n:
            result = result + " %s %s" % (n, plural)
    return result[1:]

def onText(e):
    hilight_text(e)
    color = getsourcecolor(e)
    to_write = prefix(e)
    if e.network.me == e.target:    # this is a pm
        if e.window.id == e.network.norm_case(e.source):
            to_write += "\x02<\x0F%s\x0F\x02>\x0F " % (format_source(e))
        else:
            to_write += "\x02*\x0F%s\x0F\x02*\x0F " % (format_source(e))
    else:
        if e.window.id == e.network.norm_case(e.target):
            to_write += "\x02<\x0F%s\x0F\x02>\x0F " % (format_source(e))
        else:
            to_write += "\x02<\x0F%s:%s\x0F\x02>\x0F " % (format_source(e), e.target)
    to_write += e.text
    
    if e.Highlight:
        e.window.write(to_write, widgets.HILIT)
    else:
        e.window.write(to_write, widgets.TEXT)
    
def onOwnText(e):
    color = getsourcecolor(e)
    to_write = prefix(e)
    if e.window.id == e.network.norm_case(e.target):
        to_write += "\x02<\x0F%s\x0F\x02>\x0F %s" % (format_source(e), e.text)
    else:
        to_write += "%s->\x0F \x02*\x0F%s\x0F\x02*\x0F %s" % (color, e.target, e.text)
    
    e.window.write(to_write)
    
def onAction(e):
    hilight_text(e)
    color = color = getsourcecolor(e)
    to_write = "%s\x02*\x0F %s\x0F %s" % (prefix(e), format_source(e), e.text)
    
    if e.Highlight:
        e.window.write(to_write, widgets.HILIT)
    else:
        e.window.write(to_write, widgets.TEXT)
    
def onOwnAction(e):
    color = getsourcecolor(e)
    to_write = "%s\x02*\x0F %s\x0F %s" % (prefix(e), format_source(e), e.text)
    
    e.window.write(to_write)

def onNotice(e):
    hilight_text(e)
    color = getsourcecolor(e)
    to_write = prefix(e)
    if e.network.me == e.target:    # this is a pm
        to_write += "\x02-\x0F%s\x0F\x02-\x0F " % (format_source(e))
    else:
        to_write += "\x02-\x0F%s:%s\x0F\x02-\x0F " % (format_source(e), e.target)
    to_write += e.text
    
    e.window.write(to_write, (e.Highlight and widgets.HILIT) or widgets.TEXT)

def onOwnNotice(e):
    color = getsourcecolor(e)
    to_write = "%s-> \x02-\x02%s\x0F\x02-\x0F %s" % (prefix(e), e.target, e.text)
    
    e.window.write(to_write)

def onCtcp(e):
    color = getsourcecolor(e)
    to_write = "%s\x02[\x02%s\x0F\x02]\x0F %s" % (prefix(e), format_source(e), e.text)
    
    if not e.quiet:
        e.window.write(to_write)

def onCtcpReply(e):
    color = getsourcecolor(e)
    to_write = "%s%s--- %s reply from %s:\x0F %s" % (prefix(e), color, e.name.capitalize(), format_source(e), ' '.join(e.args))
    
    window = windows.manager.get_active()
    if window.network != e.network:
        window = windows.get_default(e.network)
    window.write(to_write, widgets.TEXT)

def onJoin(e):
    if e.source == e.network.me:
        to_write = "%s%s %sjoin %s" % (prefix(e), format_info_source(e), address(e), e.target)
    else:
        to_write = "%s%s %sjoins %s" % (prefix(e), format_info_source(e), address(e), e.target)

    e.window.write(to_write)
        
def onPart(e):
    if e.source == e.network.me:
        to_write = "%s%s leave %s%s" % (prefix(e), format_info_source(e), e.target, text(e))
    else:
        to_write = "%s%s leaves %s%s" % (prefix(e), format_info_source(e), e.target, text(e))
    
    e.window.write(to_write)

def onKick(e):
    if e.source == e.network.me:
        to_write = "%s%s kick %s%s" % (prefix(e), format_info_source(e), e.target, text(e))
    else:
        to_write = "%s%s kicks %s%s" % (prefix(e), format_info_source(e), e.target, text(e))
    
    e.window.write(to_write, (e.target == e.network.me and widgets.HILIT) or widgets.EVENT)
        
def onMode(e):
    if e.source == e.network.me:
        to_write = "%s%s set mode:\x0F %s" % (prefix(e), format_info_source(e), e.text)
    else:
        to_write = "%s%s sets mode:\x0F %s" % (prefix(e), format_info_source(e), e.text)
    
    e.window.write(to_write)
        
def onQuit(e):
    to_write = "%s%s leaves%s" % (prefix(e), format_info_source(e), text(e))
    
    for channame in chaninfo.channels(e.network):
        if chaninfo.ison(e.network, channame, e.source):
            window = windows.get(windows.ChannelWindow, e.network, channame, core)
            if window:
                window.write(to_write)

def onNick(e):
    color = getsourcecolor(e)
    if e.source == e.network.me:
        to_write = "%s%sYou are now known as %s" % (prefix(e), color, e.target)
    else:
        to_write = "%s%s%s is now known as %s" % (prefix(e), color, e.source, e.target)
    
    if e.source == e.network.me:
        for window in windows.get_with(core.manager, network=e.network):
            window.write(to_write)
    else:
        for channame in chaninfo.channels(e.network):
            if chaninfo.ison(e.network,channame,e.source):
                window = windows.get(windows.ChannelWindow, e.network, channame)
                if window:
                    window.write(to_write)

def onTopic(e):
    if e.source == e.network.me:
        to_write = "%s%s set topic:\x0F %s" % (prefix(e), format_info_source(e), e.text)
    else:
        to_write = "%s%s sets topic:\x0F %s" % (prefix(e), format_info_source(e), e.text)
    
    e.window.write(to_write)

def onRaw(e):
    if not e.quiet:
        if e.msg[1].isdigit():
            if e.msg[1] == '332':
                window = windows.get(windows.ChannelWindow, e.network, e.msg[3], core) or e.window
                window.write(
                    "%sTopic on %s is: %s" % 
                        (prefix(e), e.msg[3], e.text)
                        )
                
            elif e.msg[1] == '333':
                window = windows.get(windows.ChannelWindow, e.network, e.msg[3], core) or e.window
                window.write(
                    "%sTopic on %s set by %s at time %s" % 
                        (prefix(e), e.msg[3], e.msg[4], time.ctime(int(e.msg[5])))
                        )
            
            elif e.msg[1] == '329': #RPL_CREATIONTIME
                pass
            
            elif e.msg[1] == '311': #RPL_WHOISUSER
                e.window.write("* %s is %s@%s * %s" % (e.msg[3], e.msg[4], e.msg[5], e.msg[7]))
            
            elif e.msg[1] == '312': #RPL_WHOISSERVER
                e.window.write("* %s on %s (%s)" % (e.msg[3], e.msg[4], e.msg[5]))
            
            elif e.msg[1] == '317': #RPL_WHOISIDLE
                e.window.write("* %s has been idle for %s" % (e.msg[3], pretty_time(int(e.msg[4]))))
                if e.msg[5].isdigit():
                    e.window.write("* %s signed on %s" % (e.msg[3], time.ctime(int(e.msg[5]))))
            
            elif e.msg[1] == '319': #RPL_WHOISCHANNELS
                e.window.write("* %s on channels: %s" % (e.msg[3], e.msg[4]))
            
            elif e.msg[1] == '330': #RPL_WHOISACCOUNT
                #this appears to conflict with another raw, so if there's anything weird about it,
                # we fall back on the default
                if len(e.msg) == 6 and not e.msg[4].isdigit() and not e.msg[5].isdigit():
                    e.window.write("* %s %s %s" % (e.msg[3], e.msg[5], e.msg[4]))
                else:
                    e.window.write("* %s" % ' '.join(e.msg[3:]))
            
            else:
                e.window.write("* %s" % ' '.join(e.msg[3:]))
        elif e.msg[1] == 'ERROR':
            e.window.write("Error: %s" % e.text)

def onDisconnect(e):
    to_write = '%s* Disconnected' % prefix(e)
    if e.error:
        to_write += ' (%s)' % e.error

    for window in windows.get_with(network=e.network):
        if isinstance(window, windows.StatusWindow):
            window.write(to_write, widgets.TEXT)
        else:
            window.write(to_write, widgets.EVENT)
