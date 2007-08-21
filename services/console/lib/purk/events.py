import sys
import os
import traceback

pyending = os.extsep + 'py'

class error(Exception):
    pass

class EventStopError(error):
    pass

class CommandError(error):
    pass

class data(object):
    done = False
    quiet = False
    
    def __init__(self, **kwargs):
        for attr in kwargs.items():
            setattr(self, *attr)

trigger_sequence = ("pre", "setup", "on", "setdown", "post")

all_events = {}
loaded = {}

# An event has occurred, the e_name event!
def trigger(e_name, e_data=None, **kwargs):
    if e_data is None:
        e_data = data(**kwargs)
    
    #print 'Event:', e_name, e_data
    
    failure = True
    error = None
    
    if e_name in all_events:
        for e_stage in trigger_sequence:
            if e_stage in all_events[e_name]:
                for f_ref, s_name in all_events[e_name][e_stage]:
                    try:
                        f_ref(e_data)
                    except EventStopError:
                        return
                    except CommandError, e:
                        error = e.args
                        continue
                    except:
                        traceback.print_exc()
                    failure = False
    if failure:
        print "Error handling: " + e_name
        
        return error

# Stop all processing of the current event now!
def halt():
    raise EventStopError

# Registers a specific function with an event at the given sequence stage.
def register(e_name, e_stage, f_ref, s_name=""):
    global all_events
    
    if e_name not in all_events:
        all_events[e_name] = {}
        
    if e_stage not in all_events[e_name]:
        all_events[e_name][e_stage] = []

    all_events[e_name][e_stage] += [(f_ref, s_name)]

# turn a filename (or module name) and trim it to the name of the module
def get_scriptname(name):
    s_name = os.path.basename(name)
    if s_name.endswith(pyending):
        s_name = s_name[:-len(pyending)]
    return s_name

#take a given script name and turn it into a filename
def get_filename(name):
    # split the directory and filename
    dirname = os.path.dirname(name)
    s_name = get_scriptname(name)
    
    for path in dirname and (dirname,) or sys.path:
        filename = os.path.join(path, s_name + pyending)
        if os.access(filename, os.R_OK):
            return filename

    raise ImportError("No urk script %s found" % name) 

# register the events defined by obj
def register_all(name, obj):
    # we look through everything defined in the file    
    for f in dir(obj):
        # for each bit of the event sequence
        for e_stage in trigger_sequence:

            # if the function is for this bit
            if f.startswith(e_stage):
                # get a reference to a function
                f_ref = getattr(obj, f)
                #print f
                # normalise to the event name                
                e_name = f.replace(e_stage, "", 1)
                
                # add our function to the right event section
                register(e_name, e_stage, f_ref, name)
                
                break

#load a .py file into a new module object without affecting sys.modules
def load_pyfile(filename):
    s_name = get_scriptname(filename)
    return __import__(s_name)

# Load a python script and register
# the functions defined in it for events.
# Return True if we loaded the script, False if it was already loaded
def load(name):
    s_name = get_scriptname(name)
    filename = get_filename(name)

    if s_name in loaded:
        return False
    
    loaded[s_name] = None
    
    try:
        module = load_pyfile(filename)
        loaded[s_name] = module
    except:
        del loaded[s_name]
        raise
    
    register_all(s_name, loaded[s_name])

    return module

# Is the script with the given name loaded?
def is_loaded(name):
    return get_scriptname(name) in loaded

# Remove any function which was defined in the given script
def unload(name):
    s_name = get_scriptname(name)
    
    del loaded[s_name]

    for e_name in list(all_events):
        for e_stage in list(all_events[e_name]):
            to_check = all_events[e_name][e_stage]

            all_events[e_name][e_stage] = [(f, m) for f, m in to_check if m != s_name]
            
            if not all_events[e_name][e_stage]:
                del all_events[e_name][e_stage]
        
        if not all_events[e_name]:
            del all_events[e_name]

def reload(name):
    s_name = get_scriptname(name)

    if s_name not in loaded:
        return False
    
    temp = loaded[s_name]
    
    unload(s_name)

    try:
        load(name)
        return True
    except:
        loaded[s_name] = temp
        register_all(s_name, temp)
        raise

def run(text, window, network):
    split = text.split(' ')

    c_data = data(name=split.pop(0), text=text, window=window, network=network)
    
    if split and split[0].startswith('-'):
        c_data.switches = set(split.pop(0)[1:])
    else:
        c_data.switches = set()
    
    c_data.args = split

    event_name = "Command" + c_data.name.capitalize()
    #print "searching: " + event_name
    #for s in all_events:
    #    print "match: " + s
    #    if s == event_name:
    #        print "we got it!"
    
    if event_name in all_events:
        result = trigger(event_name, c_data)
        
        if result:
            print "* /%s: %s" % (c_data.name, result[0])
            c_data.window.write("* /%s: %s" % (c_data.name, result[0]))
    else:
        trigger("Command", c_data)

        if not c_data.done:
            c_data.window.write("* /%s: No such command exists" % (c_data.name))

def onCommandPyeval(e):
    loc = sys.modules.copy()
    loc.update(e.__dict__)
    import pydoc #fix nonresponsive help() command
    old_pager, pydoc.pager = pydoc.pager, pydoc.plainpager 
    try:
        result = repr(eval(' '.join(e.args), loc))
        if 's' in e.switches:
            run(
                'say - %s => %s' % (' '.join(e.args),result),
                e.window,
                e.network
                )
        else:
            e.window.write(result)
    except:
        for line in traceback.format_exc().split('\n'):
            e.window.write(line)
    pydoc.pager = old_pager

def onCommandPyexec(e):
    loc = sys.modules.copy()
    loc.update(e.__dict__)
    import pydoc #fix nonresponsive help() command
    old_pager, pydoc.pager = pydoc.pager, pydoc.plainpager 
    try:
        exec ' '.join(e.args) in loc
    except:
        for line in traceback.format_exc().split('\n'):
            e.window.write(line)
    pydoc.pager = old_pager

def onCommandLoad(e):
    if e.args:
        name = e.args[0]
    else:
        e.window.write('Usage: /load scriptname')

    try:
        if load(name):
            e.window.write("* The script '%s' has been loaded." % name)
        else:
            raise CommandError("The script is already loaded; use /reload instead")
    except:
        e.window.write(traceback.format_exc(), line_ending='')
        raise CommandError("Error loading the script")

def onCommandUnload(e):
    if e.args:
        name = e.args[0]
    else:
        e.window.write('Usage: /unload scriptname')

    if is_loaded(name):
        unload(name)
        e.window.write("* The script '%s' has been unloaded." % name)
    else:
        raise CommandError("No such script is loaded")

def onCommandReload(e):
    if e.args:
        name = e.args[0]
    else:
        e.window.write('Usage: /reload scriptname')

    try:
        if reload(name):
            e.window.write("* The script '%s' has been reloaded." % name)
        else:
            raise CommandError("The script isn't loaded yet; use /load instead") 
    except:
        e.window.write(traceback.format_exc(), line_ending='')

def onCommandScripts(e):
    e.window.write("Loaded scripts:")
    for name in loaded:
        e.window.write("* %s" % name)

def onCommandEcho(e):
    e.window.write(' '.join(e.args))

name = ''
for name in globals():
    if name.startswith('onCommand'):
        register(name[2:], "on", globals()[name], '_all_events')
del name
