import sys
import traceback
import windows
from conf import conf

class ConsoleWriter:
    __slots__ = ['window']
    def __init__(self, window):
        self.window = window
    def write(self, text):
        try:
            self.window.write(text, line_ending='')
        except:
            self.window.write(traceback.format_exc())

class ConsoleWindow(windows.SimpleWindow):
    def __init__(self, network, id):
        windows.SimpleWindow.__init__(self, network, id)
    
        writer = ConsoleWriter(self)
        
        sys.stdout = writer
        sys.stderr = writer
        
        self.globals = {'window': self}
        self.locals = {}

#this prevents problems (and updates an open console window) on reload
#window = None
#for window in manager:
#    if type(window).__name__ == "ConsoleWindow":
#        window.mutate(ConsoleWindow, window.network, window.id)
#del window

def onClose(e):
    if isinstance(e.window, ConsoleWindow):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

def onCommandConsole(e):
    windows.new(ConsoleWindow, None, "console").activate() 

def onCommandSay(e):
    if isinstance(e.window, ConsoleWindow):
        import pydoc #fix nonresponsive help() command
        old_pager, pydoc.pager = pydoc.pager, pydoc.plainpager 
        e.window.globals.update(sys.modules)
        text = ' '.join(e.args)
        try:
            e.window.write(">>> %s" % text) 
            result = eval(text, e.window.globals, e.window.locals)
            if result is not None:
                e.window.write(repr(result))
            e.window.globals['_'] = result
        except SyntaxError:
            try:
                exec text in e.window.globals, e.window.locals
            except:
                traceback.print_exc()
        except:
            traceback.print_exc()
        pydoc.pager = old_pager
    else:
        raise core.events.CommandError("There's no one here to speak to.")

def onStart(e):
    if conf.get('start-console'):
        windows.new(ConsoleWindow, None, "console")
