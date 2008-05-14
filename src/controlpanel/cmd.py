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

import sys
import getopt
import os
from gettext import gettext as _


def cmd_help():
    '''Print the help for to the screen'''
    print _('Usage: sugar-control-panel [ option ] key [ args ... ] \n\
    Control for the sugar environment. \n\
    Options: \n\
    -h           show this help message and exit \n\
    -l           list all the available options \n\
    -h key       show information about this key \n\
    -g key       get the current value of the key \n\
    -s key       set the current value for the key \n\
    ')

def note_restart():
    '''Instructions how to restart sugar'''
    print _('To apply your changes you have to restart sugar.\n' +
            'Hit ctrl+alt+erase on the keyboard to trigger a restart.')

def load_modules(path):    
    '''Build a list of pointers to available modules in the model directory
    and load them.
    '''
    subpath = ['controlpanel', 'model']
    names = os.listdir(os.path.join(path, '/'.join(subpath)))
    
    modules = []
    for name in names:
        if name.endswith('.py') and name != '__init__.py':
            tmp = name.strip('.py')
            mod = __import__('.'.join(subpath) + '.' + 
                             tmp, globals(), locals(), [tmp])
            modules.append(mod)
    return modules        

def main(path):
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:s:g:l", [])
    except getopt.GetoptError:
        cmd_help()
        sys.exit(2)

    if not opts:
        cmd_help()
        sys.exit()

    modules = load_modules(path)

    for opt, key in opts:
        if opt in ("-h"):
            for module in modules:
                method = getattr(module, 'set_' + key, None)
                if method:
                    print method.__doc__                              
                    sys.exit()                    
            print _("sugar-control-panel: key=%s not an available option"
                    % key)                                                    
        if opt in ("-l"):            
            for module in modules:
                methods = dir(module)
                print '%s:' % module.__name__.split('.')[-1]
                for method in methods:
                    if method.startswith('get_'):
                        print '    %s' % method[4:]
        if opt in ("-g"):
            for module in modules:
                method = getattr(module, 'print_' + key, None)
                if method:
                    try:
                        method()
                    except Exception, detail:
                        print _("sugar-control-panel: %s"
                                % detail)                    
                    sys.exit()
            print _("sugar-control-panel: key=%s not an available option"
                    % key)
        if opt in ("-s"):
            for module in modules:
                method = getattr(module, 'set_' + key, None)
                if method:
                    note = 0
                    try:
                        note = method(*args)
                    except Exception, detail:
                        print _("sugar-control-panel: %s"
                                % detail)
                    if note == 'RESTART':
                        note_restart()
                    sys.exit()
            print _("sugar-control-panel: key=%s not an available option"
                    % key)
