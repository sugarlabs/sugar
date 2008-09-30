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

import gtk

from jarabe.hardware import hardwaremanager
from sugar import profile
from sugar.graphics import style
from sugar.graphics.icon import get_icon_state, Icon
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.tray import TrayIcon
from sugar.graphics.palette import Palette
from sugar.graphics.xocolor import XoColor

from jarabe.frame.frameinvoker import FrameWidgetInvoker

_ICON_NAME = 'speaker'

class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 800

    def __init__(self, model):
        TrayIcon.__init__(self,
                          icon_name=_ICON_NAME,
                          xo_color=profile.get_color())

        self._model = model
        self.palette = SpeakerPalette(_('My Speakers'), model=model)
        self.palette.props.invoker = FrameWidgetInvoker(self)
        self.palette.set_group_id('frame')

        model.connect('notify::level', self.__speaker_status_changed_cb)
        model.connect('notify::muted', self.__speaker_status_changed_cb)
        self.connect('expose-event', self.__expose_event_cb)

        self._icon_widget.connect('button-press-event',
                                  self.__update_mute_status)

        self._update_info()

    def _update_info(self):
        name = _ICON_NAME
        current_level = self._model.props.level
        xo_color = profile.get_color()

        if self._model.props.muted:
            name += '-muted'
            xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                          style.COLOR_WHITE.get_svg()))

        self.icon.props.icon_name = get_icon_state(name, current_level, step=-1)
        self.icon.props.xo_color = xo_color

    def __update_mute_status(self, *args):
        self._model.props.muted = not self._model.props.muted

    def __expose_event_cb(self, *args):
        self._update_info()

    def __speaker_status_changed_cb(self, pspec_, param_):
        self._update_info()

class SpeakerPalette(Palette):

    def __init__(self, primary_text, model):
        Palette.__init__(self, label=primary_text)

        self._model = model

        self.set_size_request(style.zoom(style.GRID_CELL_SIZE * 4), -1)

        vbox = gtk.VBox()
        self.set_content(vbox)
        vbox.show()

        vol_step = hardwaremanager.VOL_CHANGE_INCREMENT_RECOMMENDATION
        self._adjustment = gtk.Adjustment(value=self._model.props.level,
                                          lower=0,
                                          upper=100 + vol_step,
                                          step_incr=vol_step,
                                          page_incr=vol_step,
                                          page_size=vol_step)
        self._hscale = gtk.HScale(self._adjustment)
        self._hscale.set_digits(0)
        self._hscale.set_draw_value(False)
        vbox.add(self._hscale)
        self._hscale.show()

        self._mute_item = MenuItem('')
        self._mute_icon = Icon(icon_size=gtk.ICON_SIZE_MENU)
        self._mute_item.set_image(self._mute_icon)
        self.menu.append(self._mute_item)
        self._mute_item.show()

        self._adjustment_handler_id = \
            self._adjustment.connect('value_changed',
                                     self.__adjustment_changed_cb)

        self._model_notify_level_handler_id = \
            self._model.connect('notify::level', self.__level_changed_cb)
        self._model.connect('notify::muted', self.__muted_changed_cb)

        self._mute_item.connect('activate', self.__mute_activate_cb)

        self.connect('popup', self.__popup_cb)

    def _update_muted(self):
        if self._model.props.muted:
            mute_item_text = _('Unmute')
            mute_item_icon_name = 'dialog-ok'
        else:
            mute_item_text = _('Mute')
            mute_item_icon_name = 'dialog-cancel'
        self._mute_item.get_child().set_text(mute_item_text)
        self._mute_icon.props.icon_name = mute_item_icon_name

    def _update_level(self):
        if self._adjustment.value != self._model.props.level:
            self._adjustment.handler_block(self._adjustment_handler_id)
            try:
                self._adjustment.value = self._model.props.level
            finally:
                self._adjustment.handler_unblock(self._adjustment_handler_id)

    def __adjustment_changed_cb(self, adj_):
        self._model.handler_block(self._model_notify_level_handler_id)
        try:
            self._model.props.level = self._adjustment.value
        finally:
            self._model.handler_unblock(self._model_notify_level_handler_id)
        self._model.props.muted = self._adjustment.value == 0

    def __level_changed_cb(self, pspec_, param_):
        self._update_level()

    def __mute_activate_cb(self, menuitem_):
        self._model.props.muted = not self._model.props.muted

    def __muted_changed_cb(self, pspec_, param_):
        self._update_muted()

    def __popup_cb(self, palette_):
        self._update_level()
        self._update_muted()
