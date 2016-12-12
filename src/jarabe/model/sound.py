# Copyright (C) 2006-2008 Red Hat, Inc.
# Copyright (C) 2014 Emil Dudev
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

from gi.repository import Gio
from gi.repository import GObject

from gi.repository import SugarExt
from sugar3 import dispatch


_PLAYBACK = 0
_CAPTURE = 1


_SAVE_TIMEOUT = 500


class PlaybackSound(object):
    _volume = SugarExt.VolumeAlsa.new(_PLAYBACK)

    muted_changed = dispatch.Signal()
    volume_changed = dispatch.Signal()

    VOLUME_STEP = 10

    def __init__(self):
        self._save_timeout_id = -1

    def get_muted(self):
        return self._volume.get_mute()

    def get_volume(self):
        return self._volume.get_volume()

    def set_volume(self, new_volume):
        self._volume.set_volume(new_volume)
        self.volume_changed.send(None)
        if self._save_timeout_id != -1:
            GObject.source_remove(self._save_timeout_id)
        self._save_timeout_id = GObject.timeout_add(_SAVE_TIMEOUT, self.save)

    def set_muted(self, new_state):
        self._volume.set_mute(new_state)
        self.muted_changed.send(None)
        if self._save_timeout_id != -1:
            GObject.source_remove(self._save_timeout_id)
        self._save_timeout_id = GObject.timeout_add(_SAVE_TIMEOUT, self.save)

    def save(self):
        self._save_timeout_id = -1
        settings = Gio.Settings('org.sugarlabs.sound')
        settings.set_int('volume', self.get_volume())
        return False

    def restore(self):
        settings = Gio.Settings('org.sugarlabs.sound')
        self.set_volume(settings.get_int('volume'))


class CaptureSound(object):
    _volume = SugarExt.VolumeAlsa.new(_CAPTURE)

    muted_changed = dispatch.Signal()
    volume_changed = dispatch.Signal()

    def get_muted(self):
        return self._volume.get_mute()

    def get_volume(self):
        return self._volume.get_volume()

    def set_volume(self, new_volume):
        self._volume.set_volume(new_volume)

        self.volume_changed.send(None)

    def set_muted(self, new_state):
        self._volume.set_mute(new_state)
        self.muted_changed.send(None)


sound = PlaybackSound()
capture_sound = CaptureSound()
