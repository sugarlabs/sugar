# Copyright (C) 2013 Kalpa Welivitigoda
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

from jarabe.view.viewhelp import setup_view_help
from jarabe.model import shell

BOUND_KEYS = ['<alt><shift>h']


def handle_key_press(key):
    shell_model = shell.get_model()
    activity = shell_model.get_active_activity()

    setup_view_help(activity)
