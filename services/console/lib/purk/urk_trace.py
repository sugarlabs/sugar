import sys
import commands
import linecache

import time

last_mem = [0]

def traceit_memory(frame, event, arg):
    if event == "line":
        mem = int(" " + commands.getoutput(
                "ps -eo cmd,rss | grep urk_trace.py | grep -v grep"
                ).split(" ")[-1])
                
        if mem > last_mem[0]:
            last_mem[0] = mem
            
            mem = str(mem)
        
            filename = frame.f_globals["__file__"]
            
            if filename.endswith(".pyc") or filename.endswith(".pyo"):
                filename = filename[:-1]
                
            name = frame.f_globals["__name__"]
        
            lineno = frame.f_lineno
            line = linecache.getline(filename,lineno).rstrip()

            data = "%s:%i: %s" % (name, lineno, line)

            print "%s%s" % (data, mem.rjust(80 - len(data)))

    return traceit_memory
    
lines = {}

def traceit(frame, event, arg):
    if event == "line":
        try:
            filename = frame.f_globals["__file__"]
            
            if filename.endswith(".pyc") or filename.endswith(".pyo"):
                filename = filename[:-1]
                
            name = frame.f_globals["__name__"]
        
            lineno = frame.f_lineno
            line = linecache.getline(filename,lineno).rstrip()

            data = "%s:%i: %s" % (name, lineno, line)
            
            print time.time(), data
            
            #if data in lines:
            #    lines[data] += 1
            #else:
            #    lines[data] = 1

        except Exception, e:
            print e

    return traceit
    
def main():
    import urk
    urk.main()

sys.settrace(traceit)
main()
