#!/usr/bin/env python

# Copyright (C) 2007, Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import sys
import re

def get_name_and_version():
    f = open('configure.ac', 'r')
    config = f.read()
    f.close()

    exp = 'AC_INIT\(\[[^\]]+\],\[([^\]]+)\],\[\],\[([^\]]+)\]'
    match = re.search(exp, config)
    if not match:
        print 'Cannot find the package name and version.'
        sys.exit(0)

    return [ match.group(2), match.group(1) ]


[ name, version ] = get_name_and_version()

cmd = 'git-show-ref --hash=10 refs/heads/master'
alphatag = os.popen(cmd).readline().strip()

tarball = '%s-%s-git%s.tar.bz2' % (name, version, alphatag)

os.spawnlp(os.P_WAIT, 'make', 'make', 'distcheck')

os.rename('%s-%s.tar.bz2' % (name, version), tarball)
