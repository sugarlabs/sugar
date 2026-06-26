# Copyright (C) 2009, Tomeu Vizoso
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

import logging
from gettext import gettext as _
import time

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GdkPixbuf

from sugar4.graphics import style
from sugar4.graphics.alert import ConfirmationAlert
from sugar4.graphics.icon import Icon, CellRendererIcon
from sugar4 import util
from sugar4 import profile
from sugar4.graphics.palettewindow import TreeViewInvoker

from jarabe.journal.listmodel import ListModel
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import model
from jarabe.journal import misc
from jarabe.journal import journalwindow

UPDATE_INTERVAL = 300
PROJECT_BUNDLE_ID = 'org.sugarlabs.Project'


class TreeView(Gtk.TreeView):
    __gtype_name__ = 'JournalTreeView'

    __gsignals__ = {
        'detail-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object])),
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
        'choose-project': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object])),
    }

    def __init__(self, journalactivity):
        super().__init__()

        self._journalactivity = journalactivity
        self.icon_activity_column = None
        self.buddies_columns = []

        self._invoker = TreeViewInvoker()
        self._invoker.attach_treeview(self)

        self.set_headers_visible(False)
        self.set_enable_search(False)

    def connect_to_scroller(self, scrolled):
        # scrolling detector logic
        scrolled.connect('scroll-start', self._scroll_start_cb)
        scrolled.connect('scroll-end', self._scroll_end_cb)

    def _scroll_start_cb(self, event):
        self._invoker.detach()

    def _scroll_end_cb(self, event):
        self._invoker.attach_treeview(self)

    def create_palette(self, path, column):
        if self._journalactivity is None:
            # in the objectchooser we don't show palettes
            return None

        if self._journalactivity.get_list_view().is_dragging():
            return None

        palette = None

        if column == self.icon_activity_column:
            metadata = self.get_model().get_metadata(path)

            palette = ObjectPalette(self._journalactivity, metadata,
                                    detail=True)
            palette.connect('detail-clicked', self.__detail_clicked_cb)
            palette.connect('volume-error', self.__volume_error_cb)
            palette.connect('choose-project', self.__choose_project_cb)

        elif column in self.buddies_columns:
            tree_model = self.get_model()
            iterator = tree_model.get_iter(path)

            for column_index in [ListModel.COLUMN_BUDDY_1,
                                 ListModel.COLUMN_BUDDY_2,
                                 ListModel.COLUMN_BUDDY_3]:
                if column == self.buddies_columns[column_index -
                                                  ListModel.COLUMN_BUDDY_1]:
                    buddy_value = tree_model.do_get_value(
                        iterator,
                        column_index
                    )
                    if buddy_value:
                        nick, xo_color = buddy_value
                        palette = BuddyPalette(
                            (nick,
                             xo_color.to_string()))

        return palette

    def __detail_clicked_cb(self, palette, uid):
        self.emit('detail-clicked', uid)

    def __volume_error_cb(self, palette, message, severity):
        self.emit('volume-error', message, severity)

    def __choose_project_cb(self, palette, metadata_to_copy):
        self.emit('choose-project', metadata_to_copy)

    def __del__(self):
        self._invoker.detach()


class BaseListView(Gtk.Box):
    __gtype_name__ = 'JournalBaseListView'

    __gsignals__ = {
        'clear-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
        'detail-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object])),
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, journalactivity, enable_multi_operations=False):
        self._query = {}
        self._journalactivity = journalactivity
        self._enable_multi_operations = enable_multi_operations
        self._model = None
        self._progress_bar = None
        self._last_progress_bar_pulse = None
        self._scroll_position = 0.
        self._projects_view_active = False
        
        self._current_child = None

        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.connect('map', self.__map_cb)
        self.connect('unmap', self.__unmap_cb)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self._scrolled_window.set_vexpand(True)
        self.append(self._scrolled_window)
        self._current_child = self._scrolled_window
        self._scrolled_window.set_visible(True)

        self.tree_view = TreeView(self._journalactivity)
        self.tree_view.connect('detail-clicked', self.__detail_clicked_cb)
        self.tree_view.connect('volume-error', self.__volume_error_cb)
        selection = self.tree_view.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        self.tree_view.props.fixed_height_mode = True
        self._scrolled_window.set_child(self.tree_view)
        self.tree_view.set_visible(True)

        self.cell_title = None
        self.cell_icon = None
        self._title_column = None
        
        self._add_columns()
        self.enable_drag_and_copy()

        # Auto-update stuff
        self._fully_obscured = True
        self._updates_disabled = False
        self._dirty = False
        self._refresh_idle_handler = None
        self._update_dates_timer = None
        self._backup_selected = None

        model.created.connect(self.__model_created_cb)
        model.updated.connect(self.__model_updated_cb)
        model.deleted.connect(self.__model_deleted_cb)
        
    def _switch_child(self, new_child):
        if self._current_child == new_child:
            return
        if self._current_child:
            self.remove(self._current_child)
        self.append(new_child)
        self._current_child = new_child

    def enable_drag_and_copy(self):
        self._drag_source = Gtk.DragSource.new()
        self._drag_source.set_actions(Gdk.DragAction.COPY)
        self._drag_source.connect('prepare', self.__drag_prepare_cb)
        self._drag_source.connect('drag-begin', self.__drag_begin_cb)
        self.tree_view.add_controller(self._drag_source)

    def disable_drag_and_copy(self):
        if hasattr(self, '_drag_source'):
            self.tree_view.remove_controller(self._drag_source)
            del self._drag_source
    def __drag_prepare_cb(self, drag_source, x, y):
        path_info = self.tree_view.get_path_at_pos(int(x), int(y))
        if not path_info:
            return None
        path, column, cell_x, cell_y = path_info
        self._drag_path = path

        row = self.tree_view.get_model()[path]
        uid = row[ListModel.COLUMN_UID]
        
        providers = []
        
        bytes1 = GLib.Bytes.new(uid.encode('utf-8'))
        providers.append(Gdk.ContentProvider.new_for_bytes("journal-object-id", bytes1))
        
        file_path = model.get_file(uid)
        if file_path:
            uri = 'file://' + file_path + '\r\n'
            bytes2 = GLib.Bytes.new(uri.encode('utf-8'))
            providers.append(Gdk.ContentProvider.new_for_bytes("text/uri-list", bytes2))
            
        return Gdk.ContentProvider.new_union(providers)

    def __drag_begin_cb(self, drag_source, drag):
        if hasattr(self, '_drag_path'):
            row = self.tree_view.get_model()[self._drag_path]
            try:
                texture = Gdk.Texture.new_from_filename(row[ListModel.COLUMN_ICON])
                drag_source.set_icon(texture, 0, 0)
            except GLib.Error:
                pass
        self._is_dragging = True

    def __model_created_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def __model_updated_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def __model_deleted_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def _is_new_item_visible(self, object_id):
        """Check if the created item is part of the currently selected view"""
        if 'project_id' in self._query:
            # TODO:  Would be best to check if the object_id is in the project.
            #        But there is only ever 1 project listview, so it should
            #        not be very costly.
            return True
        if not self._query.get('mountpoints', None):
            return None
        if self._query['mountpoints'] == ['/']:
            return not object_id.startswith('/')
        return object_id.startswith(self._query['mountpoints'][0])

    def _add_columns(self):
        if self._enable_multi_operations:
            cell_select = Gtk.CellRendererToggle()
            cell_select.connect('toggled', self.__cell_select_toggled_cb)
            cell_select.props.activatable = True
            cell_select.props.xpad = style.DEFAULT_PADDING
            
            # It might be, if so we just ignore it.
            if hasattr(cell_select.props, 'indicator_size'):
                cell_select.props.indicator_size = style.zoom(26)

            column = Gtk.TreeViewColumn()
            column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
            column.props.fixed_width = style.GRID_CELL_SIZE
            column.pack_start(cell_select, True)
            column.set_cell_data_func(cell_select, self.__select_set_data_cb)
            self.tree_view.append_column(column)

        cell_favorite = CellRendererFavorite()
        cell_favorite.connect('clicked', self._favorite_clicked_cb)

        self._fav_column = Gtk.TreeViewColumn()
        self._fav_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self._fav_column.props.fixed_width = cell_favorite.props.width
        self._fav_column.pack_start(cell_favorite, True)
        self._fav_column.set_cell_data_func(
            cell_favorite, self.__favorite_set_data_cb)
        self.tree_view.append_column(self._fav_column)

        self.cell_icon = CellRendererActivityIcon()

        column = Gtk.TreeViewColumn()
        self.tree_view.icon_activity_column = column
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        column.props.fixed_width = self.cell_icon.props.width
        column.pack_start(self.cell_icon, True)
        column.add_attribute(self.cell_icon, 'file-name',
                             ListModel.COLUMN_ICON)
        column.add_attribute(self.cell_icon, 'xo-color',
                             ListModel.COLUMN_ICON_COLOR)
        self.tree_view.append_column(column)
        self.icon_activity_column = column

        self.cell_title = Gtk.CellRendererText()
        self.cell_title.props.ellipsize = style.ELLIPSIZE_MODE_DEFAULT
        self.cell_title.props.ellipsize_set = True

        self._title_column = Gtk.TreeViewColumn()
        self._title_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self._title_column.props.expand = True
        self._title_column.props.clickable = True
        self._title_column.pack_start(self.cell_title, True)
        self._title_column.add_attribute(self.cell_title, 'markup',
                                         ListModel.COLUMN_TITLE)
        self.tree_view.append_column(self._title_column)

        for column_index in [ListModel.COLUMN_BUDDY_1,
                             ListModel.COLUMN_BUDDY_2,
                             ListModel.COLUMN_BUDDY_3]:

            buddies_column = Gtk.TreeViewColumn()
            buddies_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
            self.tree_view.append_column(buddies_column)

            cell_icon = CellRendererBuddy(column_index=column_index)
            buddies_column.pack_start(cell_icon, True)
            buddies_column.props.fixed_width += cell_icon.props.width
            buddies_column.add_attribute(cell_icon, 'buddy', column_index)
            buddies_column.set_cell_data_func(cell_icon,
                                              self.__buddies_set_data_cb)
            self.tree_view.buddies_columns.append(buddies_column)

        cell_progress = Gtk.CellRendererProgress()
        cell_progress.props.ypad = style.GRID_CELL_SIZE / 4
        buddies_column.pack_start(cell_progress, True)
        buddies_column.add_attribute(cell_progress, 'value',
                                     ListModel.COLUMN_PROGRESS)
        buddies_column.set_cell_data_func(cell_progress,
                                          self.__progress_data_cb)

        cell_text = Gtk.CellRendererText()
        cell_text.props.xalign = 1

        # Measure the required width for a date in the form of "10 hours, 10
        # minutes ago"
        timestamp = time.time() - 10 * 60 - 10 * 60 * 60
        date = util.timestamp_to_elapsed_string(timestamp)
        date_width = self._get_width_for_string(date)

        self.sort_column = Gtk.TreeViewColumn()
        self.sort_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self.sort_column.props.fixed_width = date_width
        self.sort_column.set_alignment(1)
        self.sort_column.props.resizable = True
        self.sort_column.props.clickable = True
        self.sort_column.pack_start(cell_text, True)
        self.sort_column.add_attribute(cell_text, 'text',
                                       ListModel.COLUMN_TIMESTAMP)
        self.tree_view.append_column(self.sort_column)

    def _get_width_for_string(self, text):
        # Add some extra margin
        text = text + 'aaaaa'

        widget = Gtk.Label(label='')
        context = widget.get_pango_context()
        layout = Pango.Layout(context)
        layout.set_text(text, len(text))
        width, height_ = layout.get_pixel_size()
        return width

    def do_unroot(self):
        if self._model is not None:
            self._model.stop()

    def __buddies_set_data_cb(self, column, cell, tree_model,
                              tree_iter, data):
        buddy = tree_model.do_get_value(tree_iter, cell._model_column_index)
        if buddy is None:
            cell.props.visible = False
            return
        # FIXME workaround for pygobject bug, see
        # https://bugzilla.gnome.org/show_bug.cgi?id=689277
        #
        # add_attribute with 'buddy' attribute in the cell should take
        # care of setting it.
        cell.props.buddy = buddy

        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        cell.props.visible = progress >= 100

    def __progress_data_cb(self, column, cell, tree_model,
                           tree_iter, data):
        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        cell.props.visible = progress < 100

    def __favorite_set_data_cb(self, column, cell, tree_model,
                               tree_iter, data):
        favorite = tree_model[tree_iter][ListModel.COLUMN_FAVORITE]
        if favorite:
            cell.props.xo_color = profile.get_color()
        else:
            cell.props.xo_color = None

    def _favorite_clicked_cb(self, cell, path):
        row = self._model[path]
        iterator = self._model.get_iter(path)
        metadata = model.get(row[ListModel.COLUMN_UID])
        if not model.is_editable(metadata):
            return
        if metadata.get('keep', 0) == '1':
            metadata['keep'] = '0'
            self._model[iterator][ListModel.COLUMN_FAVORITE] = '0'
        else:
            metadata['keep'] = '1'
            self._model[iterator][ListModel.COLUMN_FAVORITE] = '1'

        self.tree_view.queue_draw()

        # HACK for https://bugs.sugarlabs.org/ticket/4944
        # Icon does not update automatically if there is only one journal entry
        if len(self._model.get_all_ids()) == 1:
            self._do_refresh()

    def __select_set_data_cb(self, column, cell, tree_model, tree_iter,
                             data):
        uid = tree_model[tree_iter][ListModel.COLUMN_UID]
        if uid is None:
            return
        cell.props.active = self._model.is_selected(uid)

    def __cell_select_toggled_cb(self, cell, path):
        tree_iter = self._model.get_iter(path)
        uid = self._model[tree_iter][ListModel.COLUMN_UID]
        self._model.set_selected(uid, not cell.get_active())
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def update_with_query(self, query_dict):
        logging.debug('ListView.update_with_query')

        if 'order_by' not in query_dict:
            query_dict['order_by'] = ['+timestamp']
        if query_dict['order_by'] != self._query.get('order_by'):
            property_ = query_dict['order_by'][0][1:]
            cell_text = self.sort_column.get_cells()[0]
            self.sort_column.set_attributes(cell_text,
                                            text=getattr(
                                                ListModel, 'COLUMN_' +
                                                property_.upper(),
                                                ListModel.COLUMN_TIMESTAMP))
        self._query = query_dict
        self.refresh(new_query=True)

    def refresh(self, new_query=False):
        logging.debug('ListView.refresh query %r', self._query)
        self._stop_progress_bar()
        
        # Cursor setting
        root = self.get_root()
        if root:
            root.set_cursor(Gdk.Cursor.new_from_name("wait", None))
            Gdk.Display.get_default().sync()
        GLib.idle_add(self._do_refresh, new_query)

    def _do_refresh(self, new_query=False):
        if self._model is not None:
            if new_query:
                self._backup_selected = None
            else:
                self._backup_selected = self._model.get_selected_items()
            self._model.stop()
        self._dirty = False

        self._model = ListModel(self._query)
        self._model.connect('ready', self.__model_ready_cb)
        self._model.connect('progress', self.__model_progress_cb)
        self._model.setup(self.__model_updated_cb)
        
        root = self.get_root()
        if root:
            root.set_cursor(None)
            Gdk.Display.get_default().sync()

    def __model_ready_cb(self, tree_model):
        self._stop_progress_bar()

        self._scroll_position = self.tree_view.props.vadjustment.props.value
        logging.debug('ListView.__model_ready_cb %r', self._scroll_position)

        # if the selection was preserved, restore it
        if self._backup_selected is not None:
            tree_model.restore_selection(self._backup_selected)
            self.emit('selection-changed', len(self._backup_selected))

        # Cannot set it up earlier because will try to access the model
        # and it needs to be ready.
        self.tree_view.set_model(self._model)

        self.tree_view.props.vadjustment.props.value = self._scroll_position

        if len(tree_model) == 0:
            if self._query.get('project_id', None):
                self._show_message(_('Your project is empty'))
            else:
                documents_path = model.get_documents_path()
                if self._is_query_empty():
                    if self._query['mountpoints'] == ['/']:
                        self._show_message(_('Your Journal is empty'))
                    elif documents_path and self._query['mountpoints'] == \
                            [documents_path]:
                        self._show_message(_('Your documents folder is empty'))
                    else:
                        self._show_message(_('The device is empty'))
                else:
                    show_message_text = _('No matching entries')
                    if self.get_projects_view_active():
                        show_message_text = _('No Projects')

                    self._show_message(
                        show_message_text,
                        show_clear_query=self._can_clear_query())
        else:
            self._clear_message()

    def _can_clear_query(self):
        return True

    def __map_cb(self, widget):
        logging.debug('ListView.__map_cb %r', self._scroll_position)
        self.tree_view.props.vadjustment.props.value = self._scroll_position
        self.set_is_visible(True)

    def __unmap_cb(self, widget):
        self._scroll_position = self.tree_view.props.vadjustment.props.value
        logging.debug('ListView.__unmap_cb %r', self._scroll_position)
        self.set_is_visible(False)

    def _is_query_empty(self):
        # FIXME: This is a hack, we shouldn't have to update this every time
        # a new search term is added.
        return not (self._query.get('query') or self._query.get('mime_type') or
                    self._query.get('keep') or self._query.get('mtime') or
                    self._query.get('activity'))

    def __model_progress_cb(self, tree_model):
        if self._progress_bar is None:
            self._start_progress_bar()

        if time.time() - self._last_progress_bar_pulse > 0.05:
            self._progress_bar.pulse()
            self._last_progress_bar_pulse = time.time()

    def _start_progress_bar(self):
        alignment = Gtk.Box()
        alignment.set_halign(Gtk.Align.CENTER)
        alignment.set_valign(Gtk.Align.CENTER)
        
        self._switch_child(alignment)
        alignment.set_visible(True)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.props.pulse_step = 0.01
        self._last_progress_bar_pulse = time.time()
        alignment.append(self._progress_bar)
        self._progress_bar.set_visible(True)

    def _stop_progress_bar(self):
        if self._progress_bar is None:
            return
        self._switch_child(self._scrolled_window)
        self._progress_bar = None

    def _show_message(self, message, show_clear_query=False):
        background_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # Apply CSS background color
        background_box.add_css_class('bg-white')
        
        self._switch_child(background_box)

        alignment = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        alignment.set_halign(Gtk.Align.CENTER)
        alignment.set_valign(Gtk.Align.CENTER)
        alignment.set_vexpand(True)
        background_box.append(alignment)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        alignment.append(box)

        icon = Icon(pixel_size=style.LARGE_ICON_SIZE,
                    icon_name='activity-journal',
                    stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                    fill_color=style.COLOR_TRANSPARENT.get_svg())
        box.append(icon)
        icon.set_visible(True)

        label = Gtk.Label()
        color = style.COLOR_BUTTON_GREY.get_html()
        label.set_markup('<span weight="bold" color="%s">%s</span>' % (
            color, GLib.markup_escape_text(message)))
        box.append(label)
        label.set_visible(True)

        if not self.get_projects_view_active():
            if show_clear_query:
                button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                button_box.set_halign(Gtk.Align.CENTER)
                box.append(button_box)
                button_box.set_visible(True)

                button = Gtk.Button()
                button.connect('clicked', self.__clear_button_clicked_cb)

                # Build icon+label child.
                btn_icon = Icon(icon_name='dialog-cancel', pixel_size=style.SMALL_ICON_SIZE)
                box_btn = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                box_btn.append(btn_icon)
                box_btn.append(Gtk.Label(label=_('Clear search')))
                button.set_child(box_btn)

                button_box.append(button)
                button.set_visible(True)

        background_box.set_visible(True)

    def __clear_button_clicked_cb(self, button):
        self.emit('clear-clicked')

    def _clear_message(self):
        if self._current_child == self._scrolled_window:
            return
        self._switch_child(self._scrolled_window)
        self._scrolled_window.set_visible(True)

    def update_dates(self):
        if not self.tree_view.get_realized():
            return
        self.tree_view.queue_draw()

    def _set_dirty(self):
        if self._fully_obscured or self._updates_disabled:
            self._dirty = True
        else:
            self.refresh()

    def disable_updates(self):
        self._updates_disabled = True

    def enable_updates(self):
        self._updates_disabled = False
        if self._dirty:
            self.refresh()

    def set_is_visible(self, visible):
        if visible != self._fully_obscured:
            return

        logging.debug('canvas_visibility_notify_event_cb %r', visible)
        if visible:
            self._fully_obscured = False
            if self._dirty:
                self.refresh()
            if self._update_dates_timer is None:
                logging.debug('Adding date updating timer')
                self._update_dates_timer = \
                    GLib.timeout_add_seconds(UPDATE_INTERVAL,
                                             self.__update_dates_timer_cb)
        else:
            self._fully_obscured = True
            if self._update_dates_timer is not None:
                logging.debug('Remove date updating timer')
                GLib.source_remove(self._update_dates_timer)
                self._update_dates_timer = None

    def __update_dates_timer_cb(self):
        self.update_dates()
        return True

    def get_model(self):
        return self._model

    def select_all(self):
        self.get_model().select_all()
        self.tree_view.queue_draw()
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def select_none(self):
        self.get_model().select_none()
        self.tree_view.queue_draw()
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def __detail_clicked_cb(self, palette, uid):
        self.emit('detail-clicked', uid)

    def __volume_error_cb(self, palette, message, severity):
        self.emit('volume-error', message, severity)

    def get_projects_view_active(self):
        return self._query.get('activity') == PROJECT_BUNDLE_ID


class ListView(BaseListView):
    __gtype_name__ = 'JournalListView'

    __gsignals__ = {
        'title-edit-started': (GObject.SignalFlags.RUN_FIRST, None,
                               ([])),
        'title-edit-finished': (GObject.SignalFlags.RUN_FIRST, None,
                                ([str, object])),
        'title-edit-canceled': (GObject.SignalFlags.RUN_FIRST, None,
                                ([])),
        'project-view-activate': (GObject.SignalFlags.RUN_FIRST, None,
                                  ([object])),
    }

    def __init__(self, journalactivity, enable_multi_operations=False):
        BaseListView.__init__(self, journalactivity, enable_multi_operations)
        self._is_dragging = False

        click_controller = Gtk.GestureClick()
        click_controller.connect('released', self.__button_release_event_cb)
        self.tree_view.add_controller(click_controller)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self._key_press_event_cb)
        self.tree_view.add_controller(key_controller)

        self.cell_title.connect('edited', self.__cell_title_edited_cb)
        self.cell_title.connect('editing-canceled', self.__editing_canceled_cb)

        self.cell_icon.connect('clicked', self.__icon_clicked_cb)

        cell_detail = CellRendererDetail()
        cell_detail.connect('clicked', self.__detail_cell_clicked_cb)

        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        column.props.fixed_width = cell_detail.props.width
        column.pack_start(cell_detail, True)
        self.tree_view.append_column(column)

    def _key_press_event_cb(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        
        path_col = self.tree_view.get_cursor()
        if not path_col or path_col[0] is None:
            return False
            
        path, col = path_col

        if self.tree_view.has_focus():
            if keyname == 'Return':
                self.__icon_clicked_cb(None, path)
                return True

            if state & Gdk.ModifierType.CONTROL_MASK and keyname == 'F2':
                row = self.tree_view.get_model()[path]
                metadata = model.get(row[ListModel.COLUMN_UID])
                self.cell_title.props.editable = model.is_editable(metadata)

                if self.cell_title.props.editable:
                    self.emit('title-edit-started')

                column = self.tree_view.get_column(3)
                self.tree_view.set_cursor_on_cell(path, column, self.cell_title,
                                         start_editing=True)
                return True

            if keyname == 'Right':
                tree_iter = self._model.get_iter(path)
                uid = self._model[tree_iter][ListModel.COLUMN_UID]
                self.emit('detail-clicked', uid)
                return True

            if keyname in ('Delete', 'KP_Delete'):
                row = self.tree_view.get_model()[path]
                uid = row[ListModel.COLUMN_UID]
                metadata = model.get(uid)
                if model.is_editable(metadata):
                    model.delete(uid)
                return True

            if keyname == 'Escape':
                self.emit('clear-clicked')
                return True
                
        return False

    def is_dragging(self):
        return self._is_dragging

    def __button_release_event_cb(self, gesture, n_press, x, y):
        try:
            if self._is_dragging:
                return
        finally:
            self._is_dragging = False

        pos = self.tree_view.get_path_at_pos(int(x), int(y))
        if pos is None:
            return

        path, column, x_, y_ = pos
        if column != self._title_column:
            return

        row = self.tree_view.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        self.cell_title.props.editable = model.is_editable(metadata)
        if self.cell_title.props.editable:
            self.emit('title-edit-started')

        self.tree_view.set_cursor_on_cell(path, column, self.cell_title,
                                     start_editing=True)

    def __detail_cell_clicked_cb(self, cell, path):
        row = self.tree_view.get_model()[path]
        self.emit('detail-clicked', row[ListModel.COLUMN_UID])

    def __icon_clicked_cb(self, cell, path):
        row = self.tree_view.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        if metadata['activity'] == PROJECT_BUNDLE_ID:
            self.emit('project-view-activate', metadata)
            return
        misc.resume(metadata,
                    alert_window=journalwindow.get_journal_window())

    def __cell_title_edited_cb(self, cell, path, new_text):
        iterator = self._model.get_iter(path)
        old_text = self._model[iterator][ListModel.COLUMN_TITLE]

        if old_text != new_text and (new_text == '' or new_text.isspace()):
            alert = ConfirmationAlert()
            alert.props.title = _('Empty title')
            alert.props.msg = _('The title is usually not left empty')
            alert.connect('response', self._cell_title_alert_response_cb, path, new_text)
            journalwindow.get_journal_window().add_alert(alert)
            alert.set_visible(True)
            return

        if old_text != new_text:
            self._model[iterator][ListModel.COLUMN_TITLE] = new_text
            self.emit('title-edit-finished', new_text, path)

    def _cell_title_alert_response_cb(self, alert, response_id, path, new_text):
        journalwindow.get_journal_window().remove_alert(alert)

        iterator = self._model.get_iter(path)
        if response_id == Gtk.ResponseType.OK:
            self._model[iterator][ListModel.COLUMN_TITLE] = new_text
            self.emit('title-edit-finished', new_text, path)

    def __editing_canceled_cb(self, cell):
        self.cell_title.props.editable = False
        self.emit('title-edit-canceled')


class CellRendererFavorite(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererFavorite'

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'emblem-favorite'
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE


class CellRendererDetail(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererDetail'

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'go-right'
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE
        self.props.stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.prelit_stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.prelit_fill_color = style.COLOR_BLACK.get_svg()


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererActivityIcon'

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE


class CellRendererBuddy(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererBuddy'

    def __init__(self, column_index):
        CellRendererIcon.__init__(self)

        self.props.width = style.STANDARD_ICON_SIZE
        self.props.height = style.STANDARD_ICON_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

        self._model_column_index = column_index
        self.nick = None

    def set_buddy(self, buddy):
        if not buddy:
            self.props.icon_name = None
            self.nick = None
        else:
            self.nick, xo_color = buddy
            self.props.icon_name = 'computer-xo'
            self.props.xo_color = xo_color

    buddy = GObject.Property(type=object, setter=set_buddy)
