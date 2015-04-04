# Copyright (C) 2011 One Laptop Per Child
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
import logging

from gi.repository import GConf
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject


DEFAULT_PITCH = 0


DEFAULT_RATE = 0

_speech_manager = None


class SpeechManager(GObject.GObject):

    __gtype_name__ = 'SpeechManager'

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, [])
    }

    MIN_PITCH = -100
    MAX_PITCH = 100

    MIN_RATE = -100
    MAX_RATE = 100

    def __init__(self, **kwargs):
        GObject.GObject.__init__(self, **kwargs)
        self._player = _GstSpeechPlayer()
        self._player.connect('play', self._update_state, 'play')
        self._player.connect('stop', self._update_state, 'stop')
        self._player.connect('pause', self._update_state, 'pause')
        self._voice_name = self._player.get_default_voice()
        self._pitch = DEFAULT_PITCH
        self._rate = DEFAULT_RATE
        self._is_playing = False
        self._is_paused = False
        self.restore()

    def _update_state(self, player, signal):
        self._is_playing = (signal == 'play')
        self._is_paused = (signal == 'pause')
        self.emit(signal)

    def get_is_playing(self):
        return self._is_playing

    is_playing = GObject.property(type=bool, getter=get_is_playing,
                                  setter=None, default=False)

    def get_is_paused(self):
        return self._is_paused

    is_paused = GObject.property(type=bool, getter=get_is_paused,
                                 setter=None, default=False)

    def get_pitch(self):
        return self._pitch

    def get_rate(self):
        return self._rate

    def set_pitch(self, pitch):
        self._pitch = pitch
        self.save()

    def set_rate(self, rate):
        self._rate = rate
        self.save()

    def say_text(self, text):
        if text:
            self._player.speak(self._pitch, self._rate, self._voice_name, text)

    def say_selected_text(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        clipboard.request_text(self.__primary_selection_cb, None)

    def pause(self):
        self._player.pause_sound_device()

    def restart(self):
        self._player.restart_sound_device()

    def stop(self):
        self._player.stop_sound_device()

    def __primary_selection_cb(self, clipboard, text, user_data):
        self.say_text(text)

    def save(self):
        client = GConf.Client.get_default()
        client.set_int('/desktop/sugar/speech/pitch', self._pitch)
        client.set_int('/desktop/sugar/speech/rate', self._rate)
        logging.debug('saving speech configuration pitch %s rate %s',
                      self._pitch, self._rate)

    def restore(self):
        client = GConf.Client.get_default()
        self._pitch = client.get_int('/desktop/sugar/speech/pitch')
        self._rate = client.get_int('/desktop/sugar/speech/rate')
        logging.debug('loading speech configuration pitch %s rate %s',
                      self._pitch, self._rate)


class _GstSpeechPlayer(GObject.GObject):

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, [])
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self._pipeline = None

    def restart_sound_device(self):
        if self._pipeline is None:
            logging.debug('Trying to restart not initialized sound device')
            return

        self._pipeline.set_state(Gst.State.PLAYING)
        self.emit('play')

    def pause_sound_device(self):
        if self._pipeline is None:
            return

        self._pipeline.set_state(Gst.State.PAUSED)
        self.emit('pause')

    def stop_sound_device(self):
        if self._pipeline is None:
            return

        self._pipeline.set_state(Gst.State.NULL)
        self.emit('stop')

    def make_pipeline(self, command):
        if self._pipeline is not None:
            self.stop_sound_device()
            del self._pipeline

        self._pipeline = Gst.parse_launch(command)

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.__pipe_message_cb)

    def __pipe_message_cb(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self._pipeline.set_state(Gst.State.NULL)
            self.emit('stop')
        elif message.type == Gst.MessageType.ERROR:
            self._pipeline.set_state(Gst.State.NULL)
            self.emit('stop')

    def speak(self, pitch, rate, voice_name, text):
        # TODO workaround for http://bugs.sugarlabs.org/ticket/1801
        if not [i for i in text if i.isalnum()]:
            return

        self.make_pipeline('espeak name=espeak ! autoaudiosink')
        src = self._pipeline.get_by_name('espeak')

        src.props.text = text
        src.props.pitch = pitch
        src.props.rate = rate
        src.props.voice = voice_name
        src.props.track = 2  # track for marks

        self.restart_sound_device()

    def get_all_voices(self):
        all_voices = {}
        for voice in Gst.ElementFactory.make('espeak', None).props.voices:
            name, language, dialect = voice
            if dialect != 'none':
                all_voices[language + '_' + dialect] = name
            else:
                all_voices[language] = name
        return all_voices

    def get_default_voice(self):
        """Try to figure out the default voice, from the current locale ($LANG)
           Fall back to espeak's voice called Default."""
        voices = self.get_all_voices()

        locale = os.environ.get('LANG', '')
        language_location = locale.split('.', 1)[0].lower()
        language = language_location.split('_')[0]
        # if the language is es but not es_es default to es_la (latin voice)
        if language == 'es' and language_location != 'es_es':
            language_location = 'es_la'

        best = voices.get(language_location) or voices.get(language) \
            or 'default'
        logging.debug('Best voice for LANG %s seems to be %s',
                      locale, best)
        return best


def get_speech_manager():
    global _speech_manager

    if _speech_manager is None:
        _speech_manager = SpeechManager()
    return _speech_manager
