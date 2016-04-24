# -*- coding: utf-8 -*-
# Copyright (C) 2014, Ignacio Rodriguez
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

import unittest

from cpsection.aboutme import model
from jarabe.intro.agepicker import AGES
from jarabe.intro.genderpicker import GENDERS

TEST_NICKS = ['Ajay Garg', 'Aleksey Lim',
              'Bernie H. Innocenti', 'Daniel Narvaez',
              'Emil Dudev', 'Gonzalo Odiard',
              'Ignacio Rodríguez', 'Jorge Alberto Gómez López',
              'Sai Vineet', 'Sam Parkinson',
              'Sascha Silbe', 'Walter Bender']

TEST_COLORS = [['#FF8F00', '#FF2B34'],
               ['#00A0FF', '#008009'],
               ['#BCCEFF', '#F8E800'],
               ['#FF2B34', '#7F00BF'],
               ['#FF2B34', '#5E008C'],
               ['#BCCDFF', '#AC32FF'],
               ['#00EA11', '#9A5200'],
               ['#A700FF', '#FF8F00'],
               ['#00EA11', '#7F00BF'],
               ['#8BFF7A', '#F8E800'],
               ['#00A0FF', '#5E008C'],
               ['#7F00BF', '#AC32FF']]


class TestUserProfile(unittest.TestCase):
    def test_user_gender_age(self):
        for gender in GENDERS:
            for age in AGES:
                model.set_gender(gender)
                model.set_age(age)
                self.assertEqual(model.get_age(), age)
                self.assertEqual(model.get_gender(), gender)

    def test_user_nick(self):
        for nick in TEST_NICKS:
            model.set_nick(nick)
            self.assertEqual(model.get_nick(), nick)

    def test_user_color(self):
        for new_color in TEST_COLORS:
            new_color = "%s,%s" % (new_color[0], new_color[1])
            model.set_color_xo(new_color)
            self.assertEqual(model.get_color(), new_color)
