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

from gettext import gettext as _

import glib
import gtk
import gconf
import gobject

from sugar.graphics.icon import Icon
from sugar.graphics.tray import TrayIcon
from sugar.graphics.palette import Palette
from sugar.graphics.xocolor import XoColor
from sugar.graphics.menuitem import MenuItem
from sugar.graphics import style

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import speech


_ICON_NAME = 'microphone'


class SpeechDeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 150

    def __init__(self):
        client = gconf.client_get_default()
        self._color = XoColor(client.get_string('/desktop/sugar/user/color'))
        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self._manager = speech.get_speech_manager()
        self._icon_widget.connect('button-release-event',
                                  self.__button_release_event_cb)

    def create_palette(self):
        label = glib.markup_escape_text(_('Speech'))
        palette = SpeechPalette(label, manager=self._manager)
        palette.set_group_id('frame')
        return palette

    def __button_release_event_cb(self, widget, event):
        self.palette_invoker.notify_right_click()
        return True


class SpeechPalette(Palette):

    def __init__(self, primary_text, manager):
        Palette.__init__(self, label=primary_text)

        self._manager = manager
        self._manager.connect('play', self._set_menu_state, 'play')
        self._manager.connect('stop', self._set_menu_state, 'stop')
        self._manager.connect('pause', self._set_menu_state, 'pause')

        vbox = gtk.VBox()
        self.set_content(vbox)

        self._play_icon = Icon(icon_name='player_play')
        self._pause_icon = Icon(icon_name='player_pause')
        self._play_pause_menu = MenuItem(text_label=_('Say selected text'))
        self._play_pause_menu.set_image(self._play_icon)
        self._play_pause_menu.connect('activate', self.__play_activated_cb)
        self._play_pause_menu.show()

        self._stop_menu = MenuItem(icon_name='player_stop',
                text_label=_('Stop playback'))
        self._stop_menu.connect('activate', self.__stop_activated_cb)
        self._stop_menu.set_sensitive(False)
        self._stop_menu.show()

        self.menu.append(self._play_pause_menu)
        self.menu.append(self._stop_menu)

        self._adj_pitch = gtk.Adjustment(value=self._manager.get_pitch(),
                                          lower=self._manager.MIN_PITCH,
                                          upper=self._manager.MAX_PITCH)
        self._hscale_pitch = gtk.HScale(self._adj_pitch)
        self._hscale_pitch.set_draw_value(False)

        vbox.pack_start(gtk.Label(_('Pitch')), padding=style.DEFAULT_PADDING)
        vbox.pack_start(self._hscale_pitch)

        self._adj_rate = gtk.Adjustment(value=self._manager.get_rate(),
                                          lower=self._manager.MIN_RATE,
                                          upper=self._manager.MAX_RATE)
        self._hscale_rate = gtk.HScale(self._adj_rate)
        self._hscale_rate.set_draw_value(False)

        vbox.pack_start(gtk.Label(_('Rate')), padding=style.DEFAULT_PADDING)
        vbox.pack_start(self._hscale_rate)
        vbox.show_all()

        self._adj_pitch.connect('value_changed', self.__adj_pitch_changed_cb)
        self._adj_rate.connect('value_changed', self.__adj_rate_changed_cb)

    def __adj_pitch_changed_cb(self, adjustement):
        self._manager.set_pitch(int(adjustement.value))

    def __adj_rate_changed_cb(self, adjustement):
        self._manager.set_rate(int(adjustement.value))

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
    tray.add_device(SpeechDeviceView())
