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
from jarabe.intro.agepicker import AGES, AGE_LABELS 

_STROKE_COLOR = 0
_FILL_COLOR = 1
_NOCOLOR = XoColor('#010101,#ffffff')


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
                            pixel_size=style.LARGE_ICON_SIZE)
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


class GenderPicker(CanvasIcon):
    __gsignals__ = {
        'gender-changed': (GObject.SignalFlags.RUN_FIRST,
                           None,
                           ([object])),
    }

    def __init__(self, color, gender):
        CanvasIcon.__init__(self, icon_name='%s-6' % (gender),
                            pixel_size=style.XLARGE_ICON_SIZE)
        self._gender = gender
        self._color = color

        self.update_selected()

        self.connect('button_press_event', self.__pressed_cb)

    def update_color(self, color, gender):
        self._color = color
        self.update_selected(gender)

    def update_selected(self, gender=None):
        if self._gender == gender:
            self.props.xo_color = self._color
        else:
            self.props.xo_color = _NOCOLOR

    def __pressed_cb(self, button, event):
        self.emit('gender-changed', self._gender)


class AgePicker(Gtk.VBox):
    __gsignals__ = {
        'age-changed': (GObject.SignalFlags.RUN_FIRST,
                        None,
                        ([object])),
    }

    def __init__(self, color, gender, age):
        Gtk.VBox.__init__(self)
        self._color = color
        self._gender = gender
        self._age = age

        if self._gender == None:
            self._gender = 'male'

        eventbox = Gtk.EventBox()
        self._icon = CanvasIcon(icon_name='%s-%d' % (self._gender, self._age),
                                pixel_size=style.LARGE_ICON_SIZE)
        self._icon.show()
        eventbox.connect('button-press-event', self.__pressed_cb)
        eventbox.add(self._icon)
        eventbox.show()

        label = Gtk.Label()
        label.set_text(AGE_LABELS[self._age])
        label.show()
        
        self.pack_end(label, True, True, 0)
        self.pack_end(eventbox, True, True, 0)

        self.update_selected()

    def update_color(self, color, age):
        self._color = color
        self.update_selected(age)

    def update_selected(self, age=None):
        if age in AGES:
            age_index = AGES.index(age)
        else:
            age_index = None
        
        if age_index == self._age:
            self._icon.props.xo_color = self._color
        else:
            self._icon.props.xo_color = _NOCOLOR
        self._icon.show()

    def update_gender(self, gender):
        self._icon.set_icon_name('%s-%d' % (gender, self._age))
        self._icon.show()

    def __pressed_cb(self, button, event):
        self.emit('age-changed', self._age)


class AboutMe(SectionView):

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._nick_sid = 0
        self._color_valid = True
        self._nick_valid = True
        self._color = None
        self._gender = None
        self._age = None

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
        self._color = XoColor(self._model.get_color_xo())
        self._update_pickers(self._color)

        self._nick_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_entry = None
        self._nick_alert = None
        self._setup_nick()

        self._gender_label = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._gender_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._female_picker = GenderPicker(self._color, 'female')
        self._male_picker = GenderPicker(self._color, 'male')
        self._setup_gender()

        self._age_label = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._age_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._age_pickers = []
        for i in range(len(AGES)):
            self._age_pickers.append(AgePicker(self._color, self._gender, i))
        self._setup_age()

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

    def _setup_gender(self):
        self._gender = self._model.get_gender()

        label_gender = Gtk.Label(label=_('Select gender:'))
        label_gender.modify_fg(Gtk.StateType.NORMAL,
                               style.COLOR_SELECTION_GREY.get_gdk_color())
        self._group.add_widget(label_gender)
        self._gender_label.pack_start(label_gender, False, True, 0)
        label_gender.show()

        self._gender_box.pack_start(self._female_picker, False, True, 0)
        self._female_picker.update_selected(self._gender)
        self._female_picker.show()
        self._gender_box.pack_start(self._male_picker, False, True, 0)
        self._male_picker.update_selected(self._gender)
        self._male_picker.show()

        self._gender_center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        self._gender_center_in_panel.add(self._gender_box)
        self.pack_start(self._gender_label, False, False, 0)
        self.pack_start(self._gender_center_in_panel, False, False, 0)
        self._gender_label.show()
        self._gender_box.show()
        self._gender_center_in_panel.show()

    def _setup_age(self):
        self._age = self._model.get_age()

        label_age = Gtk.Label(label=_('Select age:'))
        label_age.modify_fg(Gtk.StateType.NORMAL,
                               style.COLOR_SELECTION_GREY.get_gdk_color())
        self._group.add_widget(label_age)
        self._age_label.pack_start(label_age, False, True, 0)
        label_age.show()

        for i in range(len(AGES)):
            self._age_box.pack_start(self._age_pickers[i], False, True, 0)
            self._age_pickers[i].update_selected(self._age)
            self._age_pickers[i].show()

        self._age_center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        self._age_center_in_panel.add(self._age_box)
        self.pack_start(self._age_label, False, False, 0)
        self.pack_start(self._age_center_in_panel, False, False, 0)
        self._age_label.show()
        self._age_box.show()
        self._age_center_in_panel.show()

    def setup(self):
        self._nick_entry.set_text(self._model.get_nick())
        self._color_valid = True
        self._nick_valid = True
        self.needs_restart = False

        self._nick_entry.connect('changed', self.__nick_changed_cb)
        for picker in self._pickers.values():
            picker.connect('color-changed', self.__color_changed_cb)
        self._female_picker.connect('gender-changed', self.__gender_changed_cb)
        self._male_picker.connect('gender-changed', self.__gender_changed_cb)
        for picker in self._age_pickers:
            picker.connect('age-changed', self.__age_changed_cb)

    def undo(self):
        self._model.undo()
        self._model.set_gender(self._gender)
        self._model.set_age(self._age)
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
        self._female_picker.update_color(color, self._gender)
        self._male_picker.update_color(color, self._gender)
        for i in range(len(AGES)):
            self._age_pickers[i].update_color(color, self._age)
        return False

    def __gender_changed_cb(self, genderpicker, gender):
        self._model.set_gender(gender)
        self._female_picker.update_selected(gender)
        self._male_picker.update_selected(gender)
        for i in range(len(AGES)):
            self._age_pickers[i].update_gender(gender)
        return False

    def __age_changed_cb(self, agepicker, age):
        self._model.set_age(AGES[age])
        for i in range(len(AGES)):
            self._age_pickers[i].update_selected(AGES[age])
        return False
