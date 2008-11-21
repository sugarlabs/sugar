# Copyright (C) 2007, One Laptop Per Child
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
import logging

import gobject
import gtk
import hippo

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton
from sugar.datastore import datastore

from jarabe.journal.listview import ListView
from jarabe.journal.collapsedentry import BaseCollapsedEntry
from jarabe.journal.journaltoolbox import SearchToolbar
from jarabe.journal.volumestoolbar import VolumesToolbar

class ObjectChooser(gtk.Window):

    __gtype_name__ = 'ObjectChooser'

    __gsignals__ = {
        'response': (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE,
                     ([int]))
    }

    def __init__(self, parent=None):
        gtk.Window.__init__(self)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)

        self._selected_object_id = None

        self.add_events(gtk.gdk.VISIBILITY_NOTIFY_MASK)
        self.connect('visibility-notify-event',
                     self.__visibility_notify_event_cb)
        self.connect('delete-event', self.__delete_event_cb)
        self.connect('key-press-event', self.__key_press_event_cb)
        if parent is not None:
            self.connect('realize', self.__realize_cb, parent)

        vbox = gtk.VBox()
        self.add(vbox)
        vbox.show()

        title_box = TitleBox()
        title_box.connect('volume-changed', self.__volume_changed_cb)
        title_box.close_button.connect('clicked',
                                       self.__close_button_clicked_cb)
        title_box.set_size_request(-1, style.GRID_CELL_SIZE)
        vbox.pack_start(title_box, expand=False)
        title_box.show()

        separator = gtk.HSeparator()
        vbox.pack_start(separator, expand=False)
        separator.show()

        self._toolbar = SearchToolbar()
        self._toolbar.connect('query-changed', self.__query_changed_cb)
        self._toolbar.set_size_request(-1, style.GRID_CELL_SIZE)
        vbox.pack_start(self._toolbar, expand=False)
        self._toolbar.show()

        self._list_view = ChooserListView()
        self._list_view.connect('entry-activated', self.__entry_activated_cb)
        vbox.pack_start(self._list_view)
        self._list_view.show()

        self._toolbar.set_volume_id(datastore.mounts()[0]['id'])
        
        width = gtk.gdk.screen_width() - style.GRID_CELL_SIZE * 2
        height = gtk.gdk.screen_height() - style.GRID_CELL_SIZE * 2        
        self.set_size_request(width, height)

    def __realize_cb(self, chooser, parent):
        self.window.set_transient_for(parent)
        # TODO: Should we disconnect the signal here?

    def __entry_activated_cb(self, list_view, entry):
        self._selected_object_id = entry.jobject.object_id
        self.emit('response', gtk.RESPONSE_ACCEPT)

    def __delete_event_cb(self, chooser, event):
        self.emit('response', gtk.RESPONSE_DELETE_EVENT)

    def __key_press_event_cb(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.emit('response', gtk.RESPONSE_DELETE_EVENT)

    def __close_button_clicked_cb(self, button):
        self.emit('response', gtk.RESPONSE_DELETE_EVENT)
        
    def get_selected_object_id(self):
        return self._selected_object_id

    def __query_changed_cb(self, toolbar, query):
        self._list_view.update_with_query(query)

    def __volume_changed_cb(self, volume_toolbar, volume_id):
        logging.debug('Selected volume: %r.' % volume_id)
        self._toolbar.set_volume_id(volume_id)

    def __visibility_notify_event_cb(self, window, event):
        logging.debug('visibility_notify_event_cb %r' % self)
        visible = event.state == gtk.gdk.VISIBILITY_FULLY_OBSCURED
        self._list_view.set_is_visible(visible)

class TitleBox(VolumesToolbar):
    __gtype_name__ = 'TitleBox'

    def __init__(self):
        VolumesToolbar.__init__(self)

        label = gtk.Label()
        label.set_markup('<b>%s</b>' % _('Choose an object'))
        label.set_alignment(0, 0.5)
        self._add_widget(label, expand=True)

        self.close_button = ToolButton(icon_name='dialog-cancel')
        self.close_button.set_tooltip(_('Close'))
        self.insert(self.close_button, -1)
        self.close_button.show()

    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

class ChooserCollapsedEntry(BaseCollapsedEntry):
    __gtype_name__ = 'ChooserCollapsedEntry'

    __gsignals__ = {
        'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE,
                            ([]))
    }

    def __init__(self):
        BaseCollapsedEntry.__init__(self)

        self.connect_after('button-release-event',
                           self.__button_release_event_cb)
        self.connect('motion-notify-event', self.__motion_notify_event_cb)

    def __button_release_event_cb(self, entry, event):
        self.emit('entry-activated')
        return True

    def __motion_notify_event_cb(self, entry, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.props.background_color = style.COLOR_PANEL_GREY.get_int()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.props.background_color = style.COLOR_WHITE.get_int()
        return False

class ChooserListView(ListView):
    __gtype_name__ = 'ChooserListView'

    __gsignals__ = {
        'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE,
                            ([object]))
    }

    def __init__(self):
        ListView.__init__(self)

    def create_entry(self):
        entry = ChooserCollapsedEntry()
        entry.connect('entry-activated', self.__entry_activated_cb)
        return entry

    def __entry_activated_cb(self, entry):
        self.emit('entry-activated', entry)

