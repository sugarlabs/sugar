# Copyright (C) 2008 Martin Dengler
# Copyright (C) 2014 Emil Dudev
# Copyright (C) 2014 Walter Bender
# Copyright (C) 2014 Gonzalo Odiard
# Copyright (C) 2014 Martin Abente
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

from gi.repository import GObject
from gi.repository import Gtk

from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.icon import get_icon_state, Icon
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator
from sugar3.graphics.xocolor import XoColor

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model.sound import sound
from jarabe.model.sound import capture_sound

_ICON_NAME = 'speaker'


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 103

    def __init__(self, output_device_model, output_label,
                 input_device_model, input_label):
        self._color = profile.get_color()
        self._output_label = output_label
        self._input_label = input_label

        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True

        self._audio_input_model = input_device_model()

        self._audio_output_model = output_device_model()
        # The tray icon is only for the output device
        self._audio_output_model.connect('notify::level',
                                         self.__output_status_changed_cb)
        self._audio_output_model.connect('notify::muted',
                                         self.__output_status_changed_cb)

        self._update_output_info()

    def create_palette(self):
        palette = AudioPalette(_('My Audio'),
                               self._output_label,
                               self._input_label,
                               output_model=self._audio_output_model,
                               input_model=self._audio_input_model)
        palette.set_group_id('frame')
        return palette

    def _update_output_info(self):
        name = _ICON_NAME

        current_level = self._audio_output_model.props.level
        xo_color = self._color

        if self._audio_output_model.props.muted:
            name += '-muted'
            xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                          style.COLOR_WHITE.get_svg()))

        self.icon.props.icon_name = get_icon_state(name, current_level,
                                                   step=-1)
        self.icon.props.xo_color = xo_color

    def __output_status_changed_cb(self, pspec_, param_):
        self._update_output_info()


class AudioManagerWidget(Gtk.VBox):

    def __init__(self, text, icon_name, device):
        Gtk.VBox.__init__(self)
        self._device = device

        self._ok_icon = Icon(icon_name='dialog-ok')
        self._cancel_icon = Icon(icon_name='dialog-cancel')

        icon = Icon(pixel_size=style.SMALL_ICON_SIZE)
        icon.props.icon_name = icon_name
        icon.props.xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                      style.COLOR_BUTTON_GREY.get_svg()))
        icon.show()

        label = Gtk.Label(text)
        label.show()

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        grid.attach(icon, 0, 0, 1, 1)
        grid.attach(label, 1, 0, 1, 1)
        grid.show()

        alignment = Gtk.Alignment()
        alignment.set(0.5, 0, 0, 0)
        alignment.add(grid)
        alignment.show()

        self.add(alignment)

        adjustment = Gtk.Adjustment(
            value=device.props.level,
            lower=0,
            upper=100 + sound.VOLUME_STEP,
            step_incr=sound.VOLUME_STEP,
            page_incr=sound.VOLUME_STEP,
            page_size=sound.VOLUME_STEP)
        self._adjustment = adjustment

        hscale = Gtk.HScale()
        hscale.props.draw_value = False
        hscale.set_adjustment(adjustment)
        hscale.set_digits(0)
        hscale.set_size_request(style.GRID_CELL_SIZE * 4, -1)
        hscale.show()

        button = Gtk.Button()
        button.props.relief = Gtk.ReliefStyle.NONE
        button.props.focus_on_click = False
        button.connect('clicked', self.__muted_clicked_cb)
        button.show()
        self._button = button

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        grid.attach(hscale, 0, 0, 1, 1)
        grid.attach(button, 1, 0, 1, 1)
        grid.show()

        alignment = Gtk.Alignment()
        alignment.set(0.5, 0, 0, 0)
        alignment.set_padding(0, 0, style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING)
        alignment.add(grid)
        alignment.show()

        self.add(alignment)

        self._adjustment_hid = \
            self._adjustment.connect('value_changed',
                                     self.__level_adjusted_cb)

    def update_level(self):
        self._adjustment.handler_block(self._adjustment_hid)
        self._adjustment.props.value = self._device.props.level
        self._adjustment.handler_unblock(self._adjustment_hid)

    def update_muted(self):
        if self._device.props.muted:
            self._button.set_image(self._ok_icon)
        else:
            self._button.set_image(self._cancel_icon)

    def __level_adjusted_cb(self, device, data=None):
        value = self._adjustment.props.value
        self._device.props.level = value

        # FIXME use callbacks instead
        if value <= 0:
            self._device.props.muted = True
        else:
            self._device.props.muted = False
        self.update_muted()

    def __muted_clicked_cb(self, button, data=None):
        muted = not self._device.props.muted
        self._device.props.muted = muted
        self.update_muted()

        # FIXME use callbacks instead
        if muted:
            self._device.props.level = 0
        else:
            self._device.props.level = self._device.props.last_level
        self.update_level()


class AudioPalette(Palette):

    def __init__(self, primary_text, output_text, input_text, output_model,
                 input_model):
        Palette.__init__(self, label=primary_text)

        self._capture_manager = AudioManagerWidget(input_text,
                                                   'media-audio-input',
                                                   input_model)
        self._capture_manager.show()

        separator = PaletteMenuItemSeparator()
        separator.show()

        self._speaker_manager = AudioManagerWidget(output_text,
                                                   'speaker-100',
                                                   output_model)
        self._speaker_manager.show()

        self._box = PaletteMenuBox()
        self._box.append_item(self._capture_manager, 0, 0)
        self._box.append_item(separator, 0, 0)
        self._box.append_item(self._speaker_manager, 0, 0)
        self._box.show()

        self.set_content(self._box)

        self.connect('popup', self.__popup_cb)

    def __popup_cb(self, palette):
        self._speaker_manager.update_level()
        self._speaker_manager.update_muted()
        self._capture_manager.update_level()
        self._capture_manager.update_muted()


class DeviceModelAudio(GObject.GObject):
    __gproperties__ = {
        'level': (int, None, None, 0, 100, 0, GObject.PARAM_READWRITE),
        'last-level': (int, None, None, 0, 100, 0, GObject.PARAM_READABLE),
        'muted': (bool, None, None, False, GObject.PARAM_READWRITE),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._device = None
        self._last_level = 0

    def _get_level(self):
        return self._device.get_volume()

    def _set_level(self, new_volume):
        self._device.set_volume(new_volume)

    def _get_muted(self):
        return self._device.get_muted()

    def _set_muted(self, mute):
        if mute and self._device.get_volume() > 0:
            self._last_level = self._device.get_volume()
        self._device.set_muted(mute)

    def _get_last_level(self):
        return self._last_level

    def get_type(self):
        raise NotImplementedError

    def do_get_property(self, pspec):
        if pspec.name == 'level':
            value = self._get_level()
        if pspec.name == 'last-level':
            value = self._get_last_level()
        elif pspec.name == 'muted':
            value = self._get_muted()
        return value

    def do_set_property(self, pspec, value):
        if pspec.name == 'level':
            self._set_level(value)
        elif pspec.name == 'muted':
            self._set_muted(value)


class DeviceModelSpeaker(DeviceModelAudio):

    def __init__(self):
        DeviceModelAudio.__init__(self)

        self._device = sound
        self._last_level = self._device.get_volume()
        self._device.muted_changed.connect(self.__muted_changed_cb)
        self._device.volume_changed.connect(self.__volume_changed_cb)

    def __muted_changed_cb(self, **kwargs):
        self.notify('muted')

    def __volume_changed_cb(self, **kwargs):
        self.notify('level')

    def get_type(self):
        return 'speaker'


class DeviceModelCapture(DeviceModelAudio):

    def __init__(self):
        DeviceModelAudio.__init__(self)

        self._device = capture_sound
        self._last_level = self._device.get_volume()
        self._device.muted_changed.connect(self.__muted_changed_cb)
        self._device.volume_changed.connect(self.__volume_changed_cb)

    def __muted_changed_cb(self, **kwargs):
        self.notify('muted')

    def __volume_changed_cb(self, **kwargs):
        self.notify('level')

    def get_type(self):
        return 'capture'


def setup(tray):
    tray.add_device(DeviceView(DeviceModelSpeaker, _('Speaker'),
                               DeviceModelCapture, _('Microphone')))
