# Copyright (C) 2007, 2008 One Laptop Per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
            locale_str = line.split()[1]
        elif line.find('title |') != -1:
            title = line.lstrip('title |')
        elif line.find('language |') != -1:
            lang = line.lstrip('language |')
            # Sometimes language is a language code, not the language name
            if len(lang) <= 3:
                lang = title.split()[0]
        elif line.find('territory |') != -1:
            territory = line.lstrip('territory |')
            # Sometimes territory is a territory code, not the territory name
            if len(territory) <= 3 and territory != 'USA':
                if ' locale for ' in title:
                    territory = title.split(' locale for ')[-1]
                    # Aesthetic cleanup up for titles with trailing .
                    if territory[-1] == '.':
                        territory = territory[:-1]
                else:
                    territory = title.split()[-1]
            if locale_str.endswith('utf8') and len(lang):
                locales.append((lang, territory, locale_str))

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
    path = os.path.join(os.environ.get('HOME', ''), '.i18n')
    # try avoid writing the file if the values didn't changed
    lang_line = None
    language_line = None
    other_lines = []
    try:
        with open(path) as fd:
            for line in fd:
                if line.startswith('LANG='):
                    lang_line = line
                elif line.startswith('LANGUAGE='):
                    language_line = line
                else:
                    other_lines.append(line)
    except:
        pass

    new_lang_line = 'LANG="%s"\n' % lang_env
    new_language_line = 'LANGUAGE="%s"\n' % language_env

    if lang_line == new_lang_line and language_line == new_language_line:
        return

    with open(path, 'w') as fd:
        fd.write(new_lang_line)
        fd.write(new_language_line)
        for line in other_lines:
            fd.write(line)
        fd.flush()
        # be sure all is flushed
        os.fsync(fd)


def _get_from_env(name):
    lang = os.environ[name]
    lang = lang.strip()
    if lang.endswith('UTF-8'):
        lang = lang.replace('UTF-8', 'utf8')
    return lang


def get_languages():
    # read the env variables set in bin/sugar
    langlist = None
    lang = _default_lang

    if 'LANGUAGE' in os.environ:
        lang = _get_from_env('LANGUAGE')
        langlist = lang.split(':')

    if 'LANG' in os.environ:
        lang = _get_from_env('LANG')

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
        for lang, territory, locale_str in langs:
            code = lang.replace(' ', '_') + '/' \
                + territory.replace(' ', '_')
            if code == languages:
                set_languages_list([locale_str])
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
