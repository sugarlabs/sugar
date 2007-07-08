# Copyright (C) 2006-2007 Red Hat, Inc.
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

        if os.path.isfile(_get_source_path('NEWS')):
            self.append('NEWS')

class _ManifestFileList(list):
    def __init__(self, manifest=None):
        self.append(manifest)

        f = open(manifest,'r')
        for line in f.readlines():
            stripped_line = line.strip()
            if stripped_line:
                self.append(stripped_line)
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

def _get_source_path(path=None):
    if path:
        return os.path.join(os.getcwd(), path)
    else:
        return os.getcwd()

def _get_bundle_dir():
    bundle_name = os.path.basename(_get_source_path())
    return bundle_name + '.activity'    

def _get_install_dir(prefix):
    return os.path.join(prefix, 'share/activities')

def _get_package_name(bundle_name):
    bundle = Bundle(_get_source_path())
    zipname = '%s-%d.xo' % (bundle_name, bundle.get_activity_version())
    return zipname

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
setup.py release             - do a new release of the bundle \n\
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

def _include_mo_in_bundle(bundle_zip, bundle_name):
    for langdir in os.listdir('locale'):
        if os.path.isdir(os.path.join('locale', langdir, 'LC_MESSAGES')):
            for filename in os.listdir(os.path.join('locale', langdir,
                                                    'LC_MESSAGES')):
                if filename.endswith('.mo'):
                    arcname = os.path.join(bundle_name + '.activity',
                                           'locale', langdir, 'LC_MESSAGES',
                                           filename)
                    bundle_zip.write(
                        os.path.join('locale', langdir, 'LC_MESSAGES', filename),
                        arcname)

def cmd_dist(bundle_name, manifest):
    cmd_genmo(bundle_name, manifest)
    file_list = _get_file_list(manifest)

    zipname = _get_package_name(bundle_name)
    bundle_zip = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    
    for filename in file_list:
        arcname = os.path.join(bundle_name + '.activity', filename)
        bundle_zip.write(filename, arcname)

    if os.path.exists('locale'):
        _include_mo_in_bundle(bundle_zip, bundle_name)

    bundle_zip.close()

def cmd_install(bundle_name, manifest, prefix):
    cmd_dist(bundle_name, manifest)
    cmd_uninstall(prefix)

    _extract_bundle(_get_package_name(bundle_name),
                    _get_install_dir(prefix))

def cmd_uninstall(prefix):
    path = os.path.join(_get_install_dir(prefix), _get_bundle_dir())
    if os.path.isdir(path):
        shutil.rmtree(path)

def cmd_genpot(bundle_name, manifest):
    po_path = os.path.join(_get_source_path(), 'po')
    if not os.path.isdir(po_path):
        os.mkdir(po_path)

    python_files = []
    file_list = _get_file_list(manifest)
    for file_name in file_list:
        if file_name.endswith('.py'):
            python_files.append(file_name)

    pot_file = os.path.join('po', '%s.pot' % bundle_name)
    args = [ 'xgettext', '--language=Python',
             '--keyword=_', '--output=%s' % pot_file ]

    args += python_files
    retcode = subprocess.call(args)
    if retcode:
        print 'ERROR - xgettext failed with return code %i.' % retcode

    po_regex = re.compile("po/.*\.po$")
    for file_name in _get_file_list(manifest):
        if po_regex.match(file_name):
            args = [ 'msgmerge', '-U', file_name, pot_file ]
            retcode = subprocess.call(args)
            if retcode:
                print 'ERROR - msgmerge failed with return code %i.' % retcode    

def cmd_genmo(bundle_name, manifest):
    source_path = _get_source_path()

    po_regex = re.compile("po/(.*)\.po$")
    for file_name in _get_file_list(manifest):
        match = po_regex.match(file_name)
        if match:
            lang = match.group(1)

            mo_path = os.path.join(source_path, 'locale', lang, 'LC_MESSAGES')
            if not os.path.isdir(mo_path):
                os.makedirs(mo_path)

            mo_file = os.path.join(mo_path, "%s.mo" % bundle_name)
            args = ["msgfmt", "--output-file=%s" % mo_file, file_name]
            retcode = subprocess.call(args)
            if retcode:
                print 'ERROR - msgfmt failed with return code %i.' % retcode

def cmd_release(bundle_name, manifest):
    if not os.path.isdir('.git'):
        print 'ERROR - this command works only for git repositories'

    print 'Bumping activity version...'

    info_path = os.path.join(_get_source_path(), 'activity', 'activity.info')
    f = open(info_path,'r')
    info = f.read()
    f.close()

    exp = re.compile('activity_version\s?=\s?([1-9]*)')
    match = re.search(exp, info)
    version = int(match.group(1)) + 1
    info = re.sub(exp, 'activity_version = %d' % version, info)

    f = open(info_path, 'w')
    f.write(info)
    f.close()

    news_path = os.path.join(_get_source_path(), 'NEWS')

    if os.environ.has_key('SUGAR_NEWS'):
        print 'Update NEWS.sugar...'

        sugar_news_path = os.environ['SUGAR_NEWS']
        if os.path.isfile(sugar_news_path):
            f = open(sugar_news_path,'r')
            sugar_news = f.read()
            f.close()
        else:
            sugar_news = ''

        sugar_news += '%s - %d\n\n' % (bundle_name, version)

        f = open(news_path,'r')
        for line in f.readline():
            if len(line) > 0:
                sugar_news += line
            else:
                break
        f.close()

        sugar_news += '\n'

        f = open(sugar_news_path, 'w')
        f.write(sugar_news)
        f.close()

    print 'Update NEWS...'

    f = open(news_path,'r')
    news = f.read()
    f.close()

    news = '%d\n\n' % version + news

    f = open(news_path, 'w')
    f.write(news)
    f.close()

    print 'Committing to git...'

    changelog = 'Release version %d.' % version
    retcode = subprocess.call(['git', 'commit', '-a', '-m % s' % changelog])
    if retcode:
        print 'ERROR - cannot commit to git'

    retcode = subprocess.call(['git', 'push'])
    if retcode:
        print 'ERROR - cannot push to git'

    print 'Creating the bundle...'
    cmd_dist(bundle_name, manifest)

    if os.environ.has_key('ACTIVITIES_REPOSITORY'):
        print 'Uploading to the activities repository...'
        repo = os.environ['ACTIVITIES_REPOSITORY']

        server, path = repo.split(':')
        retcode = subprocess.call(['ssh', server, 'mv',
                                   '%s/%s*' % (path, bundle_name),
                                   '%s/old' % path])
        if retcode:
            print 'ERROR - cannot remove old bundles from the repository.'

        bundle_path = os.path.join(_get_source_path(),
                                   _get_package_name(bundle_name))
        retcode = subprocess.call(['scp', bundle_path, repo])
        if retcode:
            print 'ERROR - cannot upload the bundle to the repository.'

    print 'Done.'

def cmd_clean():
    os.path.walk('.', _delete_backups, None)

def sanity_check():
    if not os.path.isfile(_get_source_path('NEWS')):
        print 'WARNING: NEWS file is missing.'

def start(bundle_name=None, manifest='MANIFEST'):
    if not bundle_name:
        bundle_name = os.path.basename(_get_source_path())

    sanity_check()

    if len(sys.argv) < 2:
        cmd_help()
    elif sys.argv[1] == 'build':
        pass
    elif sys.argv[1] == 'dev':
        cmd_dev()
    elif sys.argv[1] == 'dist':
        cmd_dist(bundle_name, manifest)
    elif sys.argv[1] == 'install' and len(sys.argv) == 3:
        cmd_install(bundle_name, manifest, sys.argv[2])
    elif sys.argv[1] == 'uninstall' and len(sys.argv) == 3:
        cmd_uninstall(sys.argv[2])
    elif sys.argv[1] == 'genpot':
        cmd_genpot(bundle_name, manifest)
    elif sys.argv[1] == 'genmo':
        cmd_genmo(bundle_name, manifest)
    elif sys.argv[1] == 'clean':
        cmd_clean()
    elif sys.argv[1] == 'release':
        cmd_release(bundle_name, manifest)
    else:
        cmd_help()
        
if __name__ == '__main__':
    start()
