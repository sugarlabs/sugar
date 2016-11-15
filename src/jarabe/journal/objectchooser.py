# Copyright (C) 2007, One Laptop Per Child
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

from gettext import gettext as _
import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Wnck

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.objectchooser import FILTER_TYPE_MIME_BY_ACTIVITY

from jarabe.journal.listview import BaseListView
from jarabe.journal.listmodel import ListModel
from jarabe.journal.journaltoolbox import MainToolbox
from jarabe.journal.volumestoolbar import VolumesToolbar
from jarabe.model import bundleregistry

from jarabe.journal.iconview import IconView


class ObjectChooser(Gtk.Window):

    __gtype_name__ = 'ObjectChooser'

    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self, parent=None, what_filter='', filter_type=None,
                 show_preview=False):
        Gtk.Window.__init__(self)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)

        self._selected_object_id = None
        self._show_preview = show_preview

        self.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect('visibility-notify-event',
                     self.__visibility_notify_event_cb)
        self.connect('delete-event', self.__delete_event_cb)
        self.connect('key-press-event', self.__key_press_event_cb)

        if parent is None:
            logging.warning('ObjectChooser: No parent window specified')
        else:
            self.connect('realize', self.__realize_cb, parent)

            screen = Wnck.Screen.get_default()
            screen.connect('window-closed', self.__window_closed_cb, parent)

        vbox = Gtk.VBox()
        self.add(vbox)
        vbox.show()

        title_box = TitleBox(what_filter, filter_type)
        title_box.connect('volume-changed', self.__volume_changed_cb)
        title_box.close_button.connect('clicked',
                                       self.__close_button_clicked_cb)
        title_box.set_size_request(-1, style.GRID_CELL_SIZE)
        vbox.pack_start(title_box, False, True, 0)
        title_box.show()

        separator = Gtk.HSeparator()
        vbox.pack_start(separator, False, True, 0)
        separator.show()

        self._toolbar = MainToolbox(default_what_filter=what_filter,
                                    default_filter_type=filter_type)
        self._toolbar.connect('query-changed', self.__query_changed_cb)
        self._toolbar.set_size_request(-1, style.GRID_CELL_SIZE)
        vbox.pack_start(self._toolbar, False, True, 0)
        self._toolbar.show()

        if not self._show_preview:
            self._list_view = ChooserListView(self._toolbar)
            self._list_view.connect('entry-activated',
                                    self.__entry_activated_cb)
            self._list_view.connect('clear-clicked', self.__clear_clicked_cb)
            vbox.pack_start(self._list_view, True, True, 0)
            self._list_view.show()
        else:
            self._icon_view = IconView(self._toolbar)
            self._icon_view.connect('entry-activated',
                                    self.__entry_activated_cb)
            self._icon_view.connect('clear-clicked', self.__clear_clicked_cb)
            vbox.pack_start(self._icon_view, True, True, 0)
            self._icon_view.show()

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)

        self._toolbar.update_filters('/', what_filter, filter_type)

    def __realize_cb(self, chooser, parent):
        self.get_window().set_transient_for(parent)
        # TODO: Should we disconnect the signal here?

    def __window_closed_cb(self, screen, window, parent):
        if window.get_xid() == parent.get_xid():
            self.destroy()

    def __entry_activated_cb(self, list_view, uid):
        self._selected_object_id = uid
        self.emit('response', Gtk.ResponseType.ACCEPT)

    def __delete_event_cb(self, chooser, event):
        self.emit('response', Gtk.ResponseType.DELETE_EVENT)

    def __key_press_event_cb(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.emit('response', Gtk.ResponseType.DELETE_EVENT)

    def __close_button_clicked_cb(self, button):
        self.emit('response', Gtk.ResponseType.DELETE_EVENT)

    def get_selected_object_id(self):
        return self._selected_object_id

    def __query_changed_cb(self, toolbar, query):
        if not self._show_preview:
            self._list_view.update_with_query(query)
        else:
            self._icon_view.update_with_query(query)

    def __volume_changed_cb(self, volume_toolbar, mount_point):
        logging.debug('Selected volume: %r.', mount_point)
        self._toolbar.set_mount_point(mount_point)

    def __visibility_notify_event_cb(self, window, event):
        logging.debug('visibility_notify_event_cb %r', self)
        visible = event.get_state() == Gdk.VisibilityState.FULLY_OBSCURED
        if not self._show_preview:
            self._list_view.set_is_visible(visible)
        else:
            self._icon_view.set_is_visible(visible)

    def __clear_clicked_cb(self, list_view):
        self._toolbar.clear_query()


class TitleBox(VolumesToolbar):
    __gtype_name__ = 'TitleBox'

    def __init__(self, what_filter='', filter_type=None):
        VolumesToolbar.__init__(self)

        label = Gtk.Label()
        title = _('Choose an object')
        if filter_type == FILTER_TYPE_MIME_BY_ACTIVITY:
            registry = bundleregistry.get_registry()
            bundle = registry.get_bundle(what_filter)
            if bundle is not None:
                title = _('Choose an object to open with %s activity') % \
                    bundle.get_name()

        label.set_markup('<b>%s</b>' % title)
        label.set_alignment(0, 0.5)
        self._add_widget(label, expand=True)

        self.close_button = ToolButton(icon_name='dialog-cancel')
        self.close_button.set_tooltip(_('Close'))
        self.insert(self.close_button, -1)
        self.close_button.show()

    def _add_widget(self, widget, expand=False):
        tool_item = Gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()


class ChooserListView(BaseListView):
    __gtype_name__ = 'ChooserListView'

    __gsignals__ = {
        'entry-activated': (GObject.SignalFlags.RUN_FIRST,
                            None,
                            ([str])),
    }

    def __init__(self, toolbar):
        BaseListView.__init__(self, None)
        self._toolbar = toolbar

        self.tree_view.props.hover_selection = True

        self.tree_view.connect('button-release-event',
                               self.__button_release_event_cb)

    def _can_clear_query(self):
        return self._toolbar.is_filter_changed()

    def __entry_activated_cb(self, entry):
        self.emit('entry-activated', entry)

    def _favorite_clicked_cb(self, cell, path):
        pass

    def create_palette(self, x, y):
        # We don't want show the palette in the object chooser
        pass

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
