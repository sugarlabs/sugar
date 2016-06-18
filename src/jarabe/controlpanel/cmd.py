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

import sys
import getopt
import os
from gettext import gettext as _
import logging

from jarabe import config


_RESTART = 1

_same_option_warning = _('sugar-control-panel: WARNING, found more than one'
                         ' option with the same name: %s module: %r')
_no_option_error = _('sugar-control-panel: key=%s not an available option')
_general_error = _('sugar-control-panel: %s')


def cmd_help():
    """Print the help to the screen"""
    # TRANS: Translators, there's a empty line at the end of this string,
    # which must appear in the translated string (msgstr) as well.
    print _('Usage: sugar-control-panel [ option ] key [ args ... ] \n\
    Control for the sugar environment. \n\
    Options: \n\
    -h           show this help message and exit \n\
    -l           list all the available options \n\
    -h key       show information about this key \n\
    -g key       get the current value of the key \n\
    -s key       set the current value for the key \n\
    -c key       clear the current value for the key \n\
    ')


def note_restart():
    """Instructions how to restart sugar"""
    print _('To apply your changes you have to restart Sugar.\n' +
            'Hit ctrl+alt+erase on the keyboard to trigger a restart.')


def load_modules():
    """Build a list of pointers to available modules and import them.
    """
    modules = []

    path = os.path.join(config.ext_path, 'cpsection')
    folder = os.listdir(path)

    for item in folder:
        if os.path.isdir(os.path.join(path, item)) and \
                os.path.exists(os.path.join(path, item, 'model.py')):
            try:
                module = __import__('.'.join(('cpsection', item, 'model')),
                                    globals(), locals(), ['model'])
            except Exception:
                logging.exception('Exception while loading extension:')
            else:
                modules.append(module)

    return modules


def main():
    try:
        options, args = getopt.getopt(sys.argv[1:], 'h:s:g:c:l', [])
    except getopt.GetoptError:
        cmd_help()
        sys.exit(2)

    if not options:
        cmd_help()
        sys.exit(2)

    modules = load_modules()

    for option, key in options:
        found = 0
        if option in ('-h'):
            for module in modules:
                method = getattr(module, 'set_' + key, None)
                if method:
                    found += 1
                    if found == 1:
                        print method.__doc__
                    else:
                        print _(_same_option_warning % (key, module))
            if found == 0:
                print _(_no_option_error % key)
        if option in ('-l'):
            for module in modules:
                methods = dir(module)
                print '%s:' % module.__name__.split('.')[1]
                for method in methods:
                    if method.startswith('get_'):
                        print '    %s' % method[4:]
                    elif method.startswith('clear_'):
                        print '    %s (use the -c argument with this option)' \
                            % method[6:]
        if option in ('-g'):
            for module in modules:
                method = getattr(module, 'print_' + key, None)
                if method:
                    found += 1
                    if found == 1:
                        try:
                            method()
                        except Exception as detail:
                            print _(_general_error % detail)
                    else:
                        print _(_same_option_warning % (key, module))
            if found == 0:
                print _(_no_option_error % key)
        if option in ('-s'):
            for module in modules:
                method = getattr(module, 'set_' + key, None)
                if method:
                    note = 0
                    found += 1
                    if found == 1:
                        try:
                            note = method(*args)
                        except Exception as detail:
                            print _(_general_error % detail)
                        if note == _RESTART:
                            note_restart()
                    else:
                        print _(_same_option_warning % (key, module))
            if found == 0:
                print _(_no_option_error % key)
        if option in ('-c'):
            for module in modules:
                method = getattr(module, 'clear_' + key, None)
                if method:
                    note = 0
                    found += 1
                    if found == 1:
                        try:
                            note = method(*args)
                        except Exception as detail:
                            print _(_general_error % detail)
                        if note == _RESTART:
                            note_restart()
                    else:
                        print _(_same_option_warning % (key, module))
            if found == 0:
                print _(_no_option_error % key)
