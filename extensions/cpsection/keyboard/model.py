# Copyright (C) 2007, 2008 One Laptop Per Child
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
import gobject
import gconf


GRP_NAME = 'grp' # The XKB name for group switch options

LAYOUTS_KEY = '/desktop/sugar/peripherals/keyboard/layouts'
OPTIONS_KEY = '/desktop/sugar/peripherals/keyboard/options'
MODEL_KEY = '/desktop/sugar/peripherals/keyboard/model'

class XKB(gobject.GObject):
    def __init__(self, display):
        gobject.GObject.__init__(self)
        
        self._engine = xklavier.Engine(display)
        self._configreg = xklavier.ConfigRegistry(self._engine)
        self._configreg.load(False)
        self._configrec = xklavier.ConfigRec()
        self._configrec.get_from_server(self._engine)
	
        self._gconf_client = gconf.client_get_default()

    def _populate_one(self, c_reg, item, store):
        store.append([item.get_description(), item.get_name()])

    def _populate_two(self, c_reg, item, subitem, store):
        layout = item.get_name()
        if subitem:
            desc = '%s, %s' % (subitem.get_description(), item.get_description())
            variant = subitem.get_name()
        else:
            desc = 'Default layout, %s' % item.get_description()
            variant = ''
        
        store.append([desc, ('%s(%s)' % (layout, variant))])

    def get_models(self):
        models = []
        self._configreg.foreach_model(self._populate_one, models)
        models.sort()
        return models

    def get_languages(self):
        languages = []
        self._configreg.foreach_language(self._populate_one, languages)
        languages.sort()
        return languages

    def get_layouts_for_language(self, language):
        layouts = []
        self._configreg.foreach_language_variant(language, self._populate_two, layouts)
        layouts.sort()
        return layouts

    def get_options_grp(self):
        options = []
        self._configreg.foreach_option(GRP_NAME, self._populate_one, options)
        options.sort()
        return options

    def get_current_model(self):
        model = self._gconf_client.get_string(MODEL_KEY)
        if model:
            return model
        else:
            return self._configrec.get_model()

    def get_current_layouts(self):
        layouts = self._gconf_client.get_list(LAYOUTS_KEY, 'string')
        if layouts:
            return layouts
        
        layouts = self._configrec.get_layouts()
        variants = self._configrec.get_variants()

        ret = []
        i = 0
        for layout in layouts:
            if len(variants) <= i or variants[i] == '':
                ret.append('%s(%s)' % (layout, ''))
            else:
                ret.append('%s(%s)' % (layout, variants[i]))
            i += 1

        return ret

    def get_current_option_grp(self):
        options = self._gconf_client.get_list(OPTIONS_KEY, 'string')
        
        if not options:
            options = self._configrec.get_options()

        for option in options:
            if option.startswith(GRP_NAME):
                return option
        
        return None
    
    def get_max_layouts(self):
        return self._engine.get_max_num_groups()
