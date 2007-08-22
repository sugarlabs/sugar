import os
import sys
import traceback
import events
import windows

urkpath = os.path.abspath(os.path.dirname(__file__))

if os.path.abspath(os.curdir) != os.path.join(urkpath):
    sys.path[0] = os.path.join(urkpath)    

sys.path = [
    os.path.join(urkpath, "scripts"),
    ] + sys.path

script_path = urkpath+"/scripts"

from ui import *

# Here I'm trying to handle the original URL IRC Client, urk don't use
# normal classes . Let's try to get a urk widget:
class Trigger(object):
    def __init__(self):
        self._mods = []
        self.events = events
        self._load_scripts()

    def _load_scripts(self):
        script_path = urkpath + "/scripts"
        try:
            suffix = os.extsep+"py"
            for script in os.listdir(script_path):
                if script.endswith(suffix):
                    try:
                        mod = self.events.load(script)
                        self._mods.append(mod)
                    except:
                        traceback.print_exc()
                        print "Failed loading script %s." % script
        except OSError:
            pass

    def get_modules(self):
        return self._mods

class Core(object):
    def __init__(self):
        self.window = None
        self.trigger = Trigger()
        self.events = self.trigger.events
        self.manager = widgets.UrkUITabs(self)
        self.channels = []

        mods = self.trigger.get_modules()
        for m in mods:
            m.core = self
            m.manager = self.manager

        if not self.window:
           self.window = windows.new(windows.StatusWindow, irc.Network(self), "status", self)
           self.window.activate()

        register_idle(self.trigger_start)
        gtk.gdk.threads_enter()

    def run_command(self, command):
        offset = 0
        if command[0] == '/':
            offset = 1

        self.events.run(command[offset:], self.manager.get_active(), self.window.network)

    def trigger_start(self):
        self.events.trigger("Start")

    def _add_script(self, module):
        return 

class Client(object):
    def __init__(self):
        self.core = Core()
        self.widget = self.core.manager.box
    
    def run_command(self, command):
        self.core.run_command(command)

    def join_server(self, network_name, port=6667):
        command = 'server '+ network_name + ' ' + str(port)
        self.run_command(command)

    def get_widget(self):
        return self.widget

    def show(self):
        self.widget.show_all()

    def add_channel(self, channel):
        self.core.channels.append(channel)

    def clear_channels(self):
        self.core.channels = []
