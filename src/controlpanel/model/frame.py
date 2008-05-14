# Copyright (C) 2008 One Laptop Per Child
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

from gettext import gettext as _

from sugar import profile
        
def get_delay():
    pro = profile.get_profile()    
    return pro.frame_delay

def print_delay():
    print get_delay()
    
def set_delay(value):
    """Set a delay for the revealing of the frame. This can be in the range:
    instantaneous: 0 (0 milliseconds)
    delay: 100 (100 milliseconds) 
    never (disable the hot corners): -1
    """
    try:
        int(value)
    except ValueError:        
        raise ValueError(_("Value must be an integer."))        
    pro = profile.get_profile()
    pro.frame_delay = int(value) 
    pro.save()
    return 'RESTART'
