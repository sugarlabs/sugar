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
from sugar.graphics.xocolor import XoColor

_COLORS = {'red': {'dark':'#b20008', 'medium':'#e6000a', 'light':'#ffadce'},
           'orange': {'dark':'#9a5200', 'medium':'#c97e00', 'light':'#ffc169'},
           'yellow': {'dark':'#807500', 'medium':'#be9e00', 'light':'#fffa00'},
           'green': {'dark':'#008009', 'medium':'#00b20d', 'light':'#8bff7a'},
           'blue': {'dark':'#00588c', 'medium':'#005fe4', 'light':'#bccdff'},
           'purple': {'dark':'#5e008c', 'medium':'#7f00bf', 'light':'#d1a3ff'}
           }

_MODIFIERS = ('dark', 'medium', 'light')
        
def get_nick():
    return profile.get_nick_name()

def print_nick():
    print get_nick()
    
def set_nick(nick):
    """Set the nickname.
    nick : e.g. 'walter'
    """
    if not nick:
        raise ValueError(_("You must enter a name."))
    pro = profile.get_profile()
    pro.nick_name = nick    
    pro.save()
    return 'RESTART'

def get_color():    
    return profile.get_color()    

def print_color():
    color = get_color().to_string()
    tmp = color.split(',')

    stroke = None
    fill = None
    for color in _COLORS:
        for hue in _COLORS[color]:
            if _COLORS[color][hue] == tmp[0]:
                stroke = (color, hue)
            if _COLORS[color][hue] == tmp[1]:
                fill = (color, hue)

    if stroke is not None:            
        print 'stroke:   color=%s hue=%s' % (stroke[0], stroke[1])
    else:
        print 'stroke:   %s' % (tmp[0])        
    if fill is not None:    
        print 'fill:     color=%s hue=%s' % (fill[0], fill[1])
    else:
        print 'fill:     %s' % (tmp[1])
        
def set_color(stroke, fill, modstroke='medium', modfill='medium'):
    """Set the system color by setting a fill and stroke color.
    fill : [red, orange, yellow, blue, green, purple]
    stroke : [red, orange, yellow, blue, green, purple]
    hue stroke : [dark, medium, light] (optional)
    hue fill : [dark, medium, light] (optional)
    """
    
    if modstroke not in _MODIFIERS or modfill not in _MODIFIERS:
        print (_("Error in specified color modifiers."))
        return
    if stroke not in _COLORS or fill not in _COLORS:
        print (_("Error in specified colors."))
        return
    
    if modstroke == modfill:
        if modfill == 'medium':
            modfill = 'light'
        else:
            modfill = 'medium'
            
    color = _COLORS[stroke][modstroke] + ',' + _COLORS[fill][modfill]
    pro = profile.get_profile()
    pro.color = XoColor(color)   
    pro.save()
    return "RESTART"

def set_color_xo(color):
    """Set a color with an XoColor
    """
    pro = profile.get_profile()
    pro.color = color
    pro.save()
    return "RESTART"
