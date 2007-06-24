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

def cmd_help():
    print 'Usage: \n\
maint-helper.py build-snapshot - build a source snapshot \n\
maint-helper.py check-licenses - check licenses in the source'

def cmd_build_snapshot():
    [ name, version ] = get_name_and_version()

    cmd = 'git-show-ref --hash=10 refs/heads/master'
    alphatag = os.popen(cmd).readline().strip()

    tarball = '%s-%s-git%s.tar.bz2' % (name, version, alphatag)

    os.spawnlp(os.P_WAIT, 'make', 'make', 'distcheck')

    os.rename('%s-%s.tar.bz2' % (name, version), tarball)

def check_licenses(path, license, missing):
    matchers = { 'LGPL' : [ 'GNU Lesser General Public',
                            'GNU General Library License' ],
                 'GPL'  : [ 'GNU General Public License'  ] }
    source_exts = [ '.py', '.c', '.h', '.cpp' ]

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
            check_source = False
            for ext in source_exts:
                if item.endswith(ext):
                    check_source = True

            # Special cases.
            if item.find('marshal') > 0 or \
               item.startswith('egg') > 0:
                check_source = False

            if check_source:
                f = open(full_path, 'r')
                source = f.read()
                f.close()

                miss_license = True

                for matcher in matchers[license]:
                    if source.find(matcher) > 0:
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

if len(sys.argv) < 2:
    cmd_help()
elif sys.argv[1] == 'build-snapshot':
    cmd_build_snapshot()
elif sys.argv[1] == 'check-licenses':
    cmd_check_licenses()
