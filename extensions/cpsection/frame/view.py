# Copyright (C) 2008, OLPC
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from gi.repository import Gtk
from gi.repository import GObject
from gettext import gettext as _

from sugar3.graphics import style

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert


_never = _('never')
_instantaneous = _('instantaneous')
_seconds_label = _('%s seconds')
_MAX_DELAY = 1000


class Frame(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self._corner_delay_sid = 0
        self._corner_delay_is_valid = True
        self._corner_delay_change_handler = None
        self._edge_delay_sid = 0
        self._edge_delay_is_valid = True
        self._edge_delay_change_handler = None
        self.restart_alerts = alerts

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        separator = Gtk.HSeparator()
        self.pack_start(separator, False, True, 0)
        separator.show()

        label_activation = Gtk.Label(label=_('Activation Delay'))
        label_activation.set_alignment(0, 0)
        self.pack_start(label_activation, False, True, 0)
        label_activation.show()

        self._box_sliders = Gtk.VBox()
        self._box_sliders.set_border_width(style.DEFAULT_SPACING * 2)
        self._box_sliders.set_spacing(style.DEFAULT_SPACING)

        self._corner_delay_slider = None
        self._corner_delay_alert = None
        self._setup_corner()

        self._edge_delay_slider = None
        self._edge_delay_alert = None
        self._setup_edge()

        self.pack_start(self._box_sliders, False, True, 0)
        self._box_sliders.show()

        self.setup()

    def _setup_corner(self):
        box_delay = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_delay = Gtk.Label(label=_('Corner'))
        label_delay.set_alignment(1, 0.75)
        label_delay.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_delay.pack_start(label_delay, False, True, 0)
        self._group.add_widget(label_delay)
        label_delay.show()

        adj = Gtk.Adjustment(value=100, lower=0, upper=_MAX_DELAY,
                             step_incr=100, page_incr=100, page_size=0)
        self._corner_delay_slider = Gtk.HScale()
        self._corner_delay_slider.set_adjustment(adj)
        self._corner_delay_slider.set_digits(0)
        self._corner_delay_slider.connect('format-value',
                                          self.__corner_delay_format_cb)
        box_delay.pack_start(self._corner_delay_slider, True, True, 0)
        self._corner_delay_slider.show()
        self._box_sliders.pack_start(box_delay, False, True, 0)
        box_delay.show()

        self._corner_delay_alert = InlineAlert()
        label_delay_error = Gtk.Label()
        self._group.add_widget(label_delay_error)

        delay_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        delay_alert_box.pack_start(label_delay_error, False, True, 0)
        label_delay_error.show()
        delay_alert_box.pack_start(self._corner_delay_alert, False, True, 0)
        self._box_sliders.pack_start(delay_alert_box, False, True, 0)
        delay_alert_box.show()
        if 'corner_delay' in self.restart_alerts:
            self._corner_delay_alert.props.msg = self.restart_msg
            self._corner_delay_alert.show()

    def _setup_edge(self):
        box_delay = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_delay = Gtk.Label(label=_('Edge'))
        label_delay.set_alignment(1, 0.75)
        label_delay.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_delay.pack_start(label_delay, False, True, 0)
        self._group.add_widget(label_delay)
        label_delay.show()

        adj = Gtk.Adjustment(value=100, lower=0, upper=_MAX_DELAY,
                             step_incr=100, page_incr=100, page_size=0)
        self._edge_delay_slider = Gtk.HScale()
        self._edge_delay_slider.set_adjustment(adj)
        self._edge_delay_slider.set_digits(0)
        self._edge_delay_slider.connect('format-value',
                                        self.__edge_delay_format_cb)
        box_delay.pack_start(self._edge_delay_slider, True, True, 0)
        self._edge_delay_slider.show()
        self._box_sliders.pack_start(box_delay, False, True, 0)
        box_delay.show()

        self._edge_delay_alert = InlineAlert()
        label_delay_error = Gtk.Label()
        self._group.add_widget(label_delay_error)

        delay_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        delay_alert_box.pack_start(label_delay_error, False, True, 0)
        label_delay_error.show()
        delay_alert_box.pack_start(self._edge_delay_alert, False, True, 0)
        self._box_sliders.pack_start(delay_alert_box, False, True, 0)
        delay_alert_box.show()
        if 'edge_delay' in self.restart_alerts:
            self._edge_delay_alert.props.msg = self.restart_msg
            self._edge_delay_alert.show()

    def setup(self):
        self._corner_delay_slider.set_value(self._model.get_corner_delay())
        self._edge_delay_slider.set_value(self._model.get_edge_delay())
        self._corner_delay_is_valid = True
        self._edge_delay_is_valid = True
        self.needs_restart = False
        self._corner_delay_change_handler = self._corner_delay_slider.connect(
            'value-changed', self.__corner_delay_changed_cb)
        self._edge_delay_change_handler = self._edge_delay_slider.connect(
            'value-changed', self.__edge_delay_changed_cb)

    def undo(self):
        self._corner_delay_slider.disconnect(self._corner_delay_change_handler)
        self._edge_delay_slider.disconnect(self._edge_delay_change_handler)
        self._model.undo()
        self._corner_delay_alert.hide()
        self._edge_delay_alert.hide()

    def _validate(self):
        if self._edge_delay_is_valid and self._corner_delay_is_valid:
            self.props.is_valid = True
        else:
            self.props.is_valid = False

    def __corner_delay_changed_cb(self, scale, data=None):
        if self._corner_delay_sid:
            GObject.source_remove(self._corner_delay_sid)
        self._corner_delay_sid = GObject.timeout_add(
            self._APPLY_TIMEOUT, self.__corner_delay_timeout_cb, scale)

    def __corner_delay_timeout_cb(self, scale):
        self._corner_delay_sid = 0
        if scale.get_value() == self._model.get_corner_delay():
            return
        try:
            self._model.set_corner_delay(scale.get_value())
        except ValueError, detail:
            self._corner_delay_alert.props.msg = detail
            self._corner_delay_is_valid = False
        else:
            self._corner_delay_alert.props.msg = self.restart_msg
            self._corner_delay_is_valid = True
            self.needs_restart = True
            self.restart_alerts.append('corner_delay')

        self._validate()
        self._corner_delay_alert.show()
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
            return
        try:
            self._model.set_edge_delay(scale.get_value())
        except ValueError, detail:
            self._edge_delay_alert.props.msg = detail
            self._edge_delay_is_valid = False
        else:
            self._edge_delay_alert.props.msg = self.restart_msg
            self._edge_delay_is_valid = True
            self.needs_restart = True
            self.restart_alerts.append('edge_delay')

        self._validate()
        self._edge_delay_alert.show()
        return False

    def __edge_delay_format_cb(self, scale, value):
        if value == _MAX_DELAY:
            return _never
        elif value == 0:
            return _instantaneous
        else:
            return _seconds_label % (value / _MAX_DELAY)
