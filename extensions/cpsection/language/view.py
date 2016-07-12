# Copyright (C) 2008, OLPC
# Copyright (C) 2009, Simon Schampijer
# Copyright (C) 2014, Walter Bender
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


import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
import gettext

from sugar3.graphics import style
from sugar3.graphics.icon import Icon

from sugar3.graphics.palettemenu import PaletteMenuItem

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert


def _translate_language(msg):
    return gettext.dgettext('iso_639', msg)


def _translate_country(msg):
    return gettext.dgettext('iso_3166', msg)

CLASS = 'Language'
ICON = 'module-language'
TITLE = gettext.gettext('Language')


class Language(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self.props.is_deferrable = False
        self._lang_sid = 0
        self._selected_lang_count = 0
        self._labels = []
        self._language_dict = {}
        self._country_dict = {}
        self._language_buttons = []
        self._country_buttons = []
        self._language_widgets = []
        self._country_widgets = []
        self._country_codes = []
        self._add_remove_boxes = []
        self._changed = False
        self._cursor_change_handler = None

        self._available_locales = self._model.read_all_languages()
        self._selected_locales = self._model.get_languages()

        for language, country, code in self._available_locales:
            if language not in self._language_dict:
                self._language_dict[language] = _translate_language(language)
                self._country_dict[language] = [[code, country]]
            else:
                self._country_dict[language].append([code, country])

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        explanation = gettext.gettext('Add languages in the order you prefer.'
                                      ' If a translation is not available,'
                                      ' the next in the list will be used.')
        self._text = Gtk.Label(label=explanation)
        self._text.set_line_wrap(True)
        self._text.set_alignment(0, 0)
        self.pack_start(self._text, False, False, 0)
        self._text.show()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.show()
        self.pack_start(scrolled, True, True, 0)

        self._table = Gtk.Table(rows=2, columns=4, homogeneous=False)
        self._table.set_border_width(style.DEFAULT_SPACING * 2)
        self._table.show()
        scrolled.add_with_viewport(self._table)

        self._lang_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self.pack_start(self._lang_alert_box, False, True, 0)

        self._lang_alert = InlineAlert()
        self._lang_alert_box.pack_start(self._lang_alert, True, True, 0)
        if 'lang' in self.restart_alerts:
            self._lang_alert.props.msg = self.restart_msg
            self._lang_alert.show()
        self._lang_alert_box.show()

        self.setup()

    def _add_row(self, locale_code=None):
        """Adds two rows to the table:
           (1) the buttons and labels for language and country;
           (2) the tables of languages and country options"""

        self._selected_lang_count += 1

        self._table.resize(self._selected_lang_count * 2, 3)

        label = Gtk.Label(label=str(self._selected_lang_count))
        label.modify_fg(Gtk.StateType.NORMAL,
                        style.COLOR_SELECTION_GREY.get_gdk_color())
        self._labels.append(label)
        self._attach_to_table(label, 0, 1, self._selected_lang_count * 2 - 1,
                              xpadding=1, ypadding=1)
        label.show()

        locale_language = None
        locale_country = None

        if locale_code is not None:
            for language, country, code in self._available_locales:
                if code == locale_code:
                    locale_language = language
                    locale_country = country
            for language, country, code in self._available_locales:
                if code == '.'.join([locale_code, 'utf8']):
                    locale_language = language
                    locale_country = country

        language_palette = []
        key_list = self._language_dict.keys()
        for language_key in sorted(key_list):
            language_palette.append(
                {'label': self._language_dict[language_key],
                 'index': len(self._language_buttons),
                 'callback': self._language_changed})

        new_language_widget = set_palette_list(language_palette)
        if locale_language is None:
            locale_language = 'English'
        new_language_button = FilterToolItem(
            'go-down', 'go-up', locale_language, new_language_widget)
        country_list = self._build_country_list(locale_language)

        new_country_widget = set_palette_list(country_list)
        if locale_country is None:
            if locale_language == 'English':
                locale_country = 'USA'
            else:
                locale_country = self._country_dict[locale_language][0]
        new_country_button = FilterToolItem(
            'go-down', 'go-up', locale_country, new_country_widget)

        if locale_code is None:
            # check the locale code acordinig to the default values selected
            for language, country, code in self._available_locales:
                if language == locale_language and country == locale_country:
                    locale_code = code
        self._country_codes.append(locale_code)

        self._language_buttons.append(new_language_button)
        self._attach_to_table(
            new_language_button, 1, 2, self._selected_lang_count * 2 - 1,
            yoptions=Gtk.AttachOptions.SHRINK)

        self._language_widgets.append(new_language_widget)
        self._attach_to_table(new_language_widget, 1, 2,
                              self._selected_lang_count * 2,
                              xpadding=style.DEFAULT_PADDING,
                              ypadding=0)

        self._country_buttons.append(new_country_button)
        self._attach_to_table(
            new_country_button, 2, 3, self._selected_lang_count * 2 - 1,
            yoptions=Gtk.AttachOptions.SHRINK)

        self._country_widgets.append(new_country_widget)
        self._attach_to_table(new_country_widget, 2, 3,
                              self._selected_lang_count * 2,
                              xpadding=style.DEFAULT_PADDING,
                              ypadding=0)

        add_remove_box = self._create_add_remove_box()
        self._add_remove_boxes.append(add_remove_box)
        self._attach_to_table(add_remove_box, 3, 4,
                              self._selected_lang_count * 2 - 1)

        add_remove_box.show_all()

        if self._selected_lang_count > 1:
            previous_add_removes = self._add_remove_boxes[-2]
            previous_add_removes.hide()

        # Hide the Remove button if the new added row is the only
        # language.
        elif self._selected_lang_count == 1:
            add_button_, remove_button = add_remove_box.get_children()
            remove_button.props.visible = False

        new_language_button.show()
        new_country_button.show()

    def _build_country_list(self, language, idx=None):
        country_list = []
        if idx is None:
            idx = len(self._country_buttons)

        for country, code in sorted((_translate_country(entry[1]), entry[0])
                                    for entry in self._country_dict[language]):
            country_list.append(
                {'label': country,
                 'code': code,
                 'index': idx,
                 'callback': self._country_changed})
        return country_list

    def _attach_to_table(self, widget, left, right, above,
                         xpadding=style.DEFAULT_SPACING,
                         ypadding=style.DEFAULT_SPACING,
                         yoptions=Gtk.AttachOptions.FILL):
        self._table.attach(widget, left, right,
                           above,
                           above + 1,
                           xoptions=Gtk.AttachOptions.FILL,
                           yoptions=yoptions,
                           xpadding=xpadding,
                           ypadding=ypadding)

    def _delete_last_row(self):
        """Deletes the last two rows of the table"""

        self._selected_lang_count -= 1

        label = self._labels.pop()
        label.destroy()

        add_remove_box = self._add_remove_boxes.pop()
        add_remove_box.destroy()

        language_button = self._language_buttons.pop()
        language_button.destroy()

        country_button = self._country_buttons.pop()
        country_button.destroy()

        language_widget = self._language_widgets.pop()
        language_widget.destroy()

        country_widget = self._country_widgets.pop()
        country_widget.destroy()

        # Remove language code associated with last row
        self._country_codes.pop()

        self._table.resize(self._selected_lang_count * 2, 3)

        if self._selected_lang_count < 1:
            return

        self._add_remove_boxes[-1].show_all()

        # Hide or show the Remove button in the new last row,
        # depending if it is the only language.
        add_remove_box = self._add_remove_boxes[-1]
        add_button_, remove_button = add_remove_box.get_children()
        if self._selected_lang_count == 1:
            remove_button.props.visible = False
        else:
            remove_button.props.visible = True

    def setup(self):
        for locale in self._selected_locales:
            self._add_row(locale_code=locale)

    def _delete_all_rows(self):
        while self._selected_lang_count > 0:
            self._delete_last_row()

    def undo(self):
        self._model.undo()
        self._lang_alert.hide()
        self._delete_all_rows()

    def _create_add_remove_box(self):
        """Creates Gtk.Hbox with add/remove buttons"""
        add_icon = Icon(icon_name='list-add')

        add_button = Gtk.Button()
        add_button.set_image(add_icon)
        add_button.connect('clicked',
                           self.__add_button_clicked_cb)

        remove_icon = Icon(icon_name='list-remove')
        remove_button = Gtk.Button()
        remove_button.set_image(remove_icon)
        remove_button.connect('clicked',
                              self.__remove_button_clicked_cb)

        add_remove_box = Gtk.HButtonBox()
        add_remove_box.set_layout(Gtk.ButtonBoxStyle.START)
        add_remove_box.set_spacing(10)
        add_remove_box.pack_start(add_button, True, True, 0)
        add_remove_box.pack_start(remove_button, True, True, 0)

        return add_remove_box

    def __add_button_clicked_cb(self, button):
        self._add_row()
        self._check_change()

    def __remove_button_clicked_cb(self, button):
        self._delete_last_row()
        self._check_change()

    def _language_changed(self, widget, event, item):
        i = item['index']

        for language_key in self._language_dict.keys():
            if self._language_dict[language_key] == item['label']:
                new_country_list = \
                    self._build_country_list(language_key, idx=i)
                break

        self._language_buttons[i].set_widget_label(item['label'])
        self._language_buttons[i].button_cb()

        self._country_buttons[i].set_widget_label(
            _translate_country(self._country_dict[language_key][0][1])),
        self._country_codes[i] = self._country_dict[language_key][0][0]

        old_country_widget = self._country_widgets[i]
        old_country_widget.destroy()

        new_country_widget = set_palette_list(new_country_list)
        self._country_buttons[i].set_widget(new_country_widget)
        self._country_widgets[i] = new_country_widget
        self._attach_to_table(new_country_widget, 2, 3, (i + 1) * 2,
                              xpadding=style.DEFAULT_PADDING,
                              ypadding=0)

        self._update_country(new_country_list[0])

    def _country_changed(self, widget, event, item):
        self._update_country(item)

    def _update_country(self, item):
        i = item['index']
        self._country_codes[i] = item['code']
        self._country_buttons[i].set_widget_label(item['label'])
        self._country_buttons[i].button_cb()

        self._check_change()

    def _check_change(self):
        selected_langs = self._country_codes[:]

        self._changed = (selected_langs != self._selected_locales)

        if self._changed is False:
            # The user reverted back to the original config
            self.needs_restart = False
            if 'lang' in self.restart_alerts:
                self.restart_alerts.remove('lang')
            self._lang_alert.hide()
            if self._lang_sid:
                GObject.source_remove(self._lang_sid)
            self._model.undo()
            return False

        if self._lang_sid:
            GObject.source_remove(self._lang_sid)
        self._lang_sid = GObject.timeout_add(self._APPLY_TIMEOUT,
                                             self.__lang_timeout_cb,
                                             selected_langs)

    def __lang_timeout_cb(self, codes):
        self._lang_sid = 0
        try:
            self._model.set_languages_list(codes)
            self.restart_alerts.append('lang')
            self.needs_restart = True
            self._lang_alert.props.msg = self.restart_msg
            self._lang_alert.show()
        except IOError as e:
            logging.exception('Error writing i18n config %s', e)
            self.undo()
            self._lang_alert.props.msg = gettext.gettext(
                'Error writing language configuration (%s)') % e
            self._lang_alert.show()
            self.props.is_valid = False
        return False


class FilterToolItem(Gtk.ToolItem):
    def __init__(self, primary_icon, secondary_icon, default_label,
                 widget):
        Gtk.ToolItem.__init__(self)

        self.set_size_request(style.GRID_CELL_SIZE * 3, -1)

        self._widget = widget
        self._visible = False

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        self.add(grid)
        grid.show()

        self._primary_icon = Icon(icon_name=primary_icon)
        self._secondary_icon = Icon(icon_name=secondary_icon)
        self._button = Gtk.Button()
        self._button.set_image(self._primary_icon)
        self._primary_icon.show()
        self._secondary_icon.show()
        grid.attach(self._button, 0, 0, 1, 1)
        self._button.show()
        self._button.connect('clicked', self.button_cb)

        event_box = Gtk.EventBox()
        self._label_widget = Gtk.Label()
        self._label_widget.set_alignment(0.0, 0.5)
        self._label_widget.set_use_markup(True)
        self.set_widget_label(default_label)
        event_box.add(self._label_widget)
        self._label_widget.show()
        grid.attach(event_box, 1, 0, 1, 1)
        event_box.show()
        # Allow clicking on the label in addition to the button
        event_box.set_events(Gdk.EventMask.TOUCH_MASK)
        event_box.connect('touch-event', self._touch_event_cb)

    def set_widget(self, widget):
        self._widget.destroy()
        self._widget = widget
        if self._visible:
            self._widget.show()
        else:
            self._widget.hide()

    def is_visible(self):
        return self._visible

    def _touch_event_cb(self, widget, event):
        if event.type in [Gdk.EventType.TOUCH_BEGIN]:
            self.button_cb(widget)

    def button_cb(self, widget=None):
        if self._visible:
            self._widget.hide()
            self._button.set_image(self._primary_icon)
        else:
            self._widget.show()
            self._button.set_image(self._secondary_icon)
        self._visible = not self._visible

    def set_widget_label(self, label):
        size = 'x-large'
        color = style.COLOR_BLACK.get_html()
        span = '<span foreground="%s" size="%s">' % (color, size)
        self._label_widget.set_markup(span + label + '</span>')


class BlackLabel(PaletteMenuItem):
    ''' Label in palette menu item with black text on white background '''

    def __init__(self, text_label=None):
        PaletteMenuItem.__init__(self, text_label=None, text_maxlen=0)

        self.id_enter_notify_cb = self.connect('enter-notify-event',
                                               self.__enter_notify_cb)
        self.id_leave_notify_cb = self.connect('leave-notify-event',
                                               self.__leave_notify_cb)
        self.set_label(text_label)

    def set_label(self, text_label):
        text = '<span foreground="%s">' % style.COLOR_BLACK.get_html() + \
            text_label + '</span>'
        self.label.set_markup(text)

    def __enter_notify_cb(self, widget, event):
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_HIGHLIGHT.get_gdk_color())

    def __leave_notify_cb(self, widget, event):
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_WHITE.get_gdk_color())


def set_palette_list(palette_list):
    menu_item = BlackLabel(text_label='English')
    req2 = menu_item.get_preferred_size()[1]
    item_width = req2.width
    item_height = req2.height + style.DEFAULT_PADDING

    palette_width = int(Gdk.Screen.width() / 2)
    palette_height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 3

    nx = min(3, int(palette_width / item_width))
    ny = min(8, int(palette_height / item_height), len(palette_list))

    if ny >= len(palette_list):
        nx = 1
        ny = len(palette_list)
    elif ny >= (len(palette_list) + 1) / 2:
        nx = 2
        ny = int((len(palette_list) + 1) / 2)
    elif ny >= (len(palette_list) + 2) / 3:
        nx = 3
        ny = int((len(palette_list) + 2) / 3)

    grid = Gtk.Grid()
    grid.set_row_spacing(style.DEFAULT_PADDING)
    grid.set_column_spacing(0)
    grid.set_border_width(0)

    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.set_size_request(nx * item_width, ny * item_height)
    scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
    scrolled_window.add_with_viewport(grid)
    grid.show()

    x = 0
    y = 0

    for item in palette_list:
        menu_item = BlackLabel(item['label'])

        menu_item.connect('button-release-event', item['callback'], item)
        grid.attach(menu_item, x, y, 1, 1)
        x += 1
        if x == nx:
            x = 0
            y += 1

        menu_item.show()

    return scrolled_window
