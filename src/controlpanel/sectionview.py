# Copyright (C) 2008, OLPC
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

import gobject
import gtk
import gettext

_ = lambda msg: gettext.dgettext('sugar', msg)

class SectionView(gtk.VBox):
    __gproperties__ = {
        'valid-section' : (bool, None, None, True,
                           gobject.PARAM_READWRITE)
        }

    def __init__(self):
        gtk.VBox.__init__(self)
        self.valid_section = True
        self.restart = False
        self.restart_alerts = []
        self._restart_msg = _('Changes require a sugar restart to take effect.')

    def do_set_property(self, pspec, value):
        if pspec.name == 'valid-section':
            if self.valid_section != value:
                self.valid_section = value

    def do_get_property(self, pspec):
        if pspec.name == 'valid-section':
            return self.valid_section

    def undo(self):
        '''Undo here the changes that have been made in this section.'''
        pass
