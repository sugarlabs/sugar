# Copyright(c) 2007-2010 by Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#              2009 by Yaco S.L. <lgs@yaco.es>
#
# This file is part of PyCha.
#
# PyCha is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyCha is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyCha.  If not, see <http://www.gnu.org/licenses/>.

import math

from jarabe.util.sugarpycha.utils import clamp


DEFAULT_COLOR = '#3c581a'


def hex2rgb(hexstring, digits=2):
    """Converts a hexstring color to a rgb tuple.

    Example: #ff0000 -> (1.0, 0.0, 0.0)

    digits is an integer number telling how many characters should be
    interpreted for each component in the hexstring.
    """
    if isinstance(hexstring, (tuple, list)):
        return hexstring

    top = float(int(digits * 'f', 16))
    r = int(hexstring[1:digits + 1], 16)
    g = int(hexstring[digits + 1:digits * 2 + 1], 16)
    b = int(hexstring[digits * 2 + 1:digits * 3 + 1], 16)
    return r / top, g / top, b / top


def rgb2hsv(r, g, b):
    """Converts a RGB color into a HSV one

    See http://en.wikipedia.org/wiki/HSV_color_space
    """
    maximum = max(r, g, b)
    minimum = min(r, g, b)
    if maximum == minimum:
        h = 0.0
    elif maximum == r:
        h = 60.0 * ((g - b) / (maximum - minimum)) + 360.0
        if h >= 360.0:
            h -= 360.0
    elif maximum == g:
        h = 60.0 * ((b - r) / (maximum - minimum)) + 120.0
    elif maximum == b:
        h = 60.0 * ((r - g) / (maximum - minimum)) + 240.0

    if maximum == 0.0:
        s = 0.0
    else:
        s = 1.0 - (minimum / maximum)

    v = maximum

    return h, s, v


def hsv2rgb(h, s, v):
    """Converts a HSV color into a RGB one

    See http://en.wikipedia.org/wiki/HSV_color_space
    """
    hi = int(math.floor(h / 60.0)) % 6
    f = (h / 60.0) - hi
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)

    if hi == 0:
        r, g, b = v, t, p
    elif hi == 1:
        r, g, b = q, v, p
    elif hi == 2:
        r, g, b = p, v, t
    elif hi == 3:
        r, g, b = p, q, v
    elif hi == 4:
        r, g, b = t, p, v
    elif hi == 5:
        r, g, b = v, p, q

    return r, g, b


def lighten(r, g, b, amount):
    """Return a lighter version of the color (r, g, b)"""
    return (clamp(0.0, 1.0, r + amount),
            clamp(0.0, 1.0, g + amount),
            clamp(0.0, 1.0, b + amount))


basicColors = dict(
    red='#6d1d1d',
    green=DEFAULT_COLOR,
    blue='#224565',
    grey='#444444',
    black='#000000',
    darkcyan='#305755',
    )


class ColorSchemeMetaclass(type):
    """This metaclass is used to autoregister all ColorScheme classes"""

    def __new__(mcs, name, bases, dict):
        klass = type.__new__(mcs, name, bases, dict)
        klass.registerColorScheme()
        return klass


class ColorScheme(dict):
    """A color scheme is a dictionary where the keys match the keys
    constructor argument and the values are colors"""
    __metaclass__ = ColorSchemeMetaclass
    __registry__ = {}

    def __init__(self, keys):
        super(ColorScheme, self).__init__()

    @classmethod
    def registerColorScheme(cls):
        key = cls.__name__.replace('ColorScheme', '').lower()
        if key:
            cls.__registry__[key] = cls

    @classmethod
    def getColorScheme(cls, name, default=None):
        return cls.__registry__.get(name, default)


class GradientColorScheme(ColorScheme):
    """In this color scheme each color is a lighter version of initialColor.

    This difference is computed based on the number of keys.

    The initialColor is given in a hex string format.
    """

    def __init__(self, keys, initialColor=DEFAULT_COLOR):
        super(GradientColorScheme, self).__init__(keys)
        if initialColor in basicColors:
            initialColor = basicColors[initialColor]

        r, g, b = hex2rgb(initialColor)
        light = 1.0 / (len(keys) * 2)

        for i, key in enumerate(keys):
            self[key] = lighten(r, g, b, light * i)


class FixedColorScheme(ColorScheme):
    """In this color scheme fixed colors are used.

    These colors are provided as a list argument in the constructor.
    """

    def __init__(self, keys, colors=[]):
        super(FixedColorScheme, self).__init__(keys)

        if len(keys) != len(colors):
            raise ValueError("You must provide as many colors as datasets "
                             "for the fixed color scheme")

        for i, key in enumerate(keys):
            self[key] = hex2rgb(colors[i])


class RainbowColorScheme(ColorScheme):
    """In this color scheme the rainbow is divided in N pieces
    where N is the number of datasets.

    So each dataset gets a color of the rainbow.
    """

    def __init__(self, keys, initialColor=DEFAULT_COLOR):
        super(RainbowColorScheme, self).__init__(keys)
        if initialColor in basicColors:
            initialColor = basicColors[initialColor]

        r, g, b = hex2rgb(initialColor)
        h, s, v = rgb2hsv(r, g, b)

        angleDelta = 360.0 / (len(keys) + 1)
        for key in keys:
            self[key] = hsv2rgb(h, s, v)
            h += angleDelta
            if h >= 360.0:
                h -= 360.0
