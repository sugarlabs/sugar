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

from sugar4.graphics import style
from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics.objectchooser import FILTER_TYPE_MIME_BY_ACTIVITY

from jarabe.journal.listview import BaseListView
from jarabe.journal.listmodel import ListModel
from jarabe.journal.journaltoolbox import MainToolbox
from jarabe.journal.volumestoolbar import VolumesToolbar
from jarabe.model import bundleregistry

from jarabe.journal.iconview import IconView

# Inject CSS for modal background
provider = Gtk.CssProvider()
css = b".modal-bg { background-color: %s; }" % style.COLOR_BLACK.get_html().encode('utf-8')
provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class ObjectChooser(Gtk.Window):

    __gtype_name__ = 'ObjectChooser'

    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self, parent=None, what_filter='', filter_type=None,
                 show_preview=False):
        super().__init__()
        self.set_decorated(False)
        self.set_modal(True)

        self._selected_object_id = None
        self._show_preview = show_preview

        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self.__key_press_event_cb)
        self.add_controller(key_controller)

        if parent is None:
            logging.warning('ObjectChooser: No parent window specified')
            # Fall back to main sugar window as transient parent
            from jarabe.model import shell as _shell
            shell_model = _shell.get_model()
            if shell_model and shell_model.get_active_window():
                self.set_transient_for(shell_model.get_active_window())
        else:
            self.set_transient_for(parent)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.add_css_class('modal-bg')
        # Margin instead of border_width
        vbox.set_margin_start(style.LINE_WIDTH)
        vbox.set_margin_end(style.LINE_WIDTH)
        vbox.set_margin_top(style.LINE_WIDTH)
        vbox.set_margin_bottom(style.LINE_WIDTH)

        self.set_child(vbox)
        vbox.set_visible(True)

        title_box = TitleBox(what_filter, filter_type)
        title_box.connect('volume-changed', self.__volume_changed_cb)
        title_box.close_button.connect('clicked',
                                       self.__close_button_clicked_cb)
        title_box.set_size_request(-1, style.GRID_CELL_SIZE)
        vbox.append(title_box)
        title_box.set_visible(True)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.append(separator)
        separator.set_visible(True)

        self._toolbar = MainToolbox(default_what_filter=what_filter,
                                    default_filter_type=filter_type)
        self._toolbar.connect('query-changed', self.__query_changed_cb)
        self._toolbar.set_size_request(-1, style.GRID_CELL_SIZE)
        vbox.append(self._toolbar)
        self._toolbar.set_visible(True)

        if not self._show_preview:
            self._list_view = ChooserListView(self._toolbar)
            self._list_view.connect('entry-activated',
                                    self.__entry_activated_cb)
            self._list_view.connect('clear-clicked', self.__clear_clicked_cb)
            self._list_view.set_vexpand(True)
            vbox.append(self._list_view)
            self._list_view.set_visible(True)
        else:
            self._icon_view = IconView(self._toolbar)
            self._icon_view.connect('entry-activated',
                                    self.__entry_activated_cb)
            self._icon_view.connect('clear-clicked', self.__clear_clicked_cb)
            self._icon_view.set_vexpand(True)
            vbox.append(self._icon_view)
            self._icon_view.set_visible(True)

        display = Gdk.Display.get_default()
        screen_width, screen_height = 800, 600
        if display:
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                geo = monitors.get_item(0).get_geometry()
                screen_width = geo.width - style.GRID_CELL_SIZE * 2
                screen_height = geo.height - style.GRID_CELL_SIZE * 2
        self.set_default_size(screen_width, screen_height)

        self._toolbar.update_filters('/', what_filter, filter_type)

        self.set_focus(self._toolbar.search_entry)
        self.connect('unmap', self.__visibility_notify_event_cb)
        self.connect('map', self.__map_cb)
        self.connect('close-request', self.__close_request_cb)
        self.connect('realize', self.__realize_cb)
        self.connect('unrealize', self.__unrealize_cb)

    def __realize_cb(self, widget):
        from jarabe.model import shell as _shell
        _shell.get_model().push_modal()

    def __unrealize_cb(self, widget):
        from jarabe.model import shell as _shell
        _shell.get_model().pop_modal()

    def __entry_activated_cb(self, list_view, uid):
        self._selected_object_id = uid
        self.emit('response', Gtk.ResponseType.ACCEPT)

    def __key_press_event_cb(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            self.emit('response', Gtk.ResponseType.DELETE_EVENT)
            return True
        return False

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

    def __visibility_notify_event_cb(self, widget):
        logging.debug('visibility_notify_event_cb %r', self)
        visible = self.get_mapped()
        if not self._show_preview:
            self._list_view.set_is_visible(visible)
        else:
            self._icon_view.set_is_visible(visible)

    def __map_cb(self, widget):
        if not self._show_preview:
            self._list_view.set_is_visible(True)
        else:
            self._icon_view.set_is_visible(True)

    def __close_request_cb(self, window):
        self.emit('response', Gtk.ResponseType.DELETE_EVENT)
        return True

    def __clear_clicked_cb(self, list_view):
        self._toolbar.clear_query()


class TitleBox(Gtk.Box):
    __gtype_name__ = 'TitleBox'

    def __init__(self, what_filter='', filter_type=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self._children = []

        label = Gtk.Label()
        title = _('Choose an object')
        if filter_type == FILTER_TYPE_MIME_BY_ACTIVITY:
            registry = bundleregistry.get_registry()
            bundle = registry.get_bundle(what_filter)
            if bundle is not None:
                title = _('Choose an object to open with %s activity') % \
                    bundle.get_name()

        label.set_markup('<b>%s</b>' % title)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        self._add_widget(label, expand=True)

        self.close_button = ToolButton(icon_name='dialog-cancel')
        self.close_button.set_tooltip(_('Close'))
        self._add_widget(self.close_button)
        self.close_button.set_visible(True)

    def _add_widget(self, widget, expand=False):
        if expand:
            widget.set_hexpand(True)

        self.append(widget)
        self._children.append(widget)
        widget.set_visible(True)


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
        
        click_controller = Gtk.GestureClick()
        click_controller.connect('released', self.__button_release_event_cb)
        self.tree_view.add_controller(click_controller)

    def _can_clear_query(self):
        return self._toolbar.is_filter_changed()

    def _favorite_clicked_cb(self, cell, path):
        pass

    def create_palette(self, x, y):
        # We don't want show the palette in the object chooser
        pass

    def __button_release_event_cb(self, gesture, n_press, x, y):
        pos = self.tree_view.get_path_at_pos(int(x), int(y))
        if pos is None:
            return False

        path, column_, x_, y_ = pos
        uid = self.tree_view.get_model()[path][ListModel.COLUMN_UID]
        self.emit('entry-activated', uid)

        return False
