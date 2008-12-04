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
        
def get_corner_delay():
    pro = profile.get_profile()    
    return pro.hot_corners_delay

def print_corner_delay():
    print get_corner_delay()
    
def set_corner_delay(delay):
    """Set a delay for the activation of the frame using hot corners.
    instantaneous: 0 (0 milliseconds)
    delay: 100 (100 milliseconds) 
    never: 1000 (disable activation)
    """
    try:
        int(delay)
    except ValueError:        
        raise ValueError(_("Value must be an integer."))        
    pro = profile.get_profile()
    pro.hot_corners_delay = int(delay) 
    pro.save()
    return 1
        
def get_edge_delay():
    pro = profile.get_profile()    
    return pro.warm_edges_delay

def print_edge_delay():
    print get_edge_delay()
    
def set_edge_delay(delay):
    """Set a delay for the activation of the frame using warm edges. 
    instantaneous: 0 (0 milliseconds)
    delay: 100 (100 milliseconds) 
    never: 1000 (disable activation)
    """
    try:
        int(delay)
    except ValueError:        
        raise ValueError(_("Value must be an integer."))        
    pro = profile.get_profile()
    pro.warm_edges_delay = int(delay) 
    pro.save()
    return 1
