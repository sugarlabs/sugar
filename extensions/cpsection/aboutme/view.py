# Copyright (C) 2008, OLPC
# Copyright (C) 2010, Sugar Labs
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
from sugar3.graphics.xocolor import XoColor, colors
from sugar3.graphics.icon import CanvasIcon

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert

_STROKE_COLOR = 0
_FILL_COLOR = 1


def _get_next_stroke_color(color):
    """ Return the next color pair in the list that shares the same fill
        as color. """
    current_index = _get_current_index(color)
    if current_index == -1:
        return '%s,%s' % (color.stroke, color.fill)
    next_index = _next_index(current_index)
    while(colors[next_index][_FILL_COLOR] !=
          colors[current_index][_FILL_COLOR]):
        next_index = _next_index(next_index)
    return '%s,%s' % (colors[next_index][_STROKE_COLOR],
                      colors[next_index][_FILL_COLOR])


def _get_previous_stroke_color(color):
    """ Return the previous color pair in the list that shares the same fill
        as color. """
    current_index = _get_current_index(color)
    if current_index == -1:
        return '%s,%s' % (color.stroke, color.fill)
    previous_index = _previous_index(current_index)
    while (colors[previous_index][_FILL_COLOR] !=
           colors[current_index][_FILL_COLOR]):
        previous_index = _previous_index(previous_index)
    return '%s,%s' % (colors[previous_index][_STROKE_COLOR],
                      colors[previous_index][_FILL_COLOR])


def _get_next_fill_color(color):
    """ Return the next color pair in the list that shares the same stroke
        as color. """
    current_index = _get_current_index(color)
    if current_index == -1:
        return '%s,%s' % (color.stroke, color.fill)
    next_index = _next_index(current_index)
    while (colors[next_index][_STROKE_COLOR] !=
           colors[current_index][_STROKE_COLOR]):
        next_index = _next_index(next_index)
    return '%s,%s' % (colors[next_index][_STROKE_COLOR],
                      colors[next_index][_FILL_COLOR])


def _get_previous_fill_color(color):
    """ Return the previous color pair in the list that shares the same stroke
        as color. """
    current_index = _get_current_index(color)
    if current_index == -1:
        return '%s,%s' % (color.stroke, color.fill)
    previous_index = _previous_index(current_index)
    while (colors[previous_index][_STROKE_COLOR] !=
           colors[current_index][_STROKE_COLOR]):
        previous_index = _previous_index(previous_index)
    return '%s,%s' % (colors[previous_index][_STROKE_COLOR],
                      colors[previous_index][_FILL_COLOR])


def _next_index(current_index):
    next_index = current_index + 1
    if next_index == len(colors):
        next_index = 0
    return next_index


def _previous_index(current_index):
    previous_index = current_index - 1
    if previous_index < 0:
        previous_index = len(colors) - 1
    return previous_index


def _get_current_index(color):
    return colors.index([color.stroke, color.fill])


_PREVIOUS_FILL_COLOR = 0
_NEXT_FILL_COLOR = 1
_CURRENT_COLOR = 2
_NEXT_STROKE_COLOR = 3
_PREVIOUS_STROKE_COLOR = 4


class ColorPicker(CanvasIcon):
    __gsignals__ = {
        'color-changed': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          ([object])),
    }

    def __init__(self, picker):
        CanvasIcon.__init__(self, icon_name='computer-xo',
                            pixel_size=style.XLARGE_ICON_SIZE)
        self._picker = picker
        self._color = None

        self.connect('button_press_event', self.__pressed_cb, picker)

    def update(self, color):
        if self._picker == _PREVIOUS_FILL_COLOR:
            self._color = XoColor(_get_previous_fill_color(color))
        elif self._picker == _PREVIOUS_STROKE_COLOR:
            self._color = XoColor(_get_previous_stroke_color(color))
        elif self._picker == _NEXT_FILL_COLOR:
            self._color = XoColor(_get_next_fill_color(color))
        elif self._picker == _NEXT_STROKE_COLOR:
            self._color = XoColor(_get_next_stroke_color(color))
        else:
            self._color = color
        self.props.xo_color = self._color

    def __pressed_cb(self, button, event, picker):
        if picker != _CURRENT_COLOR:
            self.emit('color-changed', self._color)


class AboutMe(SectionView):

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._nick_sid = 0
        self._color_valid = True
        self._nick_valid = True

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        self._color_label = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_alert = None

        self._pickers = {
            _PREVIOUS_FILL_COLOR: ColorPicker(_PREVIOUS_FILL_COLOR),
            _NEXT_FILL_COLOR: ColorPicker(_NEXT_FILL_COLOR),
            _CURRENT_COLOR: ColorPicker(_CURRENT_COLOR),
            _NEXT_STROKE_COLOR: ColorPicker(_NEXT_STROKE_COLOR),
            _PREVIOUS_STROKE_COLOR: ColorPicker(_PREVIOUS_STROKE_COLOR),
        }

        self._setup_color()
        initial_color = XoColor(self._model.get_color_xo())
        self._update_pickers(initial_color)

        self._nick_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_entry = None
        self._nick_alert = None
        self._setup_nick()
        self.setup()

    def _setup_nick(self):
        self._nick_entry = Gtk.Entry()
        self._nick_entry.set_width_chars(25)
        self._nick_box.pack_start(self._nick_entry, False, True, 0)
        self._nick_entry.show()

        label_entry_error = Gtk.Label()
        self._group.add_widget(label_entry_error)
        self._nick_alert_box.pack_start(label_entry_error, False, True, 0)
        label_entry_error.show()

        self._nick_alert = InlineAlert()
        self._nick_alert_box.pack_start(self._nick_alert, True, True, 0)
        if 'nick' in self.restart_alerts:
            self._nick_alert.props.msg = self.restart_msg
            self._nick_alert.show()

        self._center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        self._center_in_panel.add(self._nick_box)
        self.pack_start(self._center_in_panel, False, False, 0)
        self.pack_start(self._nick_alert_box, False, False, 0)
        self._nick_box.show()
        self._nick_alert_box.show()
        self._center_in_panel.show()

    def _setup_color(self):
        label_color = Gtk.Label(label=_('Click to change your color:'))
        label_color.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        self._group.add_widget(label_color)
        self._color_label.pack_start(label_color, False, True, 0)
        label_color.show()

        for picker_index in sorted(self._pickers.keys()):
            if picker_index == _CURRENT_COLOR:
                left_separator = Gtk.SeparatorToolItem()
                left_separator.show()
                self._color_box.pack_start(left_separator, False, True, 0)

            picker = self._pickers[picker_index]
            picker.show()
            self._color_box.pack_start(picker, False, True, 0)

            if picker_index == _CURRENT_COLOR:
                right_separator = Gtk.SeparatorToolItem()
                right_separator.show()
                self._color_box.pack_start(right_separator, False, True, 0)

        label_color_error = Gtk.Label()
        self._group.add_widget(label_color_error)
        self._color_alert_box.pack_start(label_color_error, False, True, 0)
        label_color_error.show()

        self._color_alert = InlineAlert()
        self._color_alert_box.pack_start(self._color_alert, True, True, 0)
        if 'color' in self.restart_alerts:
            self._color_alert.props.msg = self.restart_msg
            self._color_alert.show()

        self._center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        self._center_in_panel.add(self._color_box)
        self.pack_start(self._color_label, False, False, 0)
        self.pack_start(self._center_in_panel, False, False, 0)
        self.pack_start(self._color_alert_box, False, False, 0)
        self._color_label.show()
        self._color_box.show()
        self._color_alert_box.show()
        self._center_in_panel.show()

    def setup(self):
        self._nick_entry.set_text(self._model.get_nick())
        self._color_valid = True
        self._nick_valid = True
        self.needs_restart = False

        self._nick_entry.connect('changed', self.__nick_changed_cb)
        for picker in self._pickers.values():
            picker.connect('color-changed', self.__color_changed_cb)

    def undo(self):
        self._model.undo()
        self._nick_alert.hide()
        self._color_alert.hide()

    def _update_pickers(self, color):
        for picker in self._pickers.values():
            picker.update(color)

    def _validate(self):
        if self._nick_valid and self._color_valid:
            self.props.is_valid = True
        else:
            self.props.is_valid = False

    def __nick_changed_cb(self, widget, data=None):
        if self._nick_sid:
            GObject.source_remove(self._nick_sid)
        self._nick_sid = GObject.timeout_add(self._APPLY_TIMEOUT,
                                             self.__nick_timeout_cb, widget)

    def __nick_timeout_cb(self, widget):
        self._nick_sid = 0

        if widget.get_text() == self._model.get_nick():
            return False
        try:
            self._model.set_nick(widget.get_text())
        except ValueError, detail:
            self._nick_alert.props.msg = detail
            self._nick_valid = False
        else:
            self._nick_alert.props.msg = self.restart_msg
            self._nick_valid = True
            self.needs_restart = True
            self.restart_alerts.append('nick')
        self._validate()
        self._nick_alert.show()
        return False

    def __color_changed_cb(self, colorpicker, color):
        self._model.set_color_xo(color.to_string())
        self.needs_restart = True
        self._color_alert.props.msg = self.restart_msg
        self._color_valid = True
        self.restart_alerts.append('color')

        self._validate()
        self._color_alert.show()

        self._update_pickers(color)

        return False
