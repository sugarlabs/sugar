# Copyright (C) 2006, Red Hat, Inc.
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

import os
from ConfigParser import ConfigParser

from sugar import env
from sugar.graphics.iconcolor import IconColor

def get_nick_name():
	return _nick_name

def get_color():
	return _color

cp = ConfigParser()
config_path = os.path.join(env.get_profile_path(), 'config')
parsed = cp.read([config_path])

if cp.has_option('Buddy', 'NickName'):
	_nick_name = cp.get('Buddy', 'NickName')
else:
	_nick_name = None

if cp.has_option('Buddy', 'Color'):
	_color = IconColor(cp.get('Buddy', 'Color'))
else:
	_color = None

del cp
