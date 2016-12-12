# Copyright (C) 2008, OLPC
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


from gi.repository import GObject
from gi.repository import Gtk
from gettext import gettext as _


class SectionView(Gtk.VBox):
    __gtype_name__ = 'SugarSectionView'

    __gsignals__ = {
        'request-close': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'add-alert': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'set-toolbar-sensitivity': (GObject.SignalFlags.RUN_FIRST, None,
                                    (GObject.TYPE_BOOLEAN,)),
    }

    __gproperties__ = {
        'is_valid': (bool, None, None, True, GObject.PARAM_READWRITE),
        'is_cancellable': (bool, None, None, True, GObject.PARAM_READWRITE),
        'is_deferrable': (bool, None, None, True, GObject.PARAM_READWRITE),
    }

    _APPLY_TIMEOUT = 1000

    def __init__(self):
        Gtk.VBox.__init__(self)
        self._is_valid = True
        self._is_cancellable = True
        self._is_deferrable = True
        self.auto_close = False
        self.needs_restart = False
        self.restart_alerts = []
        self.restart_msg = _('Changes require restart')
        self.show_restart_alert = True

    def do_set_property(self, pspec, value):
        if pspec.name == 'is-valid':
            if self._is_valid != value:
                self._is_valid = value
        if pspec.name == 'is-cancellable':
            if self._is_cancellable != value:
                self._is_cancellable = value
        if pspec.name == 'is-deferrable':
            if self._is_deferrable != value:
                self._is_deferrable = value

    def do_get_property(self, pspec):
        if pspec.name == 'is-valid':
            return self._is_valid
        if pspec.name == 'is-cancellable':
            return self._is_cancellable
        if pspec.name == 'is-deferrable':
            return self._is_deferrable

    def undo(self):
        """Undo here the changes that have been made in this section."""
        pass
if hasattr(SectionView, 'set_css_name'):
    SectionView.set_css_name('cpanelsectionview')
