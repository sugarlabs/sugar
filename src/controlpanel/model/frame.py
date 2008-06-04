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
        
def get_hot_corners_delay():
    pro = profile.get_profile()    
    return pro.hot_corners_delay

def print_hot_corners_delay():
    print get_hot_corners_delay()
    
def set_hot_corners_delay(delay):
    """Set a delay for the revealing of the frame using hot corners.
    instantaneous: 0 (0 milliseconds)
    delay: 100 (100 milliseconds) 
    never: 1000 (disable activation)
    """
    try:
        int(delay)
    except ValueError:        
        raise ValueError(_("Value must be an int."))        
    pro = profile.get_profile()
    pro.hot_corners_delay = int(delay) 
    pro.save()
    return 1
        
def get_warm_edges_delay():
    pro = profile.get_profile()    
    return pro.warm_edges_delay

def print_warm_edges_delay():
    print get_warm_edges_delay()
    
def set_warm_edges_delay(delay):
    """Set a delay for the revealing of the frame using warm edges. 
    instantaneous: 0 (0 milliseconds)
    delay: 100 (100 milliseconds) 
    never: 1000 (disable activation)
    """
    try:
        int(delay)
    except ValueError:        
        raise ValueError(_("Value must be an int."))        
    pro = profile.get_profile()
    pro.warm_edges_delay = int(delay) 
    pro.save()
    return 1
