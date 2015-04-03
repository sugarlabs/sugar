# Copyright (C) 2008 Martin Dengler
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
from gi.repository import GConf

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import get_icon_state, Icon
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator
from sugar3.graphics.xocolor import XoColor

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import sound

_ICON_NAME = 'speaker'


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 103

    def __init__(self):
        client = GConf.Client.get_default()
        self._color = XoColor(client.get_string('/desktop/sugar/user/color'))

        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True

        self._model = DeviceModel()
        self._model.connect('notify::level', self.__speaker_status_changed_cb)
        self._model.connect('notify::muted', self.__speaker_status_changed_cb)

        self.connect('draw', self.__draw_cb)

        self._update_info()

    def create_palette(self):
        label = GLib.markup_escape_text(_('My Speakers'))
        palette = SpeakerPalette(label, model=self._model)
        palette.set_group_id('frame')
        return palette

    def _update_info(self):
        name = _ICON_NAME
        current_level = self._model.props.level
        xo_color = self._color

        if self._model.props.muted:
            name += '-muted'
            xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                          style.COLOR_WHITE.get_svg()))

        self.icon.props.icon_name = get_icon_state(name, current_level,
                                                   step=-1)
        self.icon.props.xo_color = xo_color

    def __draw_cb(self, *args):
        self._update_info()

    def __speaker_status_changed_cb(self, pspec_, param_):
        self._update_info()


class SpeakerPalette(Palette):

    def __init__(self, primary_text, model):
        Palette.__init__(self, label=primary_text)

        self._model = model

        box = PaletteMenuBox()
        self.set_content(box)
        box.show()

        self._mute_item = PaletteMenuItem('')
        self._mute_icon = Icon(icon_size=Gtk.IconSize.MENU)
        self._mute_item.set_image(self._mute_icon)
        box.append_item(self._mute_item)
        self._mute_item.show()
        self._mute_item.connect('activate', self.__mute_activate_cb)

        separator = PaletteMenuItemSeparator()
        box.append_item(separator)
        separator.show()

        vol_step = sound.VOLUME_STEP
        self._adjustment = Gtk.Adjustment(value=self._model.props.level,
                                          lower=0,
                                          upper=100 + vol_step,
                                          step_incr=vol_step,
                                          page_incr=vol_step,
                                          page_size=vol_step)

        hscale = Gtk.HScale()
        hscale.props.draw_value = False
        hscale.set_adjustment(self._adjustment)
        hscale.set_digits(0)
        box.append_item(hscale, vertical_padding=0)
        hscale.show()

        self._adjustment_handler_id = \
            self._adjustment.connect('value_changed',
                                     self.__adjustment_changed_cb)

        self._model_notify_level_handler_id = \
            self._model.connect('notify::level', self.__level_changed_cb)
        self._model.connect('notify::muted', self.__muted_changed_cb)

        self.connect('popup', self.__popup_cb)

    def _update_muted(self):
        if self._model.props.muted:
            mute_item_text = _('Unmute')
            mute_item_icon_name = 'dialog-ok'
        else:
            mute_item_text = _('Mute')
            mute_item_icon_name = 'dialog-cancel'
        self._mute_item.set_label(mute_item_text)
        self._mute_icon.props.icon_name = mute_item_icon_name
        self._mute_icon.show()

    def _update_level(self):
        if self._adjustment.props.value != self._model.props.level:
            self._adjustment.handler_block(self._adjustment_handler_id)
            try:
                self._adjustment.props.value = self._model.props.level
            finally:
                self._adjustment.handler_unblock(self._adjustment_handler_id)

    def __adjustment_changed_cb(self, adj_):
        self._model.handler_block(self._model_notify_level_handler_id)
        try:
            self._model.props.level = self._adjustment.props.value
        finally:
            self._model.handler_unblock(self._model_notify_level_handler_id)
        self._model.props.muted = self._adjustment.props.value == 0

    def __level_changed_cb(self, pspec_, param_):
        self._update_level()

    def __mute_activate_cb(self, menuitem_):
        self._model.props.muted = not self._model.props.muted

    def __muted_changed_cb(self, pspec_, param_):
        self._update_muted()

    def __popup_cb(self, palette_):
        self._update_level()
        self._update_muted()


class DeviceModel(GObject.GObject):
    __gproperties__ = {
        'level': (int, None, None, 0, 100, 0, GObject.PARAM_READWRITE),
        'muted': (bool, None, None, False, GObject.PARAM_READWRITE),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        sound.muted_changed.connect(self.__muted_changed_cb)
        sound.volume_changed.connect(self.__volume_changed_cb)

    def __muted_changed_cb(self, **kwargs):
        self.notify('muted')

    def __volume_changed_cb(self, **kwargs):
        self.notify('level')

    def _get_level(self):
        return sound.get_volume()

    def _set_level(self, new_volume):
        sound.set_volume(new_volume)

    def _get_muted(self):
        return sound.get_muted()

    def _set_muted(self, mute):
        sound.set_muted(mute)

    def get_type(self):
        return 'speaker'

    def do_get_property(self, pspec):
        if pspec.name == 'level':
            return self._get_level()
        elif pspec.name == 'muted':
            return self._get_muted()

    def do_set_property(self, pspec, value):
        if pspec.name == 'level':
            self._set_level(value)
        elif pspec.name == 'muted':
            self._set_muted(value)


def setup(tray):
    tray.add_device(DeviceView())
