#!/usr/bin/env python

# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import sys
import os
import zipfile
import shutil
import subprocess
import re

from sugar import env
from sugar.activity.bundle import Bundle

class _SvnFileList(list):
    def __init__(self):
        f = os.popen('svn list -R')
        for line in f.readlines():
            filename = line.strip()
            if os.path.isfile(filename):
                self.append(filename)
        f.close()

class _GitFileList(list):
    def __init__(self):
        f = os.popen('git-ls-files')
        for line in f.readlines():
            filename = line.strip()
            if not filename.startswith('.'):
                self.append(filename)
        f.close()

class _DefaultFileList(list):
    def __init__(self):
        for name in os.listdir('activity'):
            if name.endswith('.svg'):
                self.append(os.path.join('activity', name))

        self.append('activity/activity.info')
        self.append('setup.py')

class _ManifestFileList(list):
    def __init__(self, manifest=None):
        self.append(manifest)

        f = open(manifest,'r')
        for line in f.readlines():
            self.append(line[:-1])
        f.close()

        defaults = _DefaultFileList()
        for path in defaults:
            self.append(path)

def _extract_bundle(source_file, dest_dir):
        if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)

        zf = zipfile.ZipFile(source_file)

        for i, name in enumerate(zf.namelist()):
            path = os.path.join(dest_dir, name)
            
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))

            outfile = open(path, 'wb')
            outfile.write(zf.read(name))
            outfile.flush()
            outfile.close()

def _get_source_path():
    return os.getcwd()

def _get_bundle_dir():
    bundle_name = os.path.basename(_get_source_path())
    return bundle_name + '.activity'    

def _get_install_dir(prefix):
    return os.path.join(prefix, 'share/activities')

def _get_package_name():
    bundle = Bundle(_get_source_path())
    zipname = '%s-%d.xo' % (bundle.get_name(), bundle.get_activity_version())
    return zipname
    
def _get_bundle_name():
    bundle = Bundle(_get_source_path())
    return bundle.get_name()

def _delete_backups(arg, dirname, names):
    for name in names:
        if name.endswith('~') or name.endswith('pyc'):
            os.remove(os.path.join(dirname, name))

def cmd_help():
    print 'Usage: \n\
setup.py dev                 - setup for development \n\
setup.py dist                - create a bundle package \n\
setup.py install   [dirname] - install the bundle \n\
setup.py uninstall [dirname] - uninstall the bundle \n\
setup.py genpot              - generate the gettext pot file \n\
setup.py genmo               - compile gettext po files in mo \n\
setup.py clean               - clean the directory \n\
setup.py help                - print this message \n\
'

def cmd_dev():
    bundle_path = env.get_user_activities_path()
    if not os.path.isdir(bundle_path):
        os.mkdir(bundle_path)
    bundle_path = os.path.join(bundle_path, _get_bundle_dir())
    try:
        os.symlink(_get_source_path(), bundle_path)
    except OSError:
        if os.path.islink(bundle_path):
            print 'ERROR - The bundle has been already setup for development.'
        else:
            print 'ERROR - A bundle with the same name is already installed.'    

def _get_file_list(manifest):
    if os.path.isfile(manifest):
        return _ManifestFileList(manifest)
    elif os.path.isdir('.git'):
        return _GitFileList()
    elif os.path.isdir('.svn'):
        return _SvnFileList()
    else:
        return _DefaultFileList()

def cmd_dist(manifest):
    file_list = _get_file_list(manifest)

    zipname = _get_package_name()
    bundle_zip = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    
    for filename in file_list:
        arcname = os.path.join(_get_bundle_name() + '.activity', filename)
        bundle_zip.write(filename, arcname)

    bundle_zip.close()

def cmd_install(prefix, manifest=None):
    cmd_dist(manifest)
    cmd_uninstall(prefix)
    _extract_bundle(_get_package_name(), _get_install_dir(prefix))

def cmd_uninstall(prefix):
    path = os.path.join(_get_install_dir(prefix), _get_bundle_dir())
    if os.path.isdir(path):
        shutil.rmtree(path)

def cmd_genpot(manifest):
    python_files = []
    file_list = _get_file_list(manifest)
    for file_name in file_list:
        if file_name.endswith('.py'):
            python_files.append(file_name)
    service_name = Bundle(_get_source_path()).get_service_name()
    args = ["xgettext", "--language=Python", "--keyword=_",
            "--output=locale/%s.pot" % service_name]
    args += python_files
    retcode = subprocess.call(args)
    if retcode:
        print 'ERROR - xgettext failed with return code %i.' % retcode

def cmd_genmo(manifest):
    po_regex = re.compile("locale/.*/LC_MESSAGES/.*\.po")
    service_name = Bundle(_get_source_path()).get_service_name()
    file_list = _get_file_list(manifest)
    for file_name in file_list:
        if po_regex.match(file_name):
            dir_name = os.path.dirname(file_name)
            mo_file = os.path.join(dir_name, "%s.mo" % service_name)
            args = ["msgfmt", "--output-file=%s" % mo_file, file_name]
            retcode = subprocess.call(args)
            if retcode:
                print 'ERROR - msgfmt failed with return code %i.' % retcode

def cmd_clean():
    os.path.walk('.', _delete_backups, None)

def start(manifest='MANIFEST'):
    if len(sys.argv) < 2:
        cmd_help()
    elif sys.argv[1] == 'build':
        pass
    elif sys.argv[1] == 'dev':
        cmd_dev()
    elif sys.argv[1] == 'dist':
        cmd_dist(manifest)
    elif sys.argv[1] == 'install' and len(sys.argv) == 3:
        cmd_install(sys.argv[2], manifest)
    elif sys.argv[1] == 'uninstall' and len(sys.argv) == 3:
        cmd_uninstall(sys.argv[2])
    elif sys.argv[1] == 'genpot':
        cmd_genpot(manifest)
    elif sys.argv[1] == 'genmo':
        cmd_genmo(manifest)
    elif sys.argv[1] == 'clean':
        cmd_clean()
    else:
        cmd_help()
        
if __name__ == '__main__':
    start()
