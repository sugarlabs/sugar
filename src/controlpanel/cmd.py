# Copyright (C) 2007, One Laptop Per Child
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
from gettext import gettext as _

from controlpanel import control
        
def cmd_help():
    print _('Usage: sugar-control-panel [ option ] key [ args ... ] \n\
    Control for the sugar environment. \n\
    Options: \n\
    -h           show this help message and exit \n\
    -l           list all the available options \n\
    -h key       show information about this key \n\
    -g key       get the current value of the key \n\
    -s key       set the current value for the key \n\
    ')

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:s:g:l", [])
    except getopt.GetoptError:
        cmd_help()
        sys.exit(2)

    if not opts:
        cmd_help()
        sys.exit()
        
    for opt, key in opts:
        if opt in ("-h"):            
            method = getattr(control, 'set_' + key, None)
            if method is None:
                print _("sugar-control-panel: key=%s not an available option" 
                        % key)
                sys.exit()
            else:    
                print method.__doc__
        if opt in ("-l"):
            elems = dir(control)
            for elem in elems:
                if elem.startswith('set_'):
                    print elem[4:]
        if opt in ("-g"):
            method = getattr(control, 'print_' + key, None)
            if method is None:
                print _("sugar-control-panel: key=%s not an available option" 
                        % key)
                sys.exit()
            else:    
                method()
        if opt in ("-s"):
            method = getattr(control, 'set_' + key, None)
            if method is None:
                print _("sugar-control-panel: key=%s not an available option"
                        % key)
                sys.exit()
            else:
                try:
                    method(*args)
                except Exception, e:
                    print _("sugar-control-panel: %s"% e)
