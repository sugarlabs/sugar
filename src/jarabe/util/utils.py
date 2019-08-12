#!/usr/bin/env python
# -*- coding: utf-8 -*-

# utils.py by:
#    Agustin Zubiaga <aguzubiaga97@gmail.com>

# Copyright (C) 2019 Hrishi Patel
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
import os

from sugar3 import profile
from sugar3.graphics.style import Color


def rgb2html(color):
    """Returns a html string from a Gdk color"""
    red = "%x" % int(color.red / 65535.0 * 255)
    if len(red) == 1:
        red = "0%s" % red

    green = "%x" % int(color.green / 65535.0 * 255)

    if len(green) == 1:
        green = "0%s" % green

    blue = "%x" % int(color.blue / 65535.0 * 255)

    if len(blue) == 1:
        blue = "0%s" % blue

    new_color = "#%s%s%s" % (red, green, blue)

    return new_color


def get_user_fill_color(type='gdk'):
    """Returns the user fill color"""
    color = profile.get_color()
    if type == 'gdk':
        rcolor = Color(color.get_fill_color()).get_gdk_color()

    elif type == 'str':
        rcolor = color.get_fill_color()

    return rcolor


def get_user_stroke_color(type='gdk'):
    """Returns the user stroke color"""
    color = profile.get_color()

    if type == 'gdk':
        rcolor = Color(color.get_stroke_color()).get_gdk_color()

    elif type == 'str':
        rcolor = color.get_stroke_color()

    return rcolor


def get_chart_file(activity_dir):
    """Returns a path for write the chart in a png image"""
    chart_file = os.path.join(activity_dir, "chart-1.png")
    num = 0

    while os.path.exists(chart_file):
        num += 1
        chart_file = os.path.join(activity_dir, "chart-" + str(num) + ".png")

    return chart_file


def get_decimals(number):
    """Returns the decimals count of a number"""
    return str(len(number.split('.')[1]))


def get_channels():
    path = os.path.join('/sys/class/dmi/id', 'product_version')
    try:
        product = open(path).readline().strip()
    except:
        product = None

    if product == '1' or product == '1.0':
        return 1
    else:
        return 2
