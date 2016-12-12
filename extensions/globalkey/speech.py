# Copyright (C) 2011 One Laptop Per Child
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

from jarabe.model import speech

BOUND_KEYS = ['<alt><shift>s']


def handle_key_press(key):
    manager = speech.get_speech_manager()
    if manager is None:
        return

    if manager.is_paused:
        manager.restart()
    elif not manager.is_playing:
        manager.say_selected_text()
    else:
        manager.pause()
