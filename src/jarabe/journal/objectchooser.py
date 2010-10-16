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
import wnck

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton

from jarabe.journal.listview import BaseListView
from jarabe.journal.listmodel import ListModel
from jarabe.journal.journaltoolbox import SearchToolbar
from jarabe.journal.volumestoolbar import VolumesToolbar


class ObjectChooser(gtk.Window):

    __gtype_name__ = 'ObjectChooser'

    __gsignals__ = {
        'response': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([int])),
    }

    def __init__(self, parent=None, what_filter=''):
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

        if parent is None:
            logging.warning('ObjectChooser: No parent window specified')
        else:
            self.connect('realize', self.__realize_cb, parent)

            screen = wnck.screen_get_default()
            screen.connect('window-closed', self.__window_closed_cb, parent)

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

        self._toolbar.set_mount_point('/')

        width = gtk.gdk.screen_width() - style.GRID_CELL_SIZE * 2
        height = gtk.gdk.screen_height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)

        if what_filter:
            self._toolbar.set_what_filter(what_filter)

    def __realize_cb(self, chooser, parent):
        self.window.set_transient_for(parent)
        # TODO: Should we disconnect the signal here?

    def __window_closed_cb(self, screen, window, parent):
        if window.get_xid() == parent.xid:
            self.destroy()

    def __entry_activated_cb(self, list_view, uid):
        self._selected_object_id = uid
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

    def __volume_changed_cb(self, volume_toolbar, mount_point):
        logging.debug('Selected volume: %r.', mount_point)
        self._toolbar.set_mount_point(mount_point)

    def __visibility_notify_event_cb(self, window, event):
        logging.debug('visibility_notify_event_cb %r', self)
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


class ChooserListView(BaseListView):
    __gtype_name__ = 'ChooserListView'

    __gsignals__ = {
        'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE,
                            ([str])),
    }

    def __init__(self):
        BaseListView.__init__(self)

        self.cell_icon.props.show_palette = False
        self.tree_view.props.hover_selection = True

        self.tree_view.connect('button-release-event',
                               self.__button_release_event_cb)

    def __entry_activated_cb(self, entry):
        self.emit('entry-activated', entry)

    def __button_release_event_cb(self, tree_view, event):
        if event.window != tree_view.get_bin_window():
            return False

        pos = tree_view.get_path_at_pos(int(event.x), int(event.y))
        if pos is None:
            return False

        path, column_, x_, y_ = pos
        uid = tree_view.get_model()[path][ListModel.COLUMN_UID]
        self.emit('entry-activated', uid)

        return False
