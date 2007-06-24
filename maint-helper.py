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
import datetime

source_exts = [ '.py', '.c', '.h', '.cpp' ]

def is_source(path):
    for ext in source_exts:
        if path.endswith(ext):
            return True

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

def cmd_help():
    print 'Usage: \n\
maint-helper.py build-snapshot       - build a source snapshot \n\
maint-helper.py fix-copyright [path] - fix the copyright year \n\
maint-helper.py check-licenses       - check licenses in the source'

def cmd_build_snapshot():
    [ name, version ] = get_name_and_version()

    cmd = 'git-show-ref --hash=10 refs/heads/master'
    alphatag = os.popen(cmd).readline().strip()

    tarball = '%s-%s-git%s.tar.bz2' % (name, version, alphatag)

    os.spawnlp(os.P_WAIT, 'make', 'make', 'distcheck')

    os.rename('%s-%s.tar.bz2' % (name, version), tarball)

def check_licenses(path, license, missing):
    matchers = { 'LGPL' : 'GNU Lesser General Public',
                 'GPL'  : 'GNU General Public License' }

    license_file = os.path.join(path, '.license')
    if os.path.isfile(license_file):
        f = open(license_file, 'r')
        license = f.readline().strip()
        f.close()

    for item in os.listdir(path):
        full_path = os.path.join(path, item)

        if os.path.isdir(full_path):
            check_licenses(full_path, license, missing)
        else:
            check_source = is_source(item)

            # Special cases.
            if item.find('marshal') > 0 or \
               item.startswith('egg') > 0:
                check_source = False

            if check_source:
                f = open(full_path, 'r')
                source = f.read()
                f.close()

                miss_license = True
                if source.find(matchers[license]) > 0:
                    miss_license = False

                # Special cases.
                if source.find('THIS FILE IS GENERATED') > 0:
                    miss_license = False

                if miss_license:
                    if not missing.has_key(license):
                        missing[license] = []
                    missing[license].append(full_path)

def cmd_check_licenses():
    missing = {}
    check_licenses(os.getcwd(), 'GPL', missing)

    for item in missing.keys():
        print '%s:\n' % item
        for path in missing[item]:
            print path
        print '\n'

COPYRIGHT = 'Copyright (C) '

def fix_copyright(path):
    for item in os.listdir(path):
        full_path = os.path.join(path, item)

        if os.path.isdir(full_path):
            fix_copyright(full_path)
        elif is_source(item):
            f = open(full_path, 'r')
            source = f.read()
            f.close()

            year_start = -1
            year_end = -1

            i1 = source.find(COPYRIGHT)
            if i1 != -1:
                i1 += len(COPYRIGHT)
                i2 = i1 + source[i1:].find(' ')
                if i1 > 0:
                    try:
                        year_start = int(source[i1:i1 + 4])
                        year_end = int(source[i1 + 6: i1 + 10])
                    except ValueError:
                        pass

                if year_start > 0 and year_end < 0:
                    year_end = year_start

                year = datetime.date.today().year
                if year_end < year:
                    result = '%s%d-%d%s' % (source[:i1], year_start,
                                            year, source[i2:])
                    f = open(full_path, 'w')
                    f.write(result)
                    f.close()

def cmd_fix_copyright(path):
    fix_copyright(path)

if len(sys.argv) < 2:
    cmd_help()
elif sys.argv[1] == 'build-snapshot':
    cmd_build_snapshot()
elif sys.argv[1] == 'check-licenses':
    cmd_check_licenses()
elif sys.argv[1] == 'fix-copyright' and len(sys.argv) > 2:
    cmd_fix_copyright(sys.argv[2])
