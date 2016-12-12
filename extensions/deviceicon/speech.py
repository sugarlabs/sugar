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

from gettext import gettext as _

from gi.repository import Gtk

from sugar3 import profile
from sugar3.graphics.icon import Icon
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import speech


_ICON_NAME = 'microphone'


class SpeechDeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 150

    def __init__(self):
        self._color = profile.get_color()
        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True

        self._manager = speech.get_speech_manager()

    def create_palette(self):
        palette = SpeechPalette(_('Speech'), manager=self._manager)
        palette.set_group_id('frame')
        return palette


class SpeechPalette(Palette):

    def __init__(self, primary_text, manager):
        Palette.__init__(self, label=primary_text)

        self._manager = manager
        self._manager.connect('play', self._set_menu_state, 'play')
        self._manager.connect('stop', self._set_menu_state, 'stop')
        self._manager.connect('pause', self._set_menu_state, 'pause')

        box = PaletteMenuBox()
        self.set_content(box)
        box.show()

        self._play_icon = Icon(icon_name='player_play')
        self._pause_icon = Icon(icon_name='player_pause')
        self._play_pause_menu = PaletteMenuItem(
            icon_name='player_play',
            text_label=_('Say selected text'),
            accelerator='Shift+Alt+S')
        self._play_pause_menu.set_image(self._play_icon)
        self._play_pause_menu.connect('activate', self.__play_activated_cb)
        box.append_item(self._play_pause_menu)
        self._play_pause_menu.show()

        self._stop_menu = PaletteMenuItem(icon_name='player_stop',
                                          text_label=_('Stop playback'))
        self._stop_menu.connect('activate', self.__stop_activated_cb)
        self._stop_menu.set_sensitive(False)
        box.append_item(self._stop_menu)

        separator = PaletteMenuItemSeparator()
        box.append_item(separator)
        separator.show()

        pitch_label = Gtk.Label(_('Pitch'))
        box.append_item(pitch_label, vertical_padding=0)
        pitch_label.show()

        self._adj_pitch = Gtk.Adjustment(value=self._manager.get_pitch(),
                                         lower=self._manager.MIN_PITCH,
                                         upper=self._manager.MAX_PITCH)

        hscale_pitch = Gtk.HScale()
        hscale_pitch.set_adjustment(self._adj_pitch)
        hscale_pitch.set_draw_value(False)

        box.append_item(hscale_pitch, vertical_padding=0)
        hscale_pitch.show()

        rate_label = Gtk.Label(_('Rate'))
        box.append_item(rate_label, vertical_padding=0)
        rate_label.show()

        self._adj_rate = Gtk.Adjustment(value=self._manager.get_rate(),
                                        lower=self._manager.MIN_RATE,
                                        upper=self._manager.MAX_RATE)

        hscale_rate = Gtk.HScale()
        hscale_rate.set_adjustment(self._adj_rate)
        hscale_rate.set_draw_value(False)

        box.append_item(hscale_rate, vertical_padding=0)
        hscale_rate.show()

        self._adj_pitch.connect('value_changed', self.__adj_pitch_changed_cb)
        self._adj_rate.connect('value_changed', self.__adj_rate_changed_cb)

    def __adj_pitch_changed_cb(self, adjustment):
        self._manager.set_pitch(int(adjustment.get_value()))

    def __adj_rate_changed_cb(self, adjustment):
        self._manager.set_rate(int(adjustment.get_value()))

    def __play_activated_cb(self, widget):
        if self._manager.is_paused:
            self._manager.restart()
        elif not self._manager.is_playing:
            self._manager.say_selected_text()
        else:
            self._manager.pause()

    def __stop_activated_cb(self, widget):
        self._manager.stop()

    def _set_menu_state(self, manager, signal):
        if signal == 'play':
            self._play_pause_menu.set_image(self._pause_icon)
            self._play_pause_menu.set_label(_('Pause playback'))
            self._stop_menu.set_sensitive(True)

        elif signal == 'pause':
            self._play_pause_menu.set_image(self._play_icon)
            self._play_pause_menu.set_label(_('Say selected text'))
            self._stop_menu.set_sensitive(True)

        elif signal == 'stop':
            self._play_pause_menu.set_image(self._play_icon)
            self._play_pause_menu.set_label(_('Say selected text'))
            self._stop_menu.set_sensitive(False)


def setup(tray):
    if speech.get_speech_manager() is not None:
        tray.add_device(SpeechDeviceView())
