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

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import style
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
    
    def __init__(self, shell):
        gobject.GObject.__init__(self)
        self._activities = []
        self._shell = shell
        
        shell.connect('activity-opened', self.__activity_opened_cb)
        shell.connect('activity-closed', self.__activity_closed_cb)
        
    def __iter__(self): 
        return iter(self._activities)
        
    def __len__(self):
        return len(self._activities)
        
    def __getitem__(self, i):
        return self._activities[i]
        
    def __activity_opened_cb(self, model, activity):
        self._add_activity(activity)

    def __activity_closed_cb(self, model, activity):
        self._remove_activity(activity)
        
    def _add_activity(self, activity):
        h_activity = HomeActivity(activity)
        self._activities.append(h_activity)
        self.emit('activity-added', h_activity)

    def _remove_activity(self, activity):
        i = 0
        for h_activity in self._activities:
            if h_activity.get_id() == activity.get_id():
                self.emit('activity-removed', self._activities[i])
                del self._activities[i]
                return
            i += 1
