# Copyright (C) 2013 Sugar Labs
# Copyright (C) 2009 OLPC
# Author: Sayamindu Dasgupta <sayamindu@laptop.org>
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
#

from gi.repository import Xkl
from gi.repository import Gio

_GROUP_NAME = 'grp'  # The XKB name for group switch options

_KEYBOARD_DIR = 'org.sugarlabs.peripherals.keyboard'
_LAYOUTS_KEY = 'layouts'
_OPTIONS_KEY = 'options'
_MODEL_KEY = 'model'


class KeyboardManager(object):
    def __init__(self, display):
        self._engine = Xkl.Engine.get_instance(display)
        self._configregistry = Xkl.ConfigRegistry.get_instance(self._engine)
        self._configregistry.load(False)
        self._configrec = Xkl.ConfigRec()
        self._configrec.get_from_server(self._engine)

        self._settings = Gio.Settings(_KEYBOARD_DIR)

    def _populate_one(self, config_registry, item, store):
        store.append([item.get_description(), item.get_name()])

    def _populate_two(self, config_registry, item, subitem, store):
        layout = item.get_name()
        if subitem:
            description = '%s, %s' % (subitem.get_description(),
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
        self._configregistry.foreach_language_variant(language,
                                                      self._populate_two,
                                                      layouts)
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
        model = self._settings.get_string(_MODEL_KEY)
        if not model:
            model = self._configrec.model
            self.set_model(model)
        return model

    def get_current_layouts(self):
        """Return the enabled keyboard layouts with variants"""
        layouts = self._settings.get_strv(_LAYOUTS_KEY)
        if layouts:
            return layouts

        layouts = self._configrec.layouts
        variants = self._configrec.variants

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
        options = self._settings.get_strv(_OPTIONS_KEY)

        if not options:
            options = self._configrec.options
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
        self._settings.set_string(_MODEL_KEY, model)
        self._configrec.set_model(model)
        self._configrec.activate(self._engine)

    def set_option_group(self, option_group):
        """Sets the supplied option for switching keyboard group"""
        # XXX: Merge, not overwrite previous options
        if not option_group:
            options = ['']
        elif isinstance(option_group, list):
            options = option_group
        else:
            options = [option_group]

        self._settings.set_strv(_OPTIONS_KEY, options)
        self._configrec.set_options(options)
        self._configrec.activate(self._engine)

    def set_layouts(self, layouts):
        """Sets the supplied keyboard layouts (with variants)"""
        if layouts is None or not layouts:
            return

        self._settings.set_strv(_LAYOUTS_KEY, layouts)

        layouts_list = []
        variants_list = []
        for layout in layouts:
            layouts_list.append(layout.split('(')[0])
            variants_list.append(layout.split('(')[1][:-1])
        self._configrec.set_layouts(layouts_list)
        self._configrec.set_variants(variants_list)
        self._configrec.activate(self._engine)
