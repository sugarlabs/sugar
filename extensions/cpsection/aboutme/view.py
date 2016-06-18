# Copyright (C) 2008, OLPC
# Copyright (C) 2010-14, Sugar Labs
# Copyright (C) 2010-14, Walter Bender
# Copyright (C) 2014, Ignacio Rodriguez
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
from sugar3.graphics.xocolor import XoColor, colors
from sugar3.graphics.icon import EventIcon

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert
from jarabe.intro.agepicker import AgePicker, save_age, load_age
from jarabe.intro.genderpicker import GenderPicker, save_gender, load_gender


_STROKE_COLOR = 0
_FILL_COLOR = 1
_NOCOLOR = XoColor('#010101,#FFFFFF')


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


class ColorPicker(EventIcon):

    color_changed_signal = GObject.Signal('color-changed',
                                          arg_types=([object]))

    def __init__(self, picker):
        EventIcon.__init__(self, icon_name='computer-xo',
                           pixel_size=style.LARGE_ICON_SIZE)
        self._picker = picker
        self._color = None

        self.connect('activate', self.__activate_cb, picker)

    def set_color(self, color):
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

    color = GObject.property(type=object, setter=set_color)

    def __activate_cb(self, button, picker):
        if picker != _CURRENT_COLOR:
            self.color_changed_signal.emit(self._color)


class AboutMe(SectionView):

    age_changed_signal = GObject.Signal('age-changed', arg_types=([int]))
    gender_changed_signal = GObject.Signal('gender-changed', arg_types=([str]))

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts if alerts else set()
        self.props.is_deferrable = False
        self._nick_sid = 0
        self._color_valid = True
        self._nick_valid = True
        self._color = None
        self._gender = ''
        self._age = None

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self._color = XoColor(self._model.get_color())

        self._original_nick = self._model.get_nick()
        self._setup_color()
        self._setup_nick()
        self._setup_gender()
        self._setup_age()

        self._update_pickers(self._color)

        self._nick_entry.set_text(self._original_nick)
        self._color_valid = True
        self._nick_valid = True
        self.needs_restart = False

        self._nick_entry.connect('changed', self.__nick_changed_cb)

        for picker in self._pickers.values():
            picker.connect('color-changed', self.__color_changed_cb)

        self._gender_pickers.connect('gender-changed',
                                     self.__gender_changed_cb)
        self._age_pickers.connect('age-changed', self.__age_changed_cb)

    def _setup_nick(self):
        grid = Gtk.Grid()
        grid.set_row_spacing(style.DEFAULT_SPACING)
        grid.set_column_spacing(style.DEFAULT_SPACING)

        self._nick_entry = Gtk.Entry()
        self._nick_entry.set_width_chars(25)
        grid.attach(self._nick_entry, 0, 0, 1, 1)
        self._nick_entry.show()

        alert_grid = Gtk.Grid()
        self._nick_alert = InlineAlert()
        alert_grid.attach(self._nick_alert, 0, 0, 1, 1)
        if 'nick' in self.restart_alerts:
            self._nick_alert.props.msg = self.restart_msg
            self._nick_alert.show()

        center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        center_in_panel.add(grid)
        grid.show()

        center_alert = Gtk.Alignment.new(0.5, 0, 0, 0)
        center_alert.add(alert_grid)
        alert_grid.show()

        self.pack_start(center_in_panel, False, False, 0)
        self.pack_start(center_alert, False, False, 0)
        center_in_panel.show()
        center_alert.show()

    def _setup_color(self):
        grid = Gtk.Grid()
        grid.set_row_spacing(style.DEFAULT_SPACING)
        grid.set_column_spacing(style.DEFAULT_SPACING)

        self._color_alert = None

        self._pickers = {
            _PREVIOUS_FILL_COLOR: ColorPicker(_PREVIOUS_FILL_COLOR),
            _NEXT_FILL_COLOR: ColorPicker(_NEXT_FILL_COLOR),
            _CURRENT_COLOR: ColorPicker(_CURRENT_COLOR),
            _NEXT_STROKE_COLOR: ColorPicker(_NEXT_STROKE_COLOR),
            _PREVIOUS_STROKE_COLOR: ColorPicker(_PREVIOUS_STROKE_COLOR),
        }

        label_color = Gtk.Label(label=_('Click to change your color:'))
        label_color.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        grid.attach(label_color, 0, 0, 3, 1)
        label_color.show()

        current = 0
        for picker_index in sorted(self._pickers.keys()):
            if picker_index == _CURRENT_COLOR:
                left_separator = Gtk.SeparatorToolItem()
                grid.attach(left_separator, current, 1, 1, 1)
                left_separator.show()
                current += 1

            picker = self._pickers[picker_index]
            picker.show()
            grid.attach(picker, current, 1, 1, 1)
            current += 1

            if picker_index == _CURRENT_COLOR:
                right_separator = Gtk.SeparatorToolItem()
                right_separator.show()
                grid.attach(right_separator, current, 1, 1, 1)
                current += 1

        label_color_error = Gtk.Label()
        grid.attach(label_color_error, 0, 2, 3, 1)
        label_color_error.show()

        self._color_alert = InlineAlert()
        grid.attach(self._color_alert, 0, 3, 3, 1)
        if 'color' in self.restart_alerts:
            self._color_alert.props.msg = self.restart_msg
            self._color_alert.show()

        center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        center_in_panel.add(grid)
        grid.show()

        self.pack_start(center_in_panel, False, False, 0)
        center_in_panel.show()

    def _setup_gender(self):
        self._saved_gender = load_gender()

        self._gender_pickers = GenderPicker()

        grid = Gtk.Grid()
        grid.set_row_spacing(style.DEFAULT_SPACING)
        grid.set_column_spacing(style.DEFAULT_SPACING)

        label_gender = Gtk.Label(label=_('Select gender:'))
        label_gender.modify_fg(Gtk.StateType.NORMAL,
                               style.COLOR_SELECTION_GREY.get_gdk_color())
        grid.attach(label_gender, 0, 0, 1, 1)
        label_gender.show()

        grid.attach(self._gender_pickers, 0, 1, 1, 1)
        self._gender_pickers.show()

        center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        center_in_panel.add(grid)
        grid.show()

        self.pack_start(center_in_panel, False, False, 0)
        center_in_panel.show()

    def _setup_age(self):
        self._saved_age = load_age()

        grid = Gtk.Grid()
        grid.set_row_spacing(style.DEFAULT_SPACING)
        grid.set_column_spacing(style.DEFAULT_SPACING)

        self._age_pickers = AgePicker(self._saved_gender)
        center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        center_in_panel.add(self._age_pickers)
        self._age_pickers.show()

        label = self._age_pickers.get_label()

        label_age = Gtk.Label(label=_(label))
        label_age.modify_fg(Gtk.StateType.NORMAL,
                            style.COLOR_SELECTION_GREY.get_gdk_color())
        left_align = Gtk.Alignment.new(0, 0, 0, 0)
        left_align.add(label_age)
        label_age.show()
        grid.attach(left_align, 0, 0, 1, 1)
        left_align.show()

        grid.attach(center_in_panel, 0, 1, 1, 1)
        center_in_panel.show()

        center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        center_in_panel.add(grid)
        grid.show()
        self.pack_start(center_in_panel, False, False, 0)
        center_in_panel.show()

    def setup(self):
        pass

    def undo(self):
        self._model.undo()
        self._nick_alert.hide()
        self._color_alert.hide()

        # Undo gender or age changes
        save_gender(self._saved_gender)
        save_age(self._saved_age)

    def _update_pickers(self, color):
        for picker in self._pickers.values():
            picker.props.color = color
        self._gender_pickers.update_color(color)
        self._age_pickers.update_color(color)

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
            self.restart_alerts.remove('nick')
            if not self.restart_alerts:
                self.needs_restart = False
            self._nick_alert.hide()
            return False
        try:
            self._model.set_nick(widget.get_text())
        except ValueError, detail:
            self._nick_alert.props.msg = detail
            self._nick_valid = False
            self._nick_alert.show()
        else:
            self._nick_valid = True
            if widget.get_text() == self._original_nick:
                self.restart_alerts.remove('nick')
                if not self.restart_alerts:
                    self.needs_restart = False
                self._nick_alert.hide()
            else:
                self._nick_alert.props.msg = self.restart_msg
                self.needs_restart = True
                self.restart_alerts.add('nick')
                self._nick_alert.show()
        self._validate()
        return False

    def __color_changed_cb(self, colorpicker, color):
        self._model.set_color_xo(color.to_string())
        self.needs_restart = True
        self._color_alert.props.msg = self.restart_msg
        self._color_valid = True
        self.restart_alerts.add('color')

        self._validate()
        self._color_alert.show()

        self._update_pickers(color)
        return False

    def __gender_changed_cb(self, genderpicker, gender):
        save_gender(gender)
        self._age_pickers.update_gender(gender)
        return False

    def __age_changed_cb(self, event, age):
        save_age(age)
