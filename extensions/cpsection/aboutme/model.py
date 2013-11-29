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

from gi.repository import GConf

from jarabe.intro.window import calculate_birth_timestamp, calculate_age
from jarabe.intro.agepicker import AGES


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
    client = GConf.Client.get_default()
    return client.get_string('/desktop/sugar/user/nick')


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
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/user/nick', nick)
    return 1


def get_gender():
    client = GConf.Client.get_default()
    return client.get_string('/desktop/sugar/user/gender')


def print_gender():
    print get_gender()


def set_gender(gender):
    """Set the gender.
    gender : e.g. 'female'
    """
    if not gender or not gender in ['male', 'female']:
        raise ValueError(_('Gender must be male or female.'))
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/user/gender', gender)
    return 1


def get_age():
    client = GConf.Client.get_default()
    age = client.get_int('/desktop/sugar/user/age')
    birth_timestamp = client.get_int('/desktop/sugar/user/birth_timestamp')

    if birth_timestamp == 0:
        if age in AGES:
            return age
        else:
            return None

    birth_age = calculate_age(birth_timestamp)

    age = (AGES[-2] + AGES[-1]) / 2
    if birth_age >= age:
        return AGES[-1]
    
    for i in range(len(AGES) - 1):
        age = (AGES[i] + AGES[i + 1]) / 2
        if birth_age < age:
            return AGES[i]

    age = client.get_int('/desktop/sugar/user/age')
    return None


def print_age():
    print get_age()


def set_age(age):
    """Set the age and an approximate birth timestamp
    age: e.g. 8
    birth_timestamp: time - age * #seconds per year
    """
    try:
        i = int(age)
    except ValueError, e:
        i = None

    if i is None or i < 1:
        raise ValueError(_('Age must be a positive integer.'))

    client = GConf.Client.get_default()
    client.set_int('/desktop/sugar/user/age', age)
    client.set_int('/desktop/sugar/user/birth_timestamp',
                   calculate_birth_timestamp(age))
    return 1


def get_color():
    client = GConf.Client.get_default()
    return client.get_string('/desktop/sugar/user/color')


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
        print _('stroke:   color=%s hue=%s') % (stroke_tuple[0],
                                                stroke_tuple[1])
    else:
        print _('stroke:   %s') % (tmp[0])
    if fill_tuple is not None:
        print _('fill:     color=%s hue=%s') % (fill_tuple[0], fill_tuple[1])
    else:
        print _('fill:     %s') % (tmp[1])


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

    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/user/color', color)
    return 1


def get_color_xo():
    client = GConf.Client.get_default()
    return client.get_string('/desktop/sugar/user/color')


def set_color_xo(color):
    """Set a color with an XoColor
    This method is used by the graphical user interface
    """
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/user/color', color)
    return 1
