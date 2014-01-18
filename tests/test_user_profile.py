# Copyright (C) 2014, Ignacio Rodriguez
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

import random
import string
import unittest

from cpsection.aboutme import model
from jarabe.intro.agepicker import AGES
from jarabe.intro.genderpicker import GENDERS
from sugar3.graphics.xocolor import colors

CHARSET = string.ascii_uppercase + string.digits


class TestUserProfile(unittest.TestCase):
    def setUp(self):
        self.start_age = model.get_age()
        self.start_gender = model.get_gender()
        self.start_nick = model.get_nick()
        self.start_color = model.get_color()

    def test_user_gender_age(self):
        for gender in GENDERS:
            for age in AGES:
                model.set_gender(gender)
                model.set_age(age)
                self.assertEqual(model.get_age(), age)
                self.assertEqual(model.get_gender(), gender)

    def test_user_nick(self):
        for current in range(1, 26):
            new_nick = ''.join(random.sample(CHARSET * current, current))
            model.set_nick(new_nick)
            self.assertEqual(model.get_nick(), new_nick)

    def test_user_color(self):
        for current in range(10):
            new_color = random.choice(colors)
            new_color = "%s,%s" % (new_color[0], new_color[1])
            model.set_color(new_color)
            self.assertEqual(model.get_color(), new_color)

    def tearDown(self):
        if isinstance(self.start_age, int):
            model.set_age(self.start_age)
        if isinstance(self.start_gender, str):
            model.set_gender(self.start_gender)

        if isinstance(self.start_nick, str):
            model.set_nick(self.start_nick)

        if isinstance(self.start_color, str):
            model.set_color(self.start_color)
