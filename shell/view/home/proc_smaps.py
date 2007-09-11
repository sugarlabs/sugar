# Copyright (C) 2007 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
# USA

import os

# /proc/PID/maps consists of a number of lines like this:
# 00400000-004b1000 r-xp 00000000 fd:00 5767206                  /bin/bash
# 006b1000-006bb000 rw-p 000b1000 fd:00 5767206                  /bin/bash
# 006bb000-006c0000 rw-p 006bb000 00:00 0 
# ...
# The fields are: address, permissions, offset, device, inode, and
# (for non-anonymous mappings) pathname.
#
# /proc/PID/smaps gives additional information for each mapping:
# 00400000-004b1000 r-xp 00000000 fd:00 5767206                  /bin/bash
# Size:               708 kB
# Rss:                476 kB
# Shared_Clean:       468 kB
# Shared_Dirty:         0 kB
# Private_Clean:        8 kB
# Private_Dirty:        0 kB
# Referenced:           0 kb
#
# The "Referenced" line only appears in kernel 2.6.22 and later.

def get_shared_mapping_names(pid):
    """Returns a set of the files for which PID has a shared mapping"""
    
    mappings = set()
    infile = open("/proc/%s/maps" % pid, "r")
    for line in infile:
        # sharable mappings are non-anonymous and either read-only
        # (permissions "r-..") or writable but explicitly marked
        # shared ("rw.s")
        fields = line.split()
        if len(fields) < 6 or not fields[5].startswith('/'):
            continue
        if fields[1][0] != 'r' or (fields[1][1] == 'w' and fields[1][3] != 's'):
            continue
        mappings.add(fields[5])
    infile.close()
    return mappings

_smaps_lines_per_entry = None

def get_mappings(pid, ignored_shared_mappings):
    """Returns a list of (name, private, shared) tuples describing the
    memory mappings of PID. Shared mappings named in
    ignored_shared_mappings are ignored
    """

    global _smaps_lines_per_entry
    if _smaps_lines_per_entry is None:
        if os.path.isfile('/proc/%s/clear_refs' % os.getpid()):
            _smaps_lines_per_entry = 8
        else:
            _smaps_lines_per_entry = 7

    mappings = []
    
    smapfile = "/proc/%s/smaps" % pid
    infile = open(smapfile, "r")
    input = infile.read()
    infile.close()
    lines = input.splitlines()

    for line_idx in range(0, len(lines), _smaps_lines_per_entry):
        name_idx = lines[line_idx].find('/')
        if name_idx == -1:
            name = None
        else:
            name = lines[line_idx][name_idx:]
    
        private_clean = int(lines[line_idx + 5][14:-3])
        private_dirty = int(lines[line_idx + 6][14:-3])
        if name in ignored_shared_mappings:
            shared_clean = 0
            shared_dirty = 0
        else:
            shared_clean = int(lines[line_idx + 3][14:-3])
            shared_dirty = int(lines[line_idx + 4][14:-3])

        mapping = Mapping(name, private, shared)
        mappings.append (mapping)

    return mappings

class Mapping:
    def __init__ (self, name, private, shared):
        self.name = name
        self.private = private
        self.shared = shared
