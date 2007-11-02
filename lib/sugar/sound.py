# Copyright (C) 2007 One Laptop Per Child
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging

import gst

class Player(object):
    def __init__(self):
        self._player = gst.element_factory_make("playbin", "player")

        bus = self._player.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.__eos_cb)
        bus.connect("message::error", self.__error_cb)

    def play(self, sound_path):
        self._player.set_property("uri", "file://" + sound_path)
        self._player.set_state(gst.STATE_PLAYING)

    def __eos_cb(self, bus, message):
        self._player.set_state(gst.STATE_NULL)

    def __error_cb(self, bus, message):
        logging.error(message.parse_error())

_player = Player()

def play(sound_path):
    _player.play(sound_path)
