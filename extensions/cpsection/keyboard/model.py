# Copyright (C) 2009 OLPC
# Author: Sayamindu Dasgupta <sayamindu@laptop.org>
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

import xklavier
import gconf


_GROUP_NAME = 'grp'  # The XKB name for group switch options

_LAYOUTS_KEY = '/desktop/sugar/peripherals/keyboard/layouts'
_OPTIONS_KEY = '/desktop/sugar/peripherals/keyboard/options'
_MODEL_KEY = '/desktop/sugar/peripherals/keyboard/model'


class KeyboardManager(object):
    def __init__(self, display):
        self._engine = xklavier.Engine(display)
        self._configregistry = xklavier.ConfigRegistry(self._engine)
        self._configregistry.load(False)
        self._configrec = xklavier.ConfigRec()
        self._configrec.get_from_server(self._engine)

        self._gconf_client = gconf.client_get_default()

    def _populate_one(self, config_registry, item, store):
        store.append([item.get_description(), item.get_name()])

    def _populate_two(self, config_registry, item, subitem, store):
        layout = item.get_name()
        if subitem:
            description = '%s, %s' % (subitem.get_description(), \
                                            item.get_description())
            variant = subitem.get_name()
        else:
            description = 'Default layout, %s' % item.get_description()
            variant = ''

        store.append([description, ('%s(%s)' % (layout, variant))])

    def get_models(self):
        """Return list of supported keyboard models"""
        models = []
        self._configregistry.foreach_model(self._populate_one, models)
        models.sort()
        return models

    def get_languages(self):
        """Return list of supported keyboard languages"""
        languages = []
        self._configregistry.foreach_language(self._populate_one, languages)
        languages.sort()
        return languages

    def get_layouts_for_language(self, language):
        """Return list of supported keyboard layouts for a given language"""
        layouts = []
        self._configregistry.foreach_language_variant(language, \
                                                self._populate_two, layouts)
        layouts.sort()
        return layouts

    def get_options_group(self):
        """Return list of supported options for switching keyboard group"""
        options = []
        self._configregistry.foreach_option(_GROUP_NAME, self._populate_one,
                                            options)
        options.sort()
        return options

    def get_current_model(self):
        """Return the enabled keyboard model"""
        model = self._gconf_client.get_string(_MODEL_KEY)
        if model:
            return model
        else:
            model = self._configrec.get_model()
            self.set_model(model)
            return model

    def get_current_layouts(self):
        """Return the enabled keyboard layouts with variants"""
        layouts = self._gconf_client.get_list(_LAYOUTS_KEY, gconf.VALUE_STRING)
        if layouts:
            return layouts

        layouts = self._configrec.get_layouts()
        variants = self._configrec.get_variants()

        layout_list = []
        i = 0
        for layout in layouts:
            if len(variants) <= i or variants[i] == '':
                layout_list.append('%s(%s)' % (layout, ''))
            else:
                layout_list.append('%s(%s)' % (layout, variants[i]))
            i += 1

        self.set_layouts(layout_list)

        return layout_list

    def get_current_option_group(self):
        """Return the enabled option for switching keyboard group"""
        options = self._gconf_client.get_list(_OPTIONS_KEY, gconf.VALUE_STRING)

        if not options:
            options = self._configrec.get_options()
            self.set_option_group(options)

        for option in options:
            if option.startswith(_GROUP_NAME):
                return option

        return None

    def get_max_layouts(self):
        """Return the maximum number of layouts supported simultaneously"""
        return self._engine.get_max_num_groups()

    def set_model(self, model):
        """Sets the supplied keyboard model"""
        if model is None or not model:
            return
        self._gconf_client.set_string(_MODEL_KEY, model)
        self._configrec.set_model(model)
        self._configrec.activate(self._engine)

    def set_option_group(self, option_group):
        """Sets the supplied option for switching keyboard group"""
        #XXX: Merge, not overwrite previous options
        if not option_group:
            options = ['']
        elif isinstance(option_group, list):
            options = option_group
        else:
            options = [option_group]
        self._gconf_client.set_list(_OPTIONS_KEY, gconf.VALUE_STRING, options)
        self._configrec.set_options(options)
        self._configrec.activate(self._engine)

    def set_layouts(self, layouts):
        """Sets the supplied keyboard layouts (with variants)"""
        if layouts is None or not layouts:
            return
        self._gconf_client.set_list(_LAYOUTS_KEY, gconf.VALUE_STRING, layouts)
        layouts_list = []
        variants_list = []
        for layout in layouts:
            layouts_list.append(layout.split('(')[0])
            variants_list.append(layout.split('(')[1][:-1])

        self._configrec.set_layouts(layouts_list)
        self._configrec.set_variants(variants_list)
        self._configrec.activate(self._engine)
