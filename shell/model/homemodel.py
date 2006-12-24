# Copyright (C) 2006, Owen Williams.
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

import gobject
import wnck

from model.homeactivity import HomeActivity

class HomeModel(gobject.GObject):

    __gsignals__ = {
        'activity-added':   (gobject.SIGNAL_RUN_FIRST, 
                             gobject.TYPE_NONE, 
                            ([gobject.TYPE_PYOBJECT])),
        'activity-removed': (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE,
                            ([gobject.TYPE_PYOBJECT]))
    }
    
    def __init__(self, bundle_registry):
        gobject.GObject.__init__(self)

        self._activities = {}
        self._bundle_registry = bundle_registry

        screen = wnck.screen_get_default()
        screen.connect('window-opened', self._window_opened_cb)
        screen.connect('window-closed', self._window_closed_cb)
        
    def __iter__(self): 
        return iter(self._activities)
        
    def __len__(self):
        return len(self._activities)
        
    def __getitem__(self, i):
        return self._activities[i]

    def _window_opened_cb(self, screen, window):
        if window.get_window_type() == wnck.WINDOW_NORMAL:
            self._add_activity(window)

    def _window_closed_cb(self, screen, window):
        if window.get_window_type() == wnck.WINDOW_NORMAL:
            self._remove_activity(window.get_xid())
        
    def _add_activity(self, window):
        activity = HomeActivity(self._bundle_registry, window)
        self._activities[window.get_xid()] = activity
        self.emit('activity-added', activity)

    def _remove_activity(self, xid):
        if self._activities.has_key(xid):
            self.emit('activity-removed', self._activities[xid])
            del self._activities[xid]
