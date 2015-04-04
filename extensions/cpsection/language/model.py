# Copyright (C) 2007, 2008 One Laptop Per Child
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
#
#
# The language config is based on the system-config-language
# (http://fedoraproject.org/wiki/SystemConfig/language) tool
# Parts of the code were reused.
#

import os
import locale
from gettext import gettext as _
import subprocess


_default_lang = '%s.%s' % locale.getdefaultlocale()
_standard_msg = _('Could not access ~/.i18n. Create standard settings.')


def read_all_languages():
    fdp = subprocess.Popen(['locale', '-av'], stdout=subprocess.PIPE)
    lines = fdp.stdout.read().split('\n')
    locales = []

    for line in lines:
        if line.find('locale:') != -1:
            locale = line.split()[1]
        elif line.find('language |') != -1:
            lang = line.lstrip('language |')
        elif line.find('territory |') != -1:
            territory = line.lstrip('territory |')
            if locale.endswith('utf8') and len(lang):
                locales.append((lang, territory, locale))

    # FIXME: This is a temporary workaround for locales that are essential to
    # OLPC, but are not in Glibc yet.
    locales.append(('Kreyol', 'Haiti', 'ht_HT.utf8'))
    locales.append(('Dari', 'Afghanistan', 'fa_AF.utf8'))
    locales.append(('Pashto', 'Afghanistan', 'ps_AF.utf8'))

    locales.sort()
    return locales


def _initialize():
    if set_languages.__doc__ is None:
        # when running under 'python -OO', all __doc__ fields are None,
        # so += would fail -- and this function would be unnecessary anyway.
        return
    languages = read_all_languages()
    set_languages.__doc__ += '\n'
    for lang in languages:
        set_languages.__doc__ += '%s \n' % (lang[0].replace(' ', '_') + '/' +
                                            lang[1].replace(' ', '_'))


def _write_i18n(lang_env, language_env):
    path = os.path.join(os.environ.get('HOME'), '.i18n')
    if not os.access(path, os.W_OK):
        print _standard_msg
        fd = open(path, 'w')
        fd.write('LANG="%s"\n' % _default_lang)
        fd.write('LANGUAGE="%s"\n' % _default_lang)
        fd.close()
    else:
        fd = open(path, 'w')
        fd.write('LANG="%s"\n' % lang_env)
        fd.write('LANGUAGE="%s"\n' % language_env)
        fd.close()


def get_languages():
    path = os.path.join(os.environ.get('HOME', ''), '.i18n')
    if not os.access(path, os.R_OK):
        print _standard_msg
        fd = open(path, 'w')
        fd.write('LANG="%s"\n' % _default_lang)
        fd.write('LANGUAGE="%s"\n' % _default_lang)
        fd.close()
        return [_default_lang]

    fd = open(path, 'r')
    lines = fd.readlines()
    fd.close()

    langlist = None

    for line in lines:
        if line.startswith('LANGUAGE='):
            lang = line[9:].replace('"', '')
            lang = lang.strip()
            langlist = lang.split(':')
        elif line.startswith('LANG='):
            lang = line[5:].replace('"', '')

    # There might be cases where .i18n may not contain a LANGUAGE field
    if langlist is None:
        return [lang]
    else:
        return langlist


def print_languages():
    codes = get_languages()

    languages = read_all_languages()
    for code in codes:
        found_lang = False
        for lang in languages:
            if lang[2].split('.')[0] == code.split('.')[0]:
                print lang[0].replace(' ', '_') + '/' + \
                    lang[1].replace(' ', '_')
                found_lang = True
                break
        if not found_lang:
            print (_('Language for code=%s could not be determined.') % code)


def set_languages(languages):
    """Set the system language.
    languages :
    """

    if isinstance(languages, list):
        set_languages_list(languages)
        return

    if languages.endswith('utf8'):
        set_languages_list([languages])
        return 1
    else:
        langs = read_all_languages()
        for lang, territory, locale in langs:
            code = lang.replace(' ', '_') + '/' \
                + territory.replace(' ', '_')
            if code == languages:
                set_languages_list([locale])
                return 1
        print (_("Sorry I do not speak \'%s\'.") % languages)


def set_languages_list(languages):
    """Set the system language using a list of preferred languages"""
    colon = ':'
    language_env = colon.join(languages)
    lang_env = languages[0].strip('\n')
    _write_i18n(lang_env, language_env)


# inilialize the docstrings for the language
_initialize()
