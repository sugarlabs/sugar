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
from gi.repository import GObject
from gettext import gettext as _

from sugar3.graphics import style

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

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        separator = Gtk.HSeparator()
        self.pack_start(separator, False, True, 0)

        label = Gtk.Label(label=_('Activation Delay'))
        label.set_alignment(0, 0)
        self.pack_start(label, False, True, 0)

        box = Gtk.VBox()
        box.set_border_width(style.DEFAULT_SPACING * 2)
        box.set_spacing(style.DEFAULT_SPACING)

        box.pack_start(self._setup_corner(), False, True, 0)
        box.pack_start(self._setup_edge(), False, True, 0)

        self.pack_start(box, False, True, 0)

        separator = Gtk.HSeparator()
        self.pack_start(separator, False, True, 0)

        label = Gtk.Label(label=_('Activation Area'))
        label.set_alignment(0, 0)
        self.pack_start(label, False, True, 0)

        box = Gtk.VBox()
        box.set_border_width(style.DEFAULT_SPACING * 2)
        box.set_spacing(style.DEFAULT_SPACING)

        box.pack_start(self._setup_trigger(), False, True, 0)

        self.pack_start(box, False, True, 0)
        self.show_all()

        self.setup()

    def _setup_corner(self):
        box_delay = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_delay = Gtk.Label(label=_('Corner'))
        label_delay.set_alignment(1, 0.75)
        label_delay.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_delay.pack_start(label_delay, False, True, 0)
        self._group.add_widget(label_delay)

        adj = Gtk.Adjustment(value=100, lower=0, upper=_MAX_DELAY,
                             step_incr=100, page_incr=100, page_size=0)
        self._corner_delay_slider = Gtk.HScale()
        self._corner_delay_slider.set_adjustment(adj)
        self._corner_delay_slider.set_digits(0)
        self._corner_delay_slider.connect('format-value',
                                          self.__corner_delay_format_cb)
        box_delay.pack_start(self._corner_delay_slider, True, True, 0)
        return box_delay

    def _setup_edge(self):
        box_delay = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_delay = Gtk.Label(label=_('Edge'))
        label_delay.set_alignment(1, 0.75)
        label_delay.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_delay.pack_start(label_delay, False, True, 0)
        self._group.add_widget(label_delay)

        adj = Gtk.Adjustment(value=100, lower=0, upper=_MAX_DELAY,
                             step_incr=100, page_incr=100, page_size=0)
        self._edge_delay_slider = Gtk.HScale()
        self._edge_delay_slider.set_adjustment(adj)
        self._edge_delay_slider.set_digits(0)
        self._edge_delay_slider.connect('format-value',
                                        self.__edge_delay_format_cb)
        box_delay.pack_start(self._edge_delay_slider, True, True, 0)
        return box_delay

    def _setup_trigger(self):
        box_trigger = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_trigger = Gtk.Label(label=_('Size'))
        label_trigger.set_alignment(1, 0.75)
        label_trigger.modify_fg(Gtk.StateType.NORMAL,
                                style.COLOR_SELECTION_GREY.get_gdk_color())
        box_trigger.pack_start(label_trigger, False, True, 0)
        self._group.add_widget(label_trigger)

        adj = Gtk.Adjustment(value=1, lower=1, upper=style.GRID_CELL_SIZE,
                             step_incr=1, page_incr=1, page_size=0)
        self._trigger_size_slider = Gtk.HScale()
        self._trigger_size_slider.set_adjustment(adj)
        self._trigger_size_slider.set_digits(0)
        self._trigger_size_slider.connect('format-value',
                                          self.__trigger_size_format_cb)
        box_trigger.pack_start(self._trigger_size_slider, True, True, 0)
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
            GObject.source_remove(self._corner_delay_sid)
        self._corner_delay_sid = GObject.timeout_add(
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
        elif value == 0:
            return _instantaneous
        else:
            return _seconds_label % (value / _MAX_DELAY)

    def __edge_delay_changed_cb(self, scale, data=None):
        if self._edge_delay_sid:
            GObject.source_remove(self._edge_delay_sid)
        self._edge_delay_sid = GObject.timeout_add(
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
        elif value == 0:
            return _instantaneous
        else:
            return _seconds_label % (value / _MAX_DELAY)

    def __trigger_size_changed_cb(self, scale, data=None):
        if self._trigger_size_sid:
            GObject.source_remove(self._trigger_size_sid)
        self._trigger_size_sid = GObject.timeout_add(
            self._APPLY_TIMEOUT, self.__trigger_size_timeout_cb, scale)

    def __trigger_size_timeout_cb(self, scale):
        self._trigger_size_sid = 0
        if scale.get_value() == self._model.get_trigger_size():
            return
        self._model.set_trigger_size(scale.get_value())

        return False

    def __trigger_size_format_cb(self, scale, value):
        value = int(value)
        if value == style.GRID_CELL_SIZE:
            return _('toolbar size')
        elif value == 1:
            corner = self._model.get_corner_delay() < _MAX_DELAY
            edge = self._model.get_edge_delay() < _MAX_DELAY
            if corner and edge:
                return _('exact corner or edge')
            elif corner:
                return _('exact corner')
            elif edge:
                return _('exact edge')
            else:
                return _('ignored')
        else:
            # TRANS: px as in pixels
            return _('{}px').format(value)

    def apply(self):
        if self._corner_delay_sid:
            GObject.source_remove(self._corner_delay_sid)
            self.__corner_delay_timeout_cb(self._corner_delay_slider)
        if self._edge_delay_sid:
            GObject.source_remove(self._edge_delay_sid)
            self.__edge_delay_timeout_cb(self._edge_delay_slider)
        if self._trigger_size_sid:
            GObject.source_remove(self._trigger_size_sid)
            self.__trigger_size_timeout_cb(self._trigger_size_sid)
