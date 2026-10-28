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

from sugar4.graphics import style

from jarabe.controlpanel.sectionview import SectionView

from .model import ServiceProvidersError

APPLY_TIMEOUT = 1000


def _create_providers_list_store(items):
    gtk_list = Gtk.ListStore(str, object)
    for i in items:
        gtk_list.append((i.name, i))
    return gtk_list


class EntryWithLabel(Gtk.Box):

    def __init__(self, label_text):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, spacing=style.DEFAULT_SPACING)

        self.label = Gtk.Label(label=label_text)
        self.label.set_halign(Gtk.Align.END)
        self.label.set_valign(Gtk.Align.CENTER)
        self.append(self.label)

        self._entry = Gtk.Entry()
        self._entry.set_max_length(25)
        self._entry.set_width_chars(25)
        self.append(self._entry)

    def get_entry(self):
        return self._entry

    entry = GObject.Property(type=object, getter=get_entry)


class ModemConfiguration(SectionView):
    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._timeout_sid = 0

        self.set_margin_top(style.DEFAULT_SPACING)
        self.set_margin_bottom(style.DEFAULT_SPACING)
        self.set_margin_start(style.DEFAULT_SPACING)
        self.set_margin_end(style.DEFAULT_SPACING)
        self.set_spacing(style.DEFAULT_SPACING)

        self._label_grp = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self._combo_grp = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        scrolled_win = Gtk.ScrolledWindow()
        scrolled_win.set_policy(Gtk.PolicyType.AUTOMATIC,
                                Gtk.PolicyType.AUTOMATIC)
        scrolled_win.set_vexpand(True)
        self.append(scrolled_win)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=style.DEFAULT_SPACING)
        main_box.set_margin_top(style.DEFAULT_SPACING)
        main_box.set_margin_bottom(style.DEFAULT_SPACING)
        main_box.set_margin_start(style.DEFAULT_SPACING)
        main_box.set_margin_end(style.DEFAULT_SPACING)
        scrolled_win.set_child(main_box)

        explanation = _('You will need to provide the following information'
                        ' to set up a mobile broadband connection to a'
                        ' cellular (3G) network.')
        self._text = Gtk.Label(label=explanation)
        self._text.set_wrap(True)
        self._text.set_halign(Gtk.Align.START)
        main_box.append(self._text)

        self._upper_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=style.DEFAULT_SPACING)
        self._upper_box.set_margin_top(style.DEFAULT_SPACING)
        self._upper_box.set_margin_bottom(style.DEFAULT_SPACING)
        self._upper_box.set_margin_start(style.DEFAULT_SPACING)
        self._upper_box.set_margin_end(style.DEFAULT_SPACING)
        main_box.append(self._upper_box)

        country_store = Gtk.ListStore(str, object)
        country_store.append(['', None])

        provider_store = Gtk.ListStore(str, object)
        provider_store.append(['', None])

        plan_store = Gtk.ListStore(str, object)
        plan_store.append(['', None])

        self._country_combo = self._add_combo(country_store, _('Country:'))
        self.provider_combo = self._add_combo(provider_store, _('Provider:'))
        self.plan_combo = self._add_combo(plan_store, _('Plan:'))

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.append(separator)

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

        lower_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=style.DEFAULT_SPACING)
        lower_box.set_margin_top(style.DEFAULT_SPACING)
        lower_box.set_margin_bottom(style.DEFAULT_SPACING)
        lower_box.set_margin_start(style.DEFAULT_SPACING)
        lower_box.set_margin_end(style.DEFAULT_SPACING)
        main_box.append(lower_box)

        self._username_entry = EntryWithLabel(_('Username:'))
        self._username_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._username_entry.label)
        self._combo_grp.add_widget(self._username_entry.entry)
        lower_box.append(self._username_entry)

        self._password_entry = EntryWithLabel(_('Password:'))
        self._password_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._password_entry.label)
        self._combo_grp.add_widget(self._password_entry.entry)
        lower_box.append(self._password_entry)

        self._number_entry = EntryWithLabel(_('Number:'))
        self._number_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._number_entry.label)
        self._combo_grp.add_widget(self._number_entry.entry)
        lower_box.append(self._number_entry)

        self._apn_entry = EntryWithLabel(_('Access Point Name (APN):'))
        self._apn_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._apn_entry.label)
        self._combo_grp.add_widget(self._apn_entry.entry)
        lower_box.append(self._apn_entry)

        self._pin_entry = EntryWithLabel(_('Personal Identity Number (PIN):'))
        self._pin_entry.entry.connect('changed', self.__entry_changed_cb)
        self._label_grp.add_widget(self._pin_entry.label)
        self._combo_grp.add_widget(self._pin_entry.entry)
        lower_box.append(self._pin_entry)

        self.setup()

    def _add_combo(self, store, label_text=''):
        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.END)
        label.set_valign(Gtk.Align.CENTER)
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

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=style.DEFAULT_SPACING)
        box.append(label)
        box.append(combo)

        self._upper_box.append(box)
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
            self._username_entry.entry.set_text(plan.username or '')
            self._password_entry.entry.set_text(plan.password or '')
            self._number_entry.entry.set_text(plan.number or '')
            self._apn_entry.entry.set_text(plan.apn or '')
