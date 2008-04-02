# Copyright (C) 2008 One Laptop Per Child
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

from gettext import gettext as _

import gtk
import gobject
import hippo

from sugar.graphics import style
from sugar.graphics import iconentry
from sugar.graphics.radiotoolbutton import RadioToolButton

from view.home.activitiesring import ActivitiesRing
from view.home.activitieslist import ActivitiesList

_RING_VIEW = 0
_LIST_VIEW = 1

class HomeBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, shell):
        hippo.CanvasBox.__init__(self)

        self._shell = shell
        self._ring_view = None
        self._list_view = None
        self._enable_xo_palette = False

        self._toolbar = HomeToolbar()
        #self._toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        self._toolbar.connect('view-changed', self.__toolbar_view_changed_cb)
        self.append(hippo.CanvasWidget(widget=self._toolbar))

        self._set_view(_RING_VIEW)

    def __toolbar_view_changed_cb(self, toolbar, view):
        self._set_view(view)

    def _set_view(self, view):
        if view == _RING_VIEW:
            if self._list_view in self.get_children():
                self.remove(self._list_view)

            if self._ring_view is None:
                self._ring_view = ActivitiesRing(self._shell)
                if self._enable_xo_palette:
                    self._ring_view.enable_xo_palette()

            self.append(self._ring_view, hippo.PACK_EXPAND)

        elif view == _LIST_VIEW:
            if self._ring_view in self.get_children():
                self.remove(self._ring_view)

            if self._list_view is None:
                self._list_view = ActivitiesList()

            self.append(self._list_view, hippo.PACK_EXPAND)
        else:
            raise ValueError('Invalid view: %r' % view)

    _REDRAW_TIMEOUT = 5 * 60 * 1000 # 5 minutes

    def resume(self):
        # TODO: Do we need this?
        #if self._redraw_id is None:
        #    self._redraw_id = gobject.timeout_add(self._REDRAW_TIMEOUT,
        #                                          self._redraw_activity_ring)
        #    self._redraw_activity_ring()
        pass

    def suspend(self):
        # TODO: Do we need this?
        #if self._redraw_id is not None:
        #    gobject.source_remove(self._redraw_id)
        #    self._redraw_id = None
        pass

    def _redraw_activity_ring(self):
        # TODO: Do we need this?
        #self._donut.redraw()
        return True

    def has_activities(self):
        # TODO: Do we need this?
        #return self._donut.has_activities()
        return False

    def enable_xo_palette(self):
        self._enable_xo_palette = True
        if self._ring_view is not None:
            self._ring_view.enable_xo_palette()

    def grab_and_rotate(self):
        pass
            
    def rotate(self):
        pass

    def release(self):
        pass

class HomeToolbar(gtk.Toolbar):
    __gtype_name__ = 'SugarHomeToolbar'

    __gsignals__ = {
        'query-changed': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([str])),
        'view-changed':  (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([int]))
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self._add_separator()

        tool_item = gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self._search_entry = iconentry.IconEntry()
        self._search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'system-search')
        self._search_entry.add_clear_button()
        self._search_entry.set_width_chars(25)
        #self._search_entry.connect('activate', self._entry_activated_cb)
        #self._search_entry.connect('changed', self._entry_changed_cb)
        tool_item.add(self._search_entry)
        self._search_entry.show()

        self._add_separator(expand=True)

        ring_button = RadioToolButton(named_icon='view-radial', group=None)
        ring_button.props.label = _('Ring view')
        ring_button.props.accelerator = _('<Ctrl>R')
        ring_button.connect('toggled', self.__view_button_toggled_cb, _RING_VIEW)
        self.insert(ring_button, -1)
        ring_button.show()

        list_button = RadioToolButton(named_icon='view-list')
        list_button.props.group = ring_button
        list_button.props.label = _('List view')
        list_button.props.accelerator = _('<Ctrl>L')
        list_button.connect('toggled', self.__view_button_toggled_cb, _LIST_VIEW)
        self.insert(list_button, -1)
        list_button.show()

        self._add_separator()

    def __view_button_toggled_cb(self, button, view):
        if button.props.active:
            self.emit('view-changed', view)

    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)
        self.insert(separator, -1)
        separator.show()

