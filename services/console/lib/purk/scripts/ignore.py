from conf import conf
import irc

def preRaw(e):
    if e.msg[1] in ('PRIVMSG','NOTICE'):
        address = e.network.norm_case('%s!%s' % (e.source, e.address))
        for mask in conf.get('ignore_masks',()):
            if irc.match_glob(address, e.network.norm_case(mask)):
                core.events.halt()

def onCommandIgnore(e):
    if 'ignore_masks' not in conf:
        conf['ignore_masks'] = []
    if 'l' in e.switches:
        for i in conf['ignore_masks']:
            e.window.write('* %s' % i)
    elif 'c' in e.switches:
        del conf['ignore_masks']
        e.window.write('* Cleared the ignore list.')  
    elif e.args:
        if '!' in e.args[0] or '*' in e.args[0] or '?' in e.args[0]:
            mask = e.args[0]
        else:
            mask = '%s!*' % e.args[0]
        if 'r' in e.switches:
            if mask in conf['ignore_masks']:
                conf['ignore_masks'].remove(mask)
                e.window.write('* Removed %s from the ignore list' % e.args[0])
            else:
                raise core.events.CommandError("Couldn't find %s in the ignore list" % e.args[0])
        else:
            if mask in conf['ignore_masks']:
                e.window.write('* %s is already ignored' % e.args[0])
            else:
                conf['ignore_masks'].append(mask)
                e.window.write('* Ignoring messages from %s' % e.args[0])
    else:
        e.window.write(
"""Usage:
 /ignore \x02nick/mask\x02 to ignore a nickname or mask
 /ignore -r \x02nick/mask\x02 to stop ignoring a nickname or mask
 /ignore -l to view the ignore list
 /ignore -c to clear the ignore list""")
