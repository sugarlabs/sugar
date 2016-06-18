# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2010-14, Sugar Labs
# Copyright (C) 2010-14, Walter Bender
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

from gettext import gettext as _

from gi.repository import Gio

from sugar3 import profile

_COLORS = {
    'red': {'dark': '#b20008', 'medium': '#e6000a', 'light': '#ffadce'},
    'orange': {'dark': '#9a5200', 'medium': '#c97e00', 'light': '#ffc169'},
    'yellow': {'dark': '#807500', 'medium': '#be9e00', 'light': '#fffa00'},
    'green': {'dark': '#008009', 'medium': '#00b20d', 'light': '#8bff7a'},
    'blue': {'dark': '#00588c', 'medium': '#005fe4', 'light': '#bccdff'},
    'purple': {'dark': '#5e008c', 'medium': '#7f00bf', 'light': '#d1a3ff'},
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
        raise ValueError(_('You must enter a name.'))
    if not isinstance(nick, unicode):
        nick = unicode(nick, 'utf-8')
    settings = Gio.Settings('org.sugarlabs.user')
    settings.set_string('nick', nick)

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/user/nick', nick)
    return 1


def get_color():
    settings = Gio.Settings('org.sugarlabs.user')
    return settings.get_string('color')


def print_color():
    color_string = get_color()
    tmp = color_string.split(',')

    stroke_tuple = None
    fill_tuple = None
    for color in _COLORS:
        for hue in _COLORS[color]:
            if _COLORS[color][hue] == tmp[0]:
                stroke_tuple = (color, hue)
            if _COLORS[color][hue] == tmp[1]:
                fill_tuple = (color, hue)

    if stroke_tuple is not None:
        print ('stroke:   color=%s hue=%s') % (stroke_tuple[0],
                                               stroke_tuple[1])
    else:
        print ('stroke:   %s') % (tmp[0])
    if fill_tuple is not None:
        print ('fill:     color=%s hue=%s') % (fill_tuple[0], fill_tuple[1])
    else:
        print ('fill:     %s') % (tmp[1])


def set_color(stroke, fill, stroke_modifier='medium', fill_modifier='medium'):
    """Set the system color by setting a fill and stroke color.
    fill : [red, orange, yellow, blue, green, purple]
    stroke : [red, orange, yellow, blue, green, purple]
    hue stroke : [dark, medium, light] (optional)
    hue fill : [dark, medium, light] (optional)
    """

    if stroke_modifier not in _MODIFIERS or fill_modifier not in _MODIFIERS:
        print (_('Error in specified color modifiers.'))
        return
    if stroke not in _COLORS or fill not in _COLORS:
        print (_('Error in specified colors.'))
        return

    if stroke_modifier == fill_modifier:
        if fill_modifier == 'medium':
            fill_modifier = 'light'
        else:
            fill_modifier = 'medium'

    color = _COLORS[stroke][stroke_modifier] + ',' \
        + _COLORS[fill][fill_modifier]

    settings = Gio.Settings('org.sugarlabs.user')
    settings.set_string('color', color)

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/user/color', color)
    return 1


def get_color_xo():
    settings = Gio.Settings('org.sugarlabs.user')
    return settings.get_string('color')


def set_color_xo(color):
    """Set a color with an XoColor
    This method is used by the graphical user interface
    """
    settings = Gio.Settings('org.sugarlabs.user')
    settings.set_string('color', color)

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/user/color', color)
    return 1
