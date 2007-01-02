###########################################################
# Main function:
# -----------------
# self:  self plugin object
# mself: memphis object / principal class
# pinfo: row with information about current tracing process
############################################################

def plg_on_top_data_refresh(self, pinfo):
    PI = self.INTERNALS['Plg'].proc
    
    pid = pinfo['pid']
    
    # Get JIFFIES CPU usage
    used_jiffies = pinfo['utime'] + pinfo['stime']
    last_ujiffies = get_pid_ujiffies(self, pid)
    
    cpu_usage = PI.get_CPU_usage(self.cpu_hz, used_jiffies, pinfo['start_time'])

    # Get PERCENT CPU usage
    if last_ujiffies == 0.0:
        pcpu = 0.0
        set_pid_ujiffies(self, pid, cpu_usage['used_jiffies'])
        data = [int(pcpu)]
        return data
                
    used_jiffies  = cpu_usage['used_jiffies'] - last_ujiffies

    # Available jiffies are
    avail_jiffies = (500/1000.0)*self.cpu_hz # 500 = 0.5 second
    pcpu = ((used_jiffies*100)/avail_jiffies)
    
    set_pid_ujiffies(self, pid, cpu_usage['used_jiffies'])
        
    data = [int(pcpu)]
    return data

def get_pid_ujiffies(self, pid):
    
    if pid in self.pids_ujiffies:
        return self.pids_ujiffies[pid]
    else:
        set_pid_ujiffies(self, pid, 0)
        return self.pids_ujiffies[pid]

def set_pid_ujiffies(self, pid, ujiffies):
    self.pids_ujiffies[pid] = ujiffies

