# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
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

from jarabe.view.viewsource import setup_view_source
from jarabe.model import shell


BOUND_KEYS = ['XF86KbdLightOnOff', '<alt><shift>v']


def handle_key_press(key):
    shell_model = shell.get_model()
    activity = shell_model.get_active_activity()

    setup_view_source(activity)
