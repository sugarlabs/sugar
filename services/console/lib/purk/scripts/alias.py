import sys
import os

from conf import conf

aliases = conf.get("aliases",{
    'op':'"mode "+window.id+" +"+"o"*len(args)+" "+" ".join(args)',
    'deop':'"mode "+window.id+" -"+"o"*len(args)+" "+" ".join(args)',
    'voice':'"mode "+window.id+" +"+"v"*len(args)+" "+" ".join(args)',
    'devoice':'"mode "+window.id+" -"+"v"*len(args)+" "+" ".join(args)',
    'umode':'"mode "+network.me+" "+" ".join(args)',
    'clear':'window.output.clear()',
    })

class CommandHandler:
    __slots__ = ["command"]
    def __init__(self, command):
        self.command = command
    def __call__(self, e):
        loc = sys.modules.copy()
        loc.update(e.__dict__)
        result = eval(self.command,loc)
        if isinstance(result,basestring):
            core.events.run(result,e.window,e.network)

for name in aliases:
    globals()['onCommand'+name.capitalize()] = CommandHandler(aliases[name])

def onCommandAlias(e):
    if e.args and 'r' in e.switches:
        name = e.args[0].lower()
        command = aliases[name]
        del aliases[name]
        conf['aliases'] = aliases
        e.window.write("* Deleted alias %s%s (was %s)" % (conf.get('command-prefix','/'),name,command))
        core.events.load(__name__,reloading=True)
    elif 'l' in e.switches:
        e.window.write("* Current aliases:")
        for i in aliases:
            e.window.write("*  %s%s: %s" % (conf.get('command-prefix','/'),i,aliases[i]))
    elif len(e.args) >= 2:
        name = e.args[0].lower()
        command = ' '.join(e.args[1:])
        aliases[name] = command
        conf['aliases'] = aliases
        e.window.write("* Created an alias %s%s to %s" % (conf.get('command-prefix','/'),name,command))
        core.events.reload(__name__)
    elif len(e.args) == 1:
        name = e.args[0].lower()
        if name in aliases:
            e.window.write("* %s%s is an alias to %s" % (conf.get('command-prefix','/'),name,aliases[name]))
        else:
            e.window.write("* There is no alias %s%s" % (conf.get('command-prefix','/'),name))
    else:
        e.window.write(
"""Usage:
 /alias \x02name\x02 \x02expression\x02 to create or replace an alias
 /alias \x02name\x02 to look at an alias
 /alias -r \x02name\x02 to remove an alias
 /alias -l to see a list of aliases""")
