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
import gettext

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

        if os.path.isfile(_get_source_path('NEWS')):
            self.append('NEWS')

class _ManifestFileList(_DefaultFileList):
    def __init__(self, manifest):
        _DefaultFileList.__init__(self)
        self.append(manifest)

        f = open(manifest,'r')
        for line in f.readlines():
            stripped_line = line.strip()
            if stripped_line and not stripped_line in self:
                self.append(stripped_line)
        f.close()

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

def _get_service_name():
    bundle = Bundle(_get_source_path())
    return bundle.get_service_name()

def cmd_help():
    print 'Usage: \n\
setup.py dev                 - setup for development \n\
setup.py dist                - create a bundle package \n\
setup.py install   [dirname] - install the bundle \n\
setup.py uninstall [dirname] - uninstall the bundle \n\
setup.py genpot              - generate the gettext pot file \n\
setup.py genl10n             - generate localization files \n\
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

def _get_po_list(manifest):
    file_list = {}

    po_regex = re.compile("po/(.*)\.po$")
    for file_name in _get_file_list(manifest):
        match = po_regex.match(file_name)
        if match:
            file_list[match.group(1)] = file_name

    return file_list

def _get_l10n_list(manifest):
    l10n_list = []

    for lang in _get_po_list(manifest).keys():
        filename = _get_service_name() + '.mo'
        l10n_list.append(os.path.join('locale', lang, 'LC_MESSAGES', filename))
        l10n_list.append(os.path.join('locale', lang, 'activity.linfo'))

    return l10n_list

def _get_activity_name():
    info_path = os.path.join(_get_source_path(), 'activity', 'activity.info')
    f = open(info_path,'r')
    info = f.read()
    f.close()
    match = re.search('^name\s*=\s*(.*)$', info, flags = re.MULTILINE)
    return match.group(1)

def cmd_dist(bundle_name, manifest):
    cmd_genl10n(bundle_name, manifest)
    file_list = _get_file_list(manifest)

    zipname = _get_package_name(bundle_name)
    bundle_zip = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    base_dir = bundle_name + '.activity'
    
    for filename in file_list:
        bundle_zip.write(filename, os.path.join(base_dir, filename))

    for filename in _get_l10n_list(manifest):
        bundle_zip.write(filename, os.path.join(base_dir, filename))

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

    # First write out a stub .pot file containing just the translated
    # activity name, then have xgettext merge the rest of the
    # translations into that. (We can't just append the activity name
    # to the end of the .pot file afterwards, because that might
    # create a duplicate msgid.)
    pot_file = os.path.join('po', '%s.pot' % bundle_name)
    activity_name = _get_activity_name()
    escaped_name = re.sub('([\\\\"])', '\\\\\\1', activity_name)
    f = open(pot_file, 'w')
    f.write('#: activity/activity.info:2\n')
    f.write('msgid "%s"\n' % escaped_name)
    f.write('msgstr ""\n')
    f.close()

    args = [ 'xgettext', '--join-existing', '--language=Python',
             '--keyword=_', '--output=%s' % pot_file ]

    args += python_files
    retcode = subprocess.call(args)
    if retcode:
        print 'ERROR - xgettext failed with return code %i.' % retcode

    for file_name in _get_po_list(manifest).values():
        args = [ 'msgmerge', '-U', file_name, pot_file ]
        retcode = subprocess.call(args)
        if retcode:
            print 'ERROR - msgmerge failed with return code %i.' % retcode    

def cmd_genl10n(bundle_name, manifest):
    source_path = _get_source_path()
    activity_name = _get_activity_name()

    po_list = _get_po_list(manifest)
    for lang in po_list.keys():
        file_name = po_list[lang]

        localedir = os.path.join(source_path, 'locale', lang)
        mo_path = os.path.join(localedir, 'LC_MESSAGES')
        if not os.path.isdir(mo_path):
            os.makedirs(mo_path)

        mo_file = os.path.join(mo_path, "%s.mo" % _get_service_name())
        args = ["msgfmt", "--output-file=%s" % mo_file, file_name]
        retcode = subprocess.call(args)
        if retcode:
            print 'ERROR - msgfmt failed with return code %i.' % retcode

        cat = gettext.GNUTranslations(open(mo_file, 'r'))
        translated_name = cat.gettext(activity_name)
        linfo_file = os.path.join(localedir, 'activity.linfo')
        f = open(linfo_file, 'w')
        f.write('[Activity]\nname = %s\n' % translated_name)
        f.close()

def cmd_release(bundle_name, manifest):
    if not os.path.isdir('.git'):
        print 'ERROR - this command works only for git repositories'

    retcode = subprocess.call(['git', 'pull'])
    if retcode:
        print 'ERROR - cannot pull from git'

    print 'Bumping activity version...'

    info_path = os.path.join(_get_source_path(), 'activity', 'activity.info')
    f = open(info_path,'r')
    info = f.read()
    f.close()

    exp = re.compile('activity_version\s?=\s?([0-9]*)')
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
        for line in f.readlines():
            if len(line.strip()) > 0:
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
        retcode = subprocess.call(['ssh', server, 'rm',
                                   '%s/%s*' % (path, bundle_name)])
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

def start(bundle_name, manifest='MANIFEST'):
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
    elif sys.argv[1] == 'genl10n':
        cmd_genl10n(bundle_name, manifest)
    elif sys.argv[1] == 'clean':
        cmd_clean()
    elif sys.argv[1] == 'release':
        cmd_release(bundle_name, manifest)
    else:
        cmd_help()
        
if __name__ == '__main__':
    start()
