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

import os
import logging
import xml.etree.ElementTree as ET
import gi
gi.require_version('Xkl', '1.0')
from gi.repository import Xkl
from gi.repository import Gio

from jarabe.config import data_path

_GROUP_NAME = 'grp'  # The XKB name for group switch options

_KEYBOARD_DIR = 'org.sugarlabs.peripherals.keyboard'
_LAYOUTS_KEY = 'layouts'
_OPTIONS_KEY = 'options'
_MODEL_KEY = 'model'
_EVDEV_XML_PATH = '/usr/share/X11/xkb/rules/evdev.xml'


class KeyboardManager(object):

    def __init__(self, display):
        self._settings = Gio.Settings.new(_KEYBOARD_DIR)
        self._engine = None
        self._configrec = None

        if display is not None:
            try:
                self._engine = Xkl.Engine.get_instance(display)
                self._configrec = Xkl.ConfigRec()
                self._configrec.get_from_server(self._engine)
            except Exception:
                logging.exception('Could not initialize Xkl engine')
                self._engine = None
                self._configrec = None

        self._models = []
        self._languages = {}
        self._layouts_for_lang = {}
        self._options = []
        self._load_xkb_registry()

    def _load_xkb_registry(self):
        lang_names = {}
        iso_file = os.path.join(data_path, 'ISO-639-2_utf-8.txt')
        if os.path.exists(iso_file):
            try:
                with open(iso_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split('|')
                        if len(parts) >= 4:
                            eng_name = parts[3].split(';')[0].strip()
                            if parts[0]:
                                lang_names[parts[0]] = eng_name
                            if parts[1]:
                                lang_names[parts[1]] = eng_name
            except Exception:
                logging.exception('Failed to parse ISO-639-2 file')

        if not os.path.exists(_EVDEV_XML_PATH):
            return

        try:
            tree = ET.parse(_EVDEV_XML_PATH)
            root = tree.getroot()

            for elem in root.iter():
                if elem.tag.startswith('{'):
                    elem.tag = elem.tag.split('}', 1)[1]

            model_list = root.find('modelList')
            if model_list is not None:
                for model_node in model_list.findall('model'):
                    config = model_node.find('configItem')
                    if config is not None:
                        name_node = config.find('name')
                        desc_node = config.find('description')
                        if name_node is not None and desc_node is not None:
                            self._models.append([desc_node.text, name_node.text])
            self._models.sort()

            layout_list = root.find('layoutList')
            if layout_list is not None:
                for layout_node in layout_list.findall('layout'):
                    config = layout_node.find('configItem')
                    if config is not None:
                        layout_name = config.find('name')
                        layout_desc = config.find('description')
                        if layout_name is not None and layout_desc is not None:
                            l_name = layout_name.text
                            l_desc = layout_desc.text

                            lang_list = config.find('languageList')
                            lang_codes = []
                            if lang_list is not None:
                                for lang_node in lang_list.findall('iso639Id'):
                                    lang_codes.append(lang_node.text)

                            variants = [[l_desc, '%s()' % l_name]]

                            variant_list = layout_node.find('variantList')
                            if variant_list is not None:
                                for var_node in variant_list.findall('variant'):
                                    var_config = var_node.find('configItem')
                                    if var_config is not None:
                                        v_name = var_config.find('name')
                                        v_desc = var_config.find('description')
                                        if v_name is not None and v_desc is not None:
                                            variants.append([
                                                '%s, %s' % (v_desc.text, l_desc),
                                                '%s(%s)' % (l_name, v_name.text)
                                            ])

                            for lang in lang_codes:
                                desc = lang_names.get(lang, lang.upper())
                                self._languages[lang] = desc
                                if lang not in self._layouts_for_lang:
                                    self._layouts_for_lang[lang] = []
                                self._layouts_for_lang[lang].extend(variants)

            for lang in self._layouts_for_lang:
                self._layouts_for_lang[lang].sort()

            option_list = root.find('optionList')
            if option_list is not None:
                for group in option_list.findall('group'):
                    config = group.find('configItem')
                    if config is not None:
                        name_node = config.find('name')
                        if name_node is not None and name_node.text == _GROUP_NAME:
                            for opt in group.findall('option'):
                                opt_config = opt.find('configItem')
                                if opt_config is not None:
                                    opt_name = opt_config.find('name')
                                    opt_desc = opt_config.find('description')
                                    if opt_name is not None and opt_desc is not None:
                                        self._options.append([opt_desc.text, opt_name.text])
            self._options.sort()

        except Exception:
            logging.exception('Failed to parse evdev.xml')

    def get_models(self):
        """Return list of supported keyboard models"""
        return self._models

    def get_languages(self):
        """Return list of supported keyboard languages"""
        languages = [[desc, code] for code, desc in self._languages.items()]
        languages.sort()
        return languages

    def get_layouts_for_language(self, language):
        """Return list of supported keyboard layouts for a given language"""
        return self._layouts_for_lang.get(language, [])

    def get_options_group(self):
        """Return list of supported options for switching keyboard group"""
        return self._options

    def get_current_model(self):
        """Return the enabled keyboard model"""
        model = self._settings.get_string(_MODEL_KEY)
        if not model:
            if self._configrec is not None:
                model = self._configrec.model
                self.set_model(model)
            else:
                model = 'pc105'
        return model

    def get_current_layouts(self):
        """Return the enabled keyboard layouts with variants"""
        layouts = self._settings.get_strv(_LAYOUTS_KEY)
        if layouts:
            return layouts

        if self._configrec is not None:
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
        return ['us']

    def get_current_option_group(self):
        """Return the enabled option for switching keyboard group"""
        options = self._settings.get_strv(_OPTIONS_KEY)

        if not options:
            if self._configrec is not None:
                options = self._configrec.options
                self.set_option_group(options)
            else:
                options = []

        for option in options:
            if option.startswith(_GROUP_NAME):
                return option

        return None

    def get_max_layouts(self):
        """Return the maximum number of layouts supported simultaneously"""
        if self._engine is not None:
            return self._engine.get_max_num_groups()
        return 4

    def set_model(self, model):
        """Sets the supplied keyboard model"""
        if model is None or not model:
            return
        self._settings.set_string(_MODEL_KEY, model)
        if self._configrec is not None:
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
        if self._configrec is not None:
            self._configrec.set_options(options)
            self._configrec.activate(self._engine)

    def set_layouts(self, layouts):
        """Sets the supplied keyboard layouts (with variants)"""
        if layouts is None or not layouts:
            return

        self._settings.set_strv(_LAYOUTS_KEY, layouts)

        if self._configrec is not None:
            layouts_list = []
            variants_list = []
            for layout in layouts:
                layouts_list.append(layout.split('(')[0])
                variants_list.append(layout.split('(')[1][:-1])
            self._configrec.set_layouts(layouts_list)
            self._configrec.set_variants(variants_list)
            self._configrec.activate(self._engine)
