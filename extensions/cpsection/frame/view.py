# Copyright (C) 2008, OLPC
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

from gi.repository import Gtk
from gi.repository import GLib
from gettext import gettext as _

from sugar4.graphics import style

from jarabe.controlpanel.sectionview import SectionView

_never = _('never')
_instantaneous = _('instantaneous')
_seconds_label = _('%s seconds')
_MAX_DELAY = 1000


class Frame(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self._corner_delay_sid = 0
        self._corner_delay_change_handler = None
        self._edge_delay_sid = 0
        self._edge_delay_change_handler = None
        self._trigger_size_sid = 0
        self._trigger_size_change_handler = None
        self.restart_alerts = alerts

        self.set_margin_top(style.DEFAULT_SPACING * 2)
        self.set_margin_bottom(style.DEFAULT_SPACING * 2)
        self.set_margin_start(style.DEFAULT_SPACING * 2)
        self.set_margin_end(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(separator)

        label = Gtk.Label(label=_('Activation Delay'))
        label.set_halign(Gtk.Align.START)
        self.append(label)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_top(style.DEFAULT_SPACING * 2)
        box.set_margin_bottom(style.DEFAULT_SPACING * 2)
        box.set_margin_start(style.DEFAULT_SPACING * 2)
        box.set_margin_end(style.DEFAULT_SPACING * 2)
        box.set_spacing(style.DEFAULT_SPACING)

        box.append(self._setup_corner())
        box.append(self._setup_edge())

        self.append(box)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(separator)

        label = Gtk.Label(label=_('Activation Area'))
        label.set_halign(Gtk.Align.START)
        self.append(label)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_top(style.DEFAULT_SPACING * 2)
        box.set_margin_bottom(style.DEFAULT_SPACING * 2)
        box.set_margin_start(style.DEFAULT_SPACING * 2)
        box.set_margin_end(style.DEFAULT_SPACING * 2)
        box.set_spacing(style.DEFAULT_SPACING)

        box.append(self._setup_trigger())

        self.append(box)

        self.setup()

    def _setup_corner(self):
        box_delay = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=style.DEFAULT_SPACING)
        label_delay = Gtk.Label(label=_('Corner'))
        label_delay.set_halign(Gtk.Align.END)
        box_delay.append(label_delay)
        self._group.add_widget(label_delay)

        adj = Gtk.Adjustment(value=100, lower=0, upper=_MAX_DELAY,
                             step_increment=100, page_increment=100, page_size=0)
        self._corner_delay_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self._corner_delay_slider.set_digits(0)
        self._corner_delay_slider.set_hexpand(True)
        self._corner_delay_slider.set_format_value_func(self.__corner_delay_format_cb)
        box_delay.append(self._corner_delay_slider)
        return box_delay

    def _setup_edge(self):
        box_delay = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=style.DEFAULT_SPACING)
        label_delay = Gtk.Label(label=_('Edge'))
        label_delay.set_halign(Gtk.Align.END)
        box_delay.append(label_delay)
        self._group.add_widget(label_delay)

        adj = Gtk.Adjustment(value=100, lower=0, upper=_MAX_DELAY,
                             step_increment=100, page_increment=100, page_size=0)
        self._edge_delay_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self._edge_delay_slider.set_digits(0)
        self._edge_delay_slider.set_hexpand(True)
        self._edge_delay_slider.set_format_value_func(self.__edge_delay_format_cb)
        box_delay.append(self._edge_delay_slider)
        return box_delay

    def _setup_trigger(self):
        box_trigger = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=style.DEFAULT_SPACING)
        label_trigger = Gtk.Label(label=_('Size'))
        label_trigger.set_halign(Gtk.Align.END)
        box_trigger.append(label_trigger)
        self._group.add_widget(label_trigger)

        adj = Gtk.Adjustment(value=1, lower=1, upper=style.GRID_CELL_SIZE,
                             step_increment=1, page_increment=1, page_size=0)
        self._trigger_size_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self._trigger_size_slider.set_digits(0)
        self._trigger_size_slider.set_hexpand(True)
        self._trigger_size_slider.set_format_value_func(self.__trigger_size_format_cb)
        box_trigger.append(self._trigger_size_slider)
        return box_trigger

    def setup(self):
        self._corner_delay_slider.set_value(self._model.get_corner_delay())
        self._edge_delay_slider.set_value(self._model.get_edge_delay())
        self._trigger_size_slider.set_value(self._model.get_trigger_size())
        self.needs_restart = False
        self._corner_delay_change_handler = self._corner_delay_slider.connect(
            'value-changed', self.__corner_delay_changed_cb)
        self._edge_delay_change_handler = self._edge_delay_slider.connect(
            'value-changed', self.__edge_delay_changed_cb)
        self._trigger_size_change_handler = self._trigger_size_slider.connect(
            'value-changed', self.__trigger_size_changed_cb)

    def undo(self):
        self._corner_delay_slider.disconnect(self._corner_delay_change_handler)
        self._edge_delay_slider.disconnect(self._edge_delay_change_handler)
        self._trigger_size_slider.disconnect(self._trigger_size_change_handler)
        self._model.undo()

    def __corner_delay_changed_cb(self, scale, data=None):
        if self._corner_delay_sid:
            GLib.source_remove(self._corner_delay_sid)
        self._corner_delay_sid = GLib.timeout_add(
            self._APPLY_TIMEOUT, self.__corner_delay_timeout_cb, scale)

    def __corner_delay_timeout_cb(self, scale):
        self._corner_delay_sid = 0
        if scale.get_value() == self._model.get_corner_delay():
            return False
        self._model.set_corner_delay(scale.get_value())

        self._trigger_size_slider.queue_draw()
        return False

    def __corner_delay_format_cb(self, scale, value):
        if value == _MAX_DELAY:
            return _never
        if value == 0:
            return _instantaneous
        return _seconds_label % (value / _MAX_DELAY)

    def __edge_delay_changed_cb(self, scale, data=None):
        if self._edge_delay_sid:
            GLib.source_remove(self._edge_delay_sid)
        self._edge_delay_sid = GLib.timeout_add(
            self._APPLY_TIMEOUT, self.__edge_delay_timeout_cb, scale)

    def __edge_delay_timeout_cb(self, scale):
        self._edge_delay_sid = 0
        if scale.get_value() == self._model.get_edge_delay():
            return False
        self._model.set_edge_delay(scale.get_value())

        self._trigger_size_slider.queue_draw()
        return False

    def __edge_delay_format_cb(self, scale, value):
        if value == _MAX_DELAY:
            return _never
        if value == 0:
            return _instantaneous
        return _seconds_label % (value / _MAX_DELAY)

    def __trigger_size_changed_cb(self, scale, data=None):
        if self._trigger_size_sid:
            GLib.source_remove(self._trigger_size_sid)
        self._trigger_size_sid = GLib.timeout_add(
            self._APPLY_TIMEOUT, self.__trigger_size_timeout_cb, scale)

    def __trigger_size_timeout_cb(self, scale):
        self._trigger_size_sid = 0
        if scale.get_value() == self._model.get_trigger_size():
            return False
        self._model.set_trigger_size(scale.get_value())

        return False

    def __trigger_size_format_cb(self, scale, value):
        value = int(value)
        if value == style.GRID_CELL_SIZE:
            return _('toolbar size')
        if value == 1:
            corner = self._model.get_corner_delay() < _MAX_DELAY
            edge = self._model.get_edge_delay() < _MAX_DELAY
            if corner and edge:
                return _('exact corner or edge')
            if corner:
                return _('exact corner')
            if edge:
                return _('exact edge')
            return _('ignored')
        else:
            # TRANS: px as in pixels
            return _('{}px').format(value)

    def apply(self):
        if self._corner_delay_sid:
            GLib.source_remove(self._corner_delay_sid)
            self.__corner_delay_timeout_cb(self._corner_delay_slider)
        if self._edge_delay_sid:
            GLib.source_remove(self._edge_delay_sid)
            self.__edge_delay_timeout_cb(self._edge_delay_slider)
        if self._trigger_size_sid:
            GLib.source_remove(self._trigger_size_sid)
            self.__trigger_size_timeout_cb(self._trigger_size_slider)
