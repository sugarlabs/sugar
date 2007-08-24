####################################################################
# This class open the /proc/PID/maps and /proc/PID/smaps files
# to get useful information about the real memory usage
####################################################################

import os
import logging

_smaps_has_references = None

# Parse the /proc/PID/smaps file
class ProcSmaps:

    mappings = [] # Devices information
    
    def __init__(self, pid):
        global _smaps_has_references
        if _smaps_has_references is None:
            _smaps_has_references = os.path.isfile('/proc/%s/clear_refs' %
                                                   os.getpid())

        smapfile = "/proc/%s/smaps" % pid
        self.mappings = []
        
        # Coded by Federico Mena (script)
        infile = open(smapfile, "r")
        input = infile.read()
        infile.close()
        
        lines = input.splitlines()

        num_lines = len (lines)
        line_idx = 0
    
        # 08065000-08067000 rw-p 0001c000 03:01 147613     /opt/gnome/bin/evolution-2.6
        # Size:                 8 kB
        # Rss:                  8 kB
        # Shared_Clean:         0 kB
        # Shared_Dirty:         0 kB
        # Private_Clean:        8 kB
        # Private_Dirty:        0 kB
        # Referenced:           4 kb -> Introduced in kernel 2.6.22

        while num_lines > 0:
            fields = lines[line_idx].split (" ", 5)
            if len (fields) == 6:
                (offsets, permissions, bin_permissions, device, inode, name) = fields
            else:
                (offsets, permissions, bin_permissions, device, inode) = fields
                name = ""
    
            size          = self.parse_smaps_size_line (lines[line_idx + 1])
            rss           = self.parse_smaps_size_line (lines[line_idx + 2])
            shared_clean  = self.parse_smaps_size_line (lines[line_idx + 3])
            shared_dirty  = self.parse_smaps_size_line (lines[line_idx + 4])
            private_clean = self.parse_smaps_size_line (lines[line_idx + 5])
            private_dirty = self.parse_smaps_size_line (lines[line_idx + 6])
            if _smaps_has_references:
                referenced = self.parse_smaps_size_line (lines[line_idx + 7])
            else:
                referenced = None
            name = name.strip ()

            mapping = Mapping (size, rss, shared_clean, shared_dirty, \
                private_clean, private_dirty, referenced, permissions, name)
            self.mappings.append (mapping)

            if _smaps_has_references:
                num_lines -= 8
                line_idx += 8
            else:
                num_lines -= 7
                line_idx += 7
        
        if _smaps_has_references:
            self._clear_reference(pid)

    def _clear_reference(self, pid):
      os.system("echo 1 > /proc/%s/clear_refs" % pid)

    # Parses a line of the form "foo: 42 kB" and returns an integer for the "42" field
    def parse_smaps_size_line (self, line):
        # Rss:                  8 kB
        fields = line.split ()
        return int(fields[1])

class Mapping:
    def __init__ (self, size, rss, shared_clean, shared_dirty, \
            private_clean, private_dirty, referenced, permissions, name):
        self.size = size
        self.rss = rss
        self.shared_clean = shared_clean
        self.shared_dirty = shared_dirty
        self.private_clean = private_clean
        self.private_dirty = private_dirty
        self.referenced  = referenced
        self.permissions = permissions
        self.name = name

# Parse /proc/PID/maps file to get the clean memory usage by process,
# we avoid lines with backed-files
class ProcMaps:
    
    clean_size = 0
    
    def __init__(self, pid):
        mapfile = "/proc/%s/maps" % pid

        try:
            infile = open(mapfile, "r")
        except:
            print "Error trying " + mapfile
            return None
            
        sum = 0
        to_data_do = {
            "[anon]": self.parse_size_line,
            "[heap]": self.parse_size_line
        }
        
        for line in infile:
            arr = line.split()
            
            # Just parse writable mapped areas
            if arr[1][1] != "w":
                continue
            
            if len(arr) == 6:                
                # if we got a backed-file we skip this info
                if os.path.isfile(arr[5]):
                    continue
                else:
                    line_size = to_data_do.get(arr[5], self.skip)(line)
                    sum += line_size
            else:
                line_size = self.parse_size_line(line)
                sum += line_size
                    
        infile.close()
        self.clean_size = sum
        
    def skip(self, line):
        return 0
    
    # Parse a maps line and return the mapped size
    def parse_size_line(self, line):
        start, end = line.split()[0].split('-')
        size = int(end, 16) - int(start, 16)            
        return size
