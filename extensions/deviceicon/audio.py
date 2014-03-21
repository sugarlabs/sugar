# Copyright (C) 2008 Martin Dengler
# Copyright (C) 2014 Emil Dudev
# Copyright (C) 2014 Walter Bender
# Copyright (C) 2014 Gonzalo Odiard
# Copyright (C) 2014 Martin Abente
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

from gi.repository import GLib
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
from jarabe.model import sound
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
        device_label = GLib.markup_escape_text(_('My Audio'))
        output_label = GLib.markup_escape_text(self._output_label)
        input_label = GLib.markup_escape_text(self._input_label)
        palette = AudioPalette(device_label, output_label, input_label,
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


class AudioPalette(Palette):

    def __init__(self, primary_text, output_text, input_text, output_model,
                 input_model):
        Palette.__init__(self, label=primary_text)

        self._models = {'output': output_model, 'input': input_model}
        self._adjustments = {}
        self._adjustment_handler_ids = {}
        self._buttons = {}

        self._ok_icons = {'output': Icon(icon_name='dialog-ok'),
                          'input': Icon(icon_name='dialog-ok')}
        self._cancel_icons = {'output': Icon(icon_name='dialog-cancel'),
                              'input': Icon(icon_name='dialog-cancel')}

        self._box = PaletteMenuBox()
        self.set_content(self._box)
        self._box.show()

        self._add_menu_item('media-audio-input', input_text, 'input')

        separator = PaletteMenuItemSeparator()
        self._box.append_item(separator)
        separator.show()

        self._add_menu_item('speaker-100', output_text, 'output')

        self.connect('popup', self.__popup_cb)

    def _add_menu_item(self, label_icon, label_text, device):
        icon = Icon(icon_size=Gtk.IconSize.MENU)
        icon.props.icon_name = label_icon
        icon.props.xo_color = XoColor('%s,%s' %
                                      (style.COLOR_WHITE.get_svg(),
                                       style.COLOR_BUTTON_GREY.get_svg()))

        label = Gtk.Label(label_text)

        alignment = Gtk.Alignment()
        alignment.set(0.5, 0, 0, 0)
        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        grid.attach(icon, 0, 0, 1, 1)
        icon.show()
        grid.attach(label, 1, 0, 1, 1)
        label.show()
        alignment.add(grid)
        grid.show()
        self._box.append_item(alignment, horizontal_padding=0,
                              vertical_padding=0)
        alignment.show()

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)

        vol_step = sound.VOLUME_STEP
        self._adjustments[device] = Gtk.Adjustment(
            value=self._models[device].props.level,
            lower=0,
            upper=100 + vol_step,
            step_incr=vol_step,
            page_incr=vol_step,
            page_size=vol_step)

        hscale = Gtk.HScale()
        hscale.props.draw_value = False
        hscale.set_adjustment(self._adjustments[device])
        hscale.set_digits(0)
        hscale.set_size_request(style.GRID_CELL_SIZE * 4, -1)
        grid.attach(hscale, 0, 0, 1, 1)
        hscale.show()

        self._buttons[device] = Gtk.Button()
        self._buttons[device].connect('clicked',
                                      self.__mute_clicked_cb, device)
        self._buttons[device].props.relief = Gtk.ReliefStyle.NONE
        self._buttons[device].props.focus_on_click = False
        grid.attach(self._buttons[device], 1, 0, 1, 1)
        self._box.append_item(grid)
        grid.show()

        self._adjustment_handler_ids[device] = \
            self._adjustments[device].connect(
                'value_changed', self.__adjustment_changed_cb, device)

    def _update_muted(self, devices):
        for device in devices:
            if self._models[device].props.muted:
                icon_name = self._ok_icons[device]
            else:
                icon_name = self._cancel_icons[device]
            self._buttons[device].set_image(icon_name)
            self._buttons[device].show()

    def _set_muted(self, device, muted):
        self._models[device].props.muted = muted

        self._adjustments[device].handler_block(
            self._adjustment_handler_ids[device])
        try:
            if muted:
                self._adjustments[device].props.value = 0
                self._models[device].props.level = 0
            else:
                self._adjustments[device].props.value = \
                    self._models[device].props.last_level
                self._models[device].props.level = \
                    self._models[device].props.last_level
        finally:
            self._adjustments[device].handler_unblock(
                self._adjustment_handler_ids[device])

        if muted:
            icon_name = self._ok_icons[device]
        else:
            icon_name = self._cancel_icons[device]
        self._buttons[device].set_image(icon_name)

    def _update_level(self, devices):
        for device in devices:
            if self._adjustments[device].props.value != \
               self._models[device].props.level:
                self._adjustments[device].handler_block(
                    self._adjustment_handler_ids[device])
                try:
                    self._adjustments[device].props.value = \
                        self._models[device].props.level
                finally:
                    self._adjustments[device].handler_unblock(
                        self._adjustment_handler_ids[device])

    def __adjustment_changed_cb(self, widget_, device):
        self._models[device].props.level = \
            self._adjustments[device].props.value

        muted = self._adjustments[device].props.value == 0
        self._models[device].props.muted = muted
        if muted:
            icon_name = self._ok_icons[device]
        else:
            icon_name = self._cancel_icons[device]
        self._buttons[device].set_image(icon_name)

    def __level_changed_cb(self, pspec_, param_, device):
        self._update_level([device])

    def __mute_clicked_cb(self, button, device):
        self._set_muted(device, not self._models[device].props.muted)

    def __muted_changed_cb(self, pspec_, param_, device):
        self._set_muted(device, self._models[device].props.muted)

    def __popup_cb(self, palette_):
        self._update_level(['output', 'input'])
        self._update_muted(['output', 'input'])


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
