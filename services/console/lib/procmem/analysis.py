import proc, proc_smaps

class Analysis:
    
    pid = 0
    
    def __init__(self, pid):
        self.pid = pid
    
    def SMaps(self):
        smaps =    proc_smaps.ProcSmaps(self.pid)
        private_dirty = 0
        shared_dirty = 0
        referenced = 0

        for map in smaps.mappings:
            private_dirty += map.private_dirty
            shared_dirty  += map.shared_dirty
            referenced += map.referenced

        smaps = {"private_dirty": int(private_dirty), \
                    "shared_dirty": int(shared_dirty),\
                    "referenced": int(referenced)}

        return smaps
    
    def ApproxRealMemoryUsage(self):
        maps = proc_smaps.ProcMaps(self.pid)
        size = (maps.clean_size/1024)

        return size
    