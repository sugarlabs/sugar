import os
import logging
from gettext import gettext as _

import gi

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

_HAS_GST = True
try:
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    Gst.parse_launch('espeak')
except Exception as e:
    logging.error('Gst or the espeak plugin is not installed in the system: %s', e)
    _HAS_GST = False

try:
    from sugar4 import power
    _power_manager = power.get_power_manager()
except (ImportError, AttributeError):
    _power_manager = None

DEFAULT_PITCH = 0
DEFAULT_RATE = 0
_SAVE_TIMEOUT = 500

SPEECH_SCHEMA = 'org.sugarlabs.speech'

translated_espeak_voices = {
    'af': _('Afrikaans'),
    'an': _('Aragonese'),
    'bg': _('Bulgarian'),
    'bs': _('Bosnian'),
    'ca': _('Catalan'),
    'cs': _('Czech'),
    'cy': _('Welsh'),
    'da': _('Danish'),
    'de': _('German'),
    'el': _('Greek'),
    'en': _('English'),
    'en_gb': _('English Britain'),
    'en_sc': _('English scottish'),
    'en_uk-north': _('English-north'),
    'en_uk-rp': _('English_rp'),
    'en_uk-wmids': _('English_wmids'),
    'en_us': _('English USA'),
    'en_wi': _('English West Indies'),
    'eo': _('Esperanto'),
    'es': _('Spanish'),
    'es_la': _('Spanish latin american'),
    'et': _('Estonian'),
    'fa': _('Farsi'),
    'fa_pin': _('Farsi-pinglish'),
    'fi': _('Finnish'),
    'fr_be': _('French belgium'),
    'fr_fr': _('French'),
    'ga': _('Irish-gaeilge'),
    'grc': _('Greek-ancient'),
    'hi': _('Hindi'),
    'hr': _('Croatian'),
    'hu': _('Hungarian'),
    'hy': _('Armenian'),
    'hy_west': _('Armenian (west)'),
    'id': _('Indonesian'),
    'is': _('Icelandic'),
    'it': _('Italian'),
    'jbo': _('Lojban'),
    'ka': _('Georgian'),
    'kn': _('Kannada'),
    'ku': _('Kurdish'),
    'la': _('Latin'),
    'lt': _('Lithuanian'),
    'lv': _('Latvian'),
    'mk': _('Macedonian'),
    'ml': _('Malayalam'),
    'ms': _('Malay'),
    'ne': _('Nepali'),
    'nl': _('Dutch'),
    'no': _('Norwegian'),
    'pa': _('Punjabi'),
    'pl': _('Polish'),
    'pt_br': _('Portuguese (Brazil)'),
    'pt_pt': _('Portuguese (Portugal)'),
    'ro': _('Romanian'),
    'ru': _('Russian'),
    'sk': _('Slovak'),
    'sq': _('Albanian'),
    'sr': _('Serbian'),
    'sv': _('Swedish'),
    'sw': _('Swahili'),
    'ta': _('Tamil'),
    'tr': _('Turkish'),
    'vi': _('Vietnam'),
    'vi_hue': _('Vietnam_hue'),
    'vi_sgn': _('Vietnam_sgn'),
    'zh': _('Mandarin'),
    'zh_yue': _('Cantonese')
}


class SpeechManager(GObject.GObject):

    __gtype_name__ = 'SpeechManager'

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, []),
        'mark': (GObject.SignalFlags.RUN_FIRST, None, [str])
    }

    MIN_PITCH = -100
    MAX_PITCH = 100

    MIN_RATE = -100
    MAX_RATE = 100

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player = None
        if not self.enabled():
            return

        self.player = GstSpeechPlayer()
        self.player.connect('play', self._update_state, 'play')
        self.player.connect('stop', self._update_state, 'stop')
        self.player.connect('pause', self._update_state, 'pause')
        self.player.connect('mark', self._mark_cb)
        self._default_voice_name = self.player.get_default_voice()
        self._pitch = DEFAULT_PITCH
        self._rate = DEFAULT_RATE
        self._is_playing = False
        self._is_paused = False
        self._save_timeout_id = -1
        self.restore()

    def enabled(self):
        return _HAS_GST

    def _update_state(self, player, signal):
        self._is_playing = (signal == 'play')
        self._is_paused = (signal == 'pause')
        self.emit(signal)

    def _mark_cb(self, player, value):
        self.emit('mark', value)

    def get_is_playing(self):
        return self._is_playing

    is_playing = GObject.Property(type=bool, getter=get_is_playing,
                                  setter=None, default=False)

    def get_is_paused(self):
        return self._is_paused

    is_paused = GObject.Property(type=bool, getter=get_is_paused,
                                 setter=None, default=False)

    def get_pitch(self):
        return self._pitch

    def get_rate(self):
        return self._rate

    def set_pitch(self, pitch):
        self._pitch = pitch
        if self._save_timeout_id != -1:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(_SAVE_TIMEOUT, self.save)

    def set_rate(self, rate):
        self._rate = rate
        if self._save_timeout_id != -1:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(_SAVE_TIMEOUT, self.save)

    def say_text(self, text, pitch=None, rate=None, lang_code=None):
        if pitch is None:
            pitch = self._pitch
        if rate is None:
            rate = self._rate
        if lang_code is None:
            voice_name = self._default_voice_name
        else:
            voice_name = self.player.get_all_voices()[lang_code]
        if text:
            logging.debug(
                'PLAYING %r lang %r pitch %r rate %r',
                text,
                voice_name,
                pitch,
                rate)
            self.player.speak(pitch, rate, voice_name, text)

    def say_selected_text(self):
        display = Gdk.Display.get_default()
        if display:
            clipboard = display.get_primary_clipboard()
            clipboard.read_text_async(None, self.__primary_selection_cb)

    def pause(self):
        self.player.pause_sound_device()

    def restart(self):
        self.player.restart_sound_device()

    def stop(self):
        self.player.stop_sound_device()

    def __primary_selection_cb(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self.say_text(text)
        except GLib.Error as e:
            logging.error("Failed to read primary clipboard text: %s", e)

    def save(self):
        self._save_timeout_id = -1

        schema_source = Gio.SettingsSchemaSource.get_default()
        if schema_source.lookup(SPEECH_SCHEMA, True) is None:
            return False

        settings = Gio.Settings(SPEECH_SCHEMA)
        settings.set_int('pitch', self._pitch)
        settings.set_int('rate', self._rate)
        logging.debug('saving speech configuration pitch %s rate %s',
                      self._pitch, self._rate)
        return False

    def restore(self):
        schema_source = Gio.SettingsSchemaSource.get_default()
        if schema_source.lookup(SPEECH_SCHEMA, True) is None:
            return

        settings = Gio.Settings(SPEECH_SCHEMA)
        self._pitch = settings.get_int('pitch')
        self._rate = settings.get_int('rate')
        logging.debug('loading speech configuration pitch %s rate %s',
                      self._pitch, self._rate)

    def get_all_voices(self):
        if self.player:
            return self.player.get_all_voices()
        return None

    def get_all_traslated_voices(self):
        """ deprecated after 0.112, due to method name spelling error """
        if self.player:
            return self.player.get_all_translated_voices()
        return None

    def get_all_translated_voices(self):
        if self.player:
            return self.player.get_all_translated_voices()
        return None


class GstSpeechPlayer(GObject.GObject):

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, []),
        'mark': (GObject.SignalFlags.RUN_FIRST, None, [str])
    }

    def __init__(self):
        super().__init__()
        self.pipeline = None
        self._all_voices = None
        self._all_translated_voices = None

    def restart_sound_device(self):
        if self.pipeline is None:
            logging.debug('Trying to restart not initialized sound device')
            return

        if _power_manager:
            _power_manager.inhibit_suspend()
        self.pipeline.set_state(Gst.State.PLAYING)
        self.emit('play')

    def pause_sound_device(self):
        if self.pipeline is None:
            return

        self.pipeline.set_state(Gst.State.PAUSED)
        if _power_manager:
            _power_manager.restore_suspend()
        self.emit('pause')

    def stop_sound_device(self):
        if self.pipeline is None:
            return

        self.pipeline.set_state(Gst.State.NULL)
        if _power_manager:
            _power_manager.restore_suspend()
        self.emit('stop')

    def make_pipeline(self, command):
        if self.pipeline is not None:
            self.stop_sound_device()
            del self.pipeline

        self.pipeline = Gst.parse_launch(command)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.__pipe_message_cb)

    def __pipe_message_cb(self, bus, message):
        if message.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            if _power_manager:
                _power_manager.restore_suspend()
            self.emit('stop')
        elif message.type is Gst.MessageType.ELEMENT and \
                message.get_structure().get_name() == 'espeak-mark':
            mark_value = message.get_structure().get_value('mark')
            self.emit('mark', mark_value)

    def speak(self, pitch, rate, voice_name, text):
        # TODO workaround for http://bugs.sugarlabs.org/ticket/1801
        if not [i for i in text if i.isalnum()]:
            return

        self.make_pipeline('espeak name=espeak ! autoaudiosink')
        src = self.pipeline.get_by_name('espeak')

        src.props.text = text
        src.props.pitch = pitch
        src.props.rate = rate
        src.props.voice = voice_name
        src.props.track = 2  # track for marks

        self.restart_sound_device()

    def get_all_voices(self):
        if self._all_voices is not None:
            return self._all_voices
        self._init_voices()
        return self._all_voices

    def get_all_translated_voices(self):
        if self._all_translated_voices is not None:
            return self._all_translated_voices
        self._init_voices()
        return self._all_translated_voices

    def _init_voices(self):
        self._all_voices = {}
        self._all_translated_voices = {}

        for voice in Gst.ElementFactory.make('espeak', None).props.voices:
            name, language, dialect = voice
            if dialect != 'none':
                lang_code = language + '_' + dialect
            else:
                lang_code = language

            self._all_voices[lang_code] = name
            if lang_code in translated_espeak_voices:
                self._all_translated_voices[lang_code] = \
                    translated_espeak_voices[lang_code]
            else:
                self._all_translated_voices[lang_code] = name

    def get_default_voice(self):
        voices = self.get_all_voices()

        locale = os.environ.get('LANG', '')
        language_location = locale.split('.', 1)[0].lower()
        language = language_location.split('_')[0]
        # if the language is es but not es_es default to es_la (latin voice)
        if language == 'es' and language_location != 'es_es':
            language_location = 'es_la'

        best = voices.get(language_location) or voices.get(language) \
            or 'english'
        return best

_speech_manager = None


def get_speech_manager():
    global _speech_manager

    if _speech_manager is None:
        _speech_manager = SpeechManager()
        if not _speech_manager.enabled():
            _speech_manager = None
    return _speech_manager
