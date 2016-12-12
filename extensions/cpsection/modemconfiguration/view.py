# -*- encoding: utf-8 -*-
# Copyright (C) 2009 Paraguay Educa, Martin Abente
# Copyright (C) 2010 Andrés Ambrois
# Copyright (C) 2012 Ajay Garg
# Copyright (C) 2013 Miguel González
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

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from sugar3.graphics import style

from jarabe.controlpanel.sectionview import SectionView


from .model import ServiceProvidersError

APPLY_TIMEOUT = 1000


def _create_providers_list_store(items):
    gtk_list = Gtk.ListStore(str, object)
    for i in items:
        gtk_list.append((i.name, i))
    return gtk_list


class EntryWithLabel(Gtk.HBox):
    __gtype_name__ = 'SugarEntryWithLabel'

    def __init__(self, label_text):
        Gtk.HBox.__init__(self, spacing=style.DEFAULT_SPACING)

        self.label = Gtk.Label(label=label_text)
        self.label.modify_fg(Gtk.StateType.NORMAL,
                             style.COLOR_SELECTION_GREY.get_gdk_color())
        self.label.set_alignment(1, 0.5)
        self.pack_start(self.label, False, True, 0)
        self.label.show()

        self._entry = Gtk.Entry()
        self._entry.set_max_length(25)
        self._entry.set_width_chars(25)
        self.pack_start(self._entry, False, True, 0)
        self._entry.show()

    def get_entry(self):
        return self._entry

    entry = GObject.property(type=object, getter=get_entry)


class ModemConfiguration(SectionView):
    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._timeout_sid = 0

        self.set_border_width(style.DEFAULT_SPACING)
        self.set_spacing(style.DEFAULT_SPACING)

        self._label_grp = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self._combo_grp = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        scrolled_win = Gtk.ScrolledWindow()
        scrolled_win.set_policy(Gtk.PolicyType.AUTOMATIC,
                                Gtk.PolicyType.AUTOMATIC)
        self.add(scrolled_win)
        scrolled_win.show()

        main_box = Gtk.VBox(spacing=style.DEFAULT_SPACING)
        main_box.set_border_width(style.DEFAULT_SPACING)
        scrolled_win.add_with_viewport(main_box)
        main_box.show()

        explanation = _('You will need to provide the following information'
                        ' to set up a mobile broadband connection to a'
                        ' cellular (3G) network.')
        self._text = Gtk.Label(label=explanation)
        self._text.set_line_wrap(True)
        self._text.set_alignment(0, 0)
        main_box.pack_start(self._text, True, False, 0)
        self._text.show()

        self._upper_box = Gtk.VBox(spacing=style.DEFAULT_SPACING)
        self._upper_box.set_border_width(style.DEFAULT_SPACING)
        main_box.pack_start(self._upper_box, True, False, 0)
        self._upper_box.show()

        country_store = Gtk.ListStore(str, object)
        country_store.append([])

        provider_store = Gtk.ListStore(str, object)
        provider_store.append([])

        plan_store = Gtk.ListStore(str, object)
        plan_store.append([])

        self._country_combo = self._add_combo(country_store, _('Country:'))
        self.provider_combo = self._add_combo(provider_store, _('Provider:'))
        self.plan_combo = self._add_combo(plan_store, _('Plan:'))

        separator = Gtk.HSeparator()
        main_box.pack_start(separator, True, False, 0)
        separator.show()

        try:
            self.service_providers = self._model.ServiceProviders()
        except ServiceProvidersError:
            self.service_providers = None
        else:
            countries = self.service_providers.get_countries()
            providers = self.service_providers.get_providers()
            plans = self.service_providers.get_plans()

            current_country = self.service_providers.get_country()
            current_provider = self.service_providers.get_provider()
            current_plan = self.service_providers.get_plan()

            country_store = _create_providers_list_store(countries)
            provider_store = _create_providers_list_store(providers)
            plan_store = _create_providers_list_store(plans)

            self._country_combo.set_model(country_store)
            self._country_combo.set_active(current_country.idx)

            self.provider_combo.set_model(provider_store)
            self.provider_combo.set_active(current_provider.idx)

            self.plan_combo.set_model(plan_store)
            self.plan_combo.set_active(current_plan.idx)

            self._country_combo.connect("changed", self._country_selected_cb)
            self.provider_combo.connect("changed", self._provider_selected_cb)
            self.plan_combo.connect("changed", self._plan_selected_cb)

        lower_box = Gtk.VBox(spacing=style.DEFAULT_SPACING)
        lower_box.set_border_width(style.DEFAULT_SPACING)
        main_box.pack_start(lower_box, True, False, 0)
        lower_box.show()

        self._username_entry = EntryWithLabel(_('Username:'))
        self._username_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._username_entry.label)
        self._combo_grp.add_widget(self._username_entry.entry)
        lower_box.pack_start(self._username_entry, False, True, 0)
        self._username_entry.show()

        self._password_entry = EntryWithLabel(_('Password:'))
        self._password_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._password_entry.label)
        self._combo_grp.add_widget(self._password_entry.entry)
        lower_box.pack_start(self._password_entry, False, True, 0)
        self._password_entry.show()

        self._number_entry = EntryWithLabel(_('Number:'))
        self._number_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._number_entry.label)
        self._combo_grp.add_widget(self._number_entry.entry)
        lower_box.pack_start(self._number_entry, False, True, 0)
        self._number_entry.show()

        self._apn_entry = EntryWithLabel(_('Access Point Name (APN):'))
        self._apn_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._apn_entry.label)
        self._combo_grp.add_widget(self._apn_entry.entry)
        lower_box.pack_start(self._apn_entry, False, True, 0)
        self._apn_entry.show()

        self._pin_entry = EntryWithLabel(_('Personal Identity Number (PIN):'))
        self._pin_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._pin_entry.label)
        self._combo_grp.add_widget(self._pin_entry.entry)
        lower_box.pack_start(self._pin_entry, False, True, 0)
        self._pin_entry.show()

        self.setup()

    def _add_combo(self, store, label_text=''):
        label = Gtk.Label(label_text)
        label.set_alignment(1, 0.5)
        self._label_grp.add_widget(label)

        combo = Gtk.ComboBox()
        self._combo_grp.add_widget(combo)
        combo.set_model(store)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("max-width-chars", 25)
        renderer_text.set_property("width-chars", 25)
        renderer_text.set_property("xalign", 0.5)
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, "text", 0)

        box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        box.pack_start(label, False, True, 0)
        label.show()
        box.pack_start(combo, False, True, 0)
        combo.show()

        self._upper_box.pack_start(box, False, True, 0)
        box.show()
        return combo

    def undo(self):
        self._model.undo()

    def _populate_entry(self, entrywithlabel, text):
        """Populate an entry with text, without triggering its 'changed'
        handler."""
        entry = entrywithlabel.entry
        entry.handler_block_by_func(self.__entry_changed_cb)
        entry.set_text(text)
        entry.handler_unblock_by_func(self.__entry_changed_cb)

    def setup(self):
        self._model.get_modem_settings(self._got_modem_settings_cb)

    def _got_modem_settings_cb(self, settings):
        self._populate_entry(self._username_entry,
                             settings.get('username', ''))
        self._populate_entry(self._number_entry, settings.get('number', ''))
        self._populate_entry(self._apn_entry, settings.get('apn', ''))
        self._populate_entry(self._password_entry,
                             settings.get('password', ''))
        self._populate_entry(self._pin_entry, settings.get('pin', ''))

    def __entry_changed_cb(self, widget, data=None):
        if self._timeout_sid:
            GLib.source_remove(self._timeout_sid)
        self._timeout_sid = GLib.timeout_add(APPLY_TIMEOUT,
                                             self.__timeout_cb)

    def __timeout_cb(self):
        self._timeout_sid = 0
        settings = {}
        settings['username'] = self._username_entry.entry.get_text()
        settings['password'] = self._password_entry.entry.get_text()
        settings['number'] = self._number_entry.entry.get_text()
        settings['apn'] = self._apn_entry.entry.get_text()
        settings['pin'] = self._pin_entry.entry.get_text()
        self._model.set_modem_settings(settings)

    def _country_selected_cb(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            country = model[tree_iter][1]

            self.service_providers.set_country(country.idx)
            providers = self.service_providers.get_providers()
            store = _create_providers_list_store(providers)
            current = self.service_providers.get_provider()
            self.provider_combo.set_model(store)
            self.provider_combo.set_active(current.idx)

    def _provider_selected_cb(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            provider = model[tree_iter][1]

            self.service_providers.set_provider(provider.idx)
            plans = self.service_providers.get_plans()
            store = _create_providers_list_store(plans)
            current = self.service_providers.get_plan()
            self.plan_combo.set_model(store)
            self.plan_combo.set_active(current.idx)

    def _plan_selected_cb(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            plan = model[tree_iter][1]

            self.service_providers.set_plan(plan.idx)
            plan = self.service_providers.get_plan()
            self._username_entry.entry.set_text(plan.username)
            self._password_entry.entry.set_text(plan.password)
            self._number_entry.entry.set_text(plan.number)
            self._apn_entry.entry.set_text(plan.apn)
