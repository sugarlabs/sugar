#!/usr/bin/env python

import sys, os
import string

class ProcInfo:

    dir_path    = "/proc/"    # Our cute Proc File System
    status_file = "status"
    stat_file    = "stat"
    
    proc_list = [] # Our PID list :D
    proc_info = [] # 
    
    def __init__(self):
        self.proc_list = self.Get_PID_List()
        
    # Returns Process List
    def Get_PID_List(self):
        list = []
        
        # Exists our procfs ?
        if os.path.isdir(self.dir_path):
            # around dir entries
            for f in os.listdir(self.dir_path):
                if os.path.isdir(self.dir_path+f) & str.isdigit(f):
                        list.append(int(f))

        return list
    
    def MemoryInfo(self, pid):
        # Path
        pidfile = self.dir_path + str(pid) + "/stat"
        try:
            infile = open(pidfile, "r")
        except:
            print "Error trying " + pidfile
            return None

        # Parsing data , check 'man 5 proc' for details
        data = infile.read().split()

        infile.close()
        
        state_dic = {
                    'R': 'Running',
                    'S': 'Sleeping', 
                    'D': 'Disk sleep',
                    'Z': 'Zombie', 
                    'T': 'Traced/Stopped', 
                    'W': 'Paging'
                    }

        # user and group owners
        pidstat = os.stat(pidfile)
        
        info = {
            'pid':        int(data[0]), # Process ID
            'name':        data[1].strip('()'), # Process name
            'state':    data[2], # Process State, ex: R|S|D|Z|T|W
            'state_name':    state_dic[data[2]], # Process State name, ex: Running, sleeping, Zombie, etc
            'ppid':        int(data[3]), # Parent process ID
            'utime':    int(data[13]), # Used jiffies in user mode
            'stime':    int(data[14]), # Used jiffies in kernel mode
            'start_time':    int(data[21]), # Process time from system boot (jiffies)
            'vsize':    int(data[22]), # Virtual memory size used (bytes)
            'rss':        int(data[23])*4,    # Resident Set Size (bytes)
            'user_id': pidstat.st_uid, # process owner
            'group_id': pidstat.st_gid # owner group
        }
        
        return info
        

    # Returns the CPU usage expressed in Jiffies
    def get_CPU_usage(self, cpu_hz, used_jiffies, start_time):
        
        # Uptime info
        uptime_file = self.dir_path + "/uptime"
        try:
            infile = file(uptime_file, "r")
        except:
            print "Error trying uptime file"
            return None
        
        uptime_line = infile.readline()
        uptime = string.split(uptime_line, " ",2)
        
        infile.close()
                
        # System uptime, from /proc/uptime
        uptime = float(uptime[0])
        
        # Jiffies
        avail_jiffies = (uptime * cpu_hz) - start_time
        
        cpu_usage = {'used_jiffies': used_jiffies, 'avail_jiffies': avail_jiffies}

        return cpu_usage

