# Copyright (C) 2014 Sam Parkinson
# Copyright (C) 2015 Martin Abente Lahaye
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
import math

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import GObject

from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator
from sugar3.graphics.xocolor import XoColor

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import brightness
from jarabe.model.screenshot import take_screenshot
from jarabe import frame


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 160

    def __init__(self, label):
        self._color = profile.get_color()
        self._label = label

        TrayIcon.__init__(self, icon_name='brightness-100',
                          xo_color=self._color)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True

        model = brightness.get_instance()
        if model.get_path():
            self._model = model
            self._model.changed_signal.connect(self.__brightness_changed_cb)
            self._update_output_info()

    def create_palette(self):
        palette = DisplayPalette()
        palette.set_group_id('frame')
        return palette

    def _update_output_info(self, value=None):
        if value is None:
            value = self._model.get_brightness()

        icon_number = math.ceil(
            float(value) * 3 / self._model.get_max_brightness()) * 33

        if icon_number == 99:
            icon_number = 100

        self.icon.props.icon_name = \
            'brightness-{:03d}'.format(int(icon_number))

    def __brightness_changed_cb(self, model, value):
        self._update_output_info(value)


class BrightnessManagerWidget(Gtk.VBox):

    TIMEOUT_DELAY = 10

    def __init__(self, text, icon_name):
        Gtk.VBox.__init__(self)
        self._progress_bar = None
        self._adjustment = None

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

        alignment = Gtk.Alignment()
        alignment.set(0.5, 0, 0, 0)
        alignment.set_padding(0, 0, style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING)

        self._model = brightness.get_instance()
        self._model_changed_hid = \
            self._model.changed_signal.connect(self.__brightness_changed_cb)

        # if sugar-backlight-helper finds the device
        if self._model.get_path():
            adjustment = Gtk.Adjustment(
                value=self._model.get_brightness(),
                lower=0,
                upper=self._model.get_max_brightness() + 1,
                step_incr=self._model.get_step_amount(),
                page_incr=self._model.get_step_amount(),
                page_size=self._model.get_step_amount())
            self._adjustment = adjustment

            self._adjustment_timeout_id = None
            self._adjustment_hid = \
                self._adjustment.connect('value_changed', self.__adjusted_cb)

            hscale = Gtk.HScale()
            hscale.props.draw_value = False
            hscale.set_adjustment(adjustment)
            hscale.set_digits(0)
            hscale.set_size_request(style.GRID_CELL_SIZE * 4, -1)
            alignment.add(hscale)
            hscale.show()
        else:
            self._progress_bar = Gtk.ProgressBar()
            self._progress_bar.set_size_request(
                style.zoom(style.GRID_CELL_SIZE * 4), -1)
            alignment.props.top_padding = style.DEFAULT_PADDING
            alignment.add(self._progress_bar)
            self._progress_bar.show()

        alignment.show()
        self.add(alignment)

    def __brightness_changed_cb(self, model, value):
        self.update(value)

    def update(self, value=None):
        if value is None:
            value = self._model.get_brightness()

        if self._adjustment:
            self._adjustment.handler_block(self._adjustment_hid)
            self._adjustment.props.value = value
            self._adjustment.handler_unblock(self._adjustment_hid)
        else:
            self._progress_bar.props.fraction = \
                float(value) / self._model.get_max_brightness()

    def __adjusted_cb(self, device, data=None):
        if self._adjustment_timeout_id is not None:
            GLib.source_remove(self._adjustment_timeout_id)
        self._adjustment_timeout_id = GLib.timeout_add(
            self.TIMEOUT_DELAY, self._adjust_brightness)

    def _adjust_brightness(self):
        self._model.handler_block(self._model_changed_hid)
        self._model.set_brightness(int(self._adjustment.props.value))
        self._model.handler_unblock(self._model_changed_hid)
        self._adjustment_timeout_id = None
        return False


class DisplayPalette(Palette):

    def __init__(self):
        Palette.__init__(self, label=_('My Display'))

        self._screenshot = PaletteMenuItem(_('Take a screenshot'))
        icon = Icon(icon_name='camera-external',
                    pixel_size=style.SMALL_ICON_SIZE)
        self._screenshot.set_image(icon)
        icon.show()
        self._screenshot.connect('activate', self.__screenshot_cb)
        self._screenshot.show()

        self._box = PaletteMenuBox()

        self._brightness_manager = None
        # only add this widget if device available
        if brightness.get_instance().get_path():
            self._add_brightness_manager()

        self._box.append_item(self._screenshot, 0, 0)
        self._box.show()

        self.set_content(self._box)
        self.connect('popup', self.__popup_cb)

    def _add_brightness_manager(self):
        self._brightness_manager = BrightnessManagerWidget(_('Brightness'),
                                                           'brightness-100')
        self._brightness_manager.show()

        separator = PaletteMenuItemSeparator()
        separator.show()

        self._box.append_item(self._brightness_manager, 0, 0)
        self._box.append_item(separator, 0, 0)

    def __popup_cb(self, palette):
        if self._brightness_manager is not None:
            self._brightness_manager.update()

    def __screenshot_cb(self, palette):
        frame_ = frame.get_view()
        frame_.hide()
        GObject.idle_add(self.__take_screenshot_cb, frame_)

    def __take_screenshot_cb(self, frame_):
        if frame_.is_visible():
            return True
        take_screenshot()
        frame_.show()
        return False


def setup(tray):
    tray.add_device(DeviceView(_('Display')))
