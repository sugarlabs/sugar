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
from gettext import ngettext
import time

import cairo
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import PangoCairo
from gi.repository import GdkPixbuf

from sugar3.graphics import style
from sugar3.graphics.alert import ConfirmationAlert
from sugar3.graphics.icon import CellRendererIcon
from sugar3.graphics.scrollingdetector import ScrollingDetector
from sugar3 import util
from sugar3 import profile
from sugar3.graphics.palettewindow import TreeViewInvoker

from jarabe.journal.basejournalview import BaseJournalView
from jarabe.journal.listmodel import ListModel
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import model
from jarabe.journal import misc
from jarabe.journal import timeline
from jarabe.journal import journalwindow


UPDATE_INTERVAL = 300
PROJECT_BUNDLE_ID = 'org.sugarlabs.Project'

# Matches sugar-artwork's GTK theme color @define-color row_odd #D5D5D5.
_CARD_BORDER_RGB = (0xd5 / 255., 0xd5 / 255., 0xd5 / 255.)

# Gtk.TreeView renders cell renderers independently per column, with no
# way to paint one continuous card across them, so the card feel here
# comes from row height and framing instead.
_ROW_HEIGHT = style.zoom(96)


# ---------------------------------------------------------------------------
# Timeline day/band/spine drawing lives in timeline.py, shared with
# gridview.py.
# ---------------------------------------------------------------------------

_TIMELINE_COLUMN_WIDTH = timeline.COLUMN_WIDTH
_TIMELINE_DAY_INK = timeline.DAY_INK
_TIMELINE_BAND_INK = timeline.BAND_INK

_TIMELINE_DAY_FONT = timeline.DAY_TITLE_SIZE

_TIMELINE_DAY_PAD = style.zoom(14)
_TIMELINE_BAND_FONT = timeline.BAND_NAME_SIZE
_TIMELINE_BAND_PAD = style.zoom(15)

# A sliver is still a row: hiding it would need a Gtk.TreeModelFilter
# around ListModel, which would break row index == entry index that
# objectchooser.py and projectview.py both depend on.
_CARD_PEEK_HEIGHT = style.zoom(10)
_CARD_PEEK_GAP = style.zoom(6)
_FOLD_SLIVER = _CARD_PEEK_HEIGHT + _CARD_PEEK_GAP

# Gtk.TreeView floors every row at the tree view's own expander-size
# plus its vertical-separator, whatever a renderer asks for -- 16px
# default, 24 under sugar-100. listmodel.ListModel is LIST_ONLY here,
# so no expander is ever drawn. Overridden at APPLICATION priority,
# which beats the theme's own THEME priority.
_FOLD_CSS = (b'treeview.journal-list { -GtkTreeView-expander-size: 0; '
             b'-GtkTreeView-vertical-separator: 0; }')

_FOLD_RESIDUE = style.zoom(1)
# timeline.FOLD_TINT, shared with gridview.py's own stack tint.

_FOLD_WASH_PAD = style.zoom(12)
_FOLD_WASH_INSET = style.zoom(16)
_FOLD_WASH_SEAM = style.zoom(8)

_CARD_INSET = style.zoom(5)
_CARD_RADIUS = style.zoom(14)
_CARD_PEEK_INSET = style.zoom(12)

_CARD_GROUND = timeline.PAGE_BG
_CARD_FILL = style.COLOR_WHITE.get_html()

_CARD_HAIRLINE = timeline.SPINE_COLOR
# 'treeview.journal-list-cards' alone has specificity (0,1,1); a bare
# '.journal-card' would lose to it in the same style context, so this
# rule repeats both classes rather than relying on provider order.
# CSS leaves border-style as 'none' by default, which zeroes the
# computed border-width, so Gtk.render_frame paints nothing unless
# border-style is set explicitly.
_CARD_CSS = ('''
treeview.journal-list-cards {
    background-color: transparent;
    background-image: none;
}
treeview.journal-list-cards.journal-card {
    background-color: %(fill)s;
    background-image: none;
    border-style: solid;
    border-width: %(border)dpx;
    border-color: %(hairline)s;
    border-radius: %(radius)dpx;
}
''' % {'fill': _CARD_FILL, 'hairline': _CARD_HAIRLINE,
       'radius': _CARD_RADIUS, 'border': style.zoom(1)}).encode()
# Clear of the gutter column (timeline.COLUMN_WIDTH), onto the ground.
_CARD_LEFT_GAP = style.zoom(8)
_CARD_RIGHT_MARGIN = style.zoom(16)

# The chip's colour is the XO stroke colour from the user's profile
# (sugar3.profile), so there is no constant tint to hardcode.
_FOLD_CHIP_FONT = style.zoom(12)
_FOLD_CHIP_HEIGHT = style.zoom(22)
_FOLD_CHIP_PAD_X = style.zoom(10)
_FOLD_CHIP_GAP = style.zoom(10)

# Shared with gridview.py's own _SCROLLBAR_* values.
_SCROLLBAR_WIDTH = timeline.SCROLLBAR_WIDTH
_SCROLLBAR_REST = timeline.SCROLLBAR_REST
_SCROLLBAR_HOVER = timeline.SCROLLBAR_HOVER
_GROUND_CSS = ('''
scrolledwindow.journal-list-ground,
scrolledwindow.journal-list-ground viewport {
    background-color: %(ground)s;
    background-image: none;
}
''' % {'ground': _CARD_GROUND}).encode()

_SCROLLBAR_CSS = ('''
scrollbar.journal-list-scrollbar {
    background-color: transparent;
    background-image: none;
    border: none;
}
scrollbar.journal-list-scrollbar trough {
    background-color: %(ground)s;
    background-image: none;
    border: none;
}
scrollbar.journal-list-scrollbar slider {
    background-color: %(rest)s;
    background-image: none;
    border: none;
    border-radius: %(width)dpx;
    min-width: %(width)dpx;
}
scrollbar.journal-list-scrollbar slider:hover {
    background-color: %(hover)s;
}
''' % {'ground': _CARD_GROUND, 'rest': _SCROLLBAR_REST,
       'hover': _SCROLLBAR_HOVER, 'width': _SCROLLBAR_WIDTH}).encode()

# Sized to model.MIN_PAGES_TO_CACHE pages of ListModel._PAGE_SIZE.
_TIMELINE_SWEEP_PREFIX = 30
_TIMELINE_SWEEP_CHUNK = 50

_timeline_text_heights = {}


def _timeline_text_height(font_px, weight):
    if (font_px, weight) not in _timeline_text_heights:
        layout = Pango.Layout(Gtk.Label(label='').get_pango_context())
        layout.set_font_description(_timeline_font(font_px, weight))
        layout.set_text('Wednesday, 30 September', -1)
        width_, height = layout.get_pixel_size()
        _timeline_text_heights[(font_px, weight)] = height
    return _timeline_text_heights[(font_px, weight)]


def _timeline_font(font_px, weight):
    # HACK: Pango.FontDescription() leaves the family unset and falls
    # back to Pango's own default, so set it explicitly.
    description = Pango.FontDescription()
    settings = Gtk.Settings.get_default()
    if settings is not None:
        family = Pango.FontDescription(
            settings.props.gtk_font_name).get_family()
        if family:
            description.set_family(family)
    description.set_weight(weight)
    description.set_absolute_size(font_px * Pango.SCALE)
    return description


def _timeline_strips():
    if _TIMELINE_DAY_FONT:
        day = (_timeline_text_height(_TIMELINE_DAY_FONT,
                                     Pango.Weight.BOLD) +
               2 * _TIMELINE_DAY_PAD)
    else:
        day = _TIMELINE_DAY_PAD
    if _TIMELINE_BAND_FONT:
        band = (_timeline_text_height(_TIMELINE_BAND_FONT,
                                      Pango.Weight.SEMIBOLD) +
                2 * _TIMELINE_BAND_PAD)
    else:
        band = _TIMELINE_BAND_PAD
    return day, band


def _page_top_margin():
    return max(0, timeline.PAGE_INSET - _TIMELINE_DAY_PAD)


def _timeline_content_area(cell_area):
    # Gtk.CellRendererPixbuf caches its icon offset for the renderer's life.
    extra = cell_area.height - _ROW_HEIGHT
    if extra <= 0:
        return cell_area
    area = Gdk.Rectangle()
    area.x = cell_area.x
    area.y = cell_area.y + extra
    area.width = cell_area.width
    area.height = _ROW_HEIGHT
    return area


def _paint_card_frame(cr, cell_area, margin, radius):
    # CellRendererIcon.do_render() repaints the background, wiping out
    # earlier drawing.
    x = cell_area.x + margin
    y = cell_area.y + margin
    width = cell_area.width - 2 * margin
    height = cell_area.height - 2 * margin
    if width <= 0 or height <= 0:
        return

    cr.save()
    timeline.rounded_rect_path(cr, x, y, width, height, radius)
    cr.set_source_rgb(*_CARD_BORDER_RGB)
    cr.set_line_width(style.zoom(1))
    cr.stroke()
    cr.restore()


def _add_css(style_context, css_data):
    provider = Gtk.CssProvider()
    provider.load_from_data(css_data)
    style_context.add_provider(
        provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


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
        Gtk.TreeView.__init__(self)

        self._journalactivity = journalactivity
        self.icon_activity_column = None
        self.buddies_columns = []

        self._invoker = TreeViewInvoker()
        self._invoker.attach_treeview(self)

        self.set_headers_visible(False)
        self.set_enable_search(False)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.TOUCH_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)

    def connect_to_scroller(self, scrolled):
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
                    if buddy_value is not None:
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

    def do_size_request(self, requisition):
        # HACK: We tell the model that the view is just resizing so it can
        # avoid hitting both D-Bus and disk.
        tree_model = self.get_model()
        if tree_model is not None:
            tree_model.view_is_resizing = True
        try:
            Gtk.TreeView.do_size_request(self, requisition)
        finally:
            if tree_model is not None:
                tree_model.view_is_resizing = False

    def __del__(self):
        self._invoker.detach()


class BaseListView(BaseJournalView):
    __gtype_name__ = 'JournalBaseListView'

    __gsignals__ = {
        'detail-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object])),
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, journalactivity, enable_multi_operations=False,
                 enable_timeline=None):
        self._journalactivity = journalactivity
        self._enable_multi_operations = enable_multi_operations
        # Only journalactivity.py's own list wants a timeline by default.
        if enable_timeline is None:
            enable_timeline = enable_multi_operations
        self._enable_timeline = enable_timeline
        self._timeline_column = None
        self._timeline_cell = None
        self._timeline_rows = {}
        self._timeline_previous = None
        self._timeline_swept = 0
        self._timeline_sweep_handler = None
        self._fold_rows = {}
        self._fold_run = []
        self._fold_run_state = None
        self._expanded_sittings = set()
        self._fold_just_toggled = False
        self._expanding_cursor = False
        self._scroll_position = 0.
        self._projects_view_active = False

        BaseJournalView.__init__(self)

        self.connect('map', self.__map_cb)
        self.connect('unmap', self.__unmap_cb)
        self.connect('destroy', self.__destroy_cb)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self.add(self._scrolled_window)
        self._scrolled_window.show()

        self.tree_view = TreeView(self._journalactivity)
        self.tree_view.connect('detail-clicked', self.__detail_clicked_cb)
        self.tree_view.connect('volume-error', self.__volume_error_cb)
        selection = self.tree_view.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        # HACK: GtkTreeView fixed_height_mode copies one row's height to
        # every row, so it must stay off for variable-height timeline rows.
        self.tree_view.props.fixed_height_mode = not self._enable_timeline
        if self._enable_timeline:
            self.tree_view.connect_after('draw', self.__timeline_draw_cb)
            self.tree_view.connect('cursor-changed', self.__cursor_changed_cb)
            style_context = self.tree_view.get_style_context()
            style_context.add_class('journal-list')
            _add_css(style_context, _FOLD_CSS)
            # connect(), not connect_after(): GTK runs this before the
            # widget's default draw handler, so the fill lands under the cells.
            self.tree_view.connect('draw', self.__card_draw_cb)
            _add_css(style_context, _CARD_CSS)

            self.tree_view.set_margin_top(_page_top_margin())
            ground_context = self._scrolled_window.get_style_context()
            ground_context.add_class('journal-list-ground')
            _add_css(ground_context, _GROUND_CSS)
            # Scoped to this view's own class, not gridview.py's provider,
            # so the rest of the shell's scrollbars stay as they are.
            vscrollbar = self._scrolled_window.get_vscrollbar()
            if vscrollbar is not None:
                bar_context = vscrollbar.get_style_context()
                bar_context.add_class('journal-list-scrollbar')
                _add_css(bar_context, _SCROLLBAR_CSS)
        self._scrolled_window.add(self.tree_view)
        self.tree_view.show()

        self.cell_title = None
        self.cell_icon = None
        self._title_column = None
        self.sort_column = None
        self._scrolling_detector = ScrollingDetector(self._scrolled_window)
        self.tree_view.connect_to_scroller(self._scrolling_detector)

        self._add_columns()
        self.enable_drag_and_copy()
        if self._enable_timeline:
            self._apply_card_style()

        # Auto-update stuff
        self._refresh_idle_handler = None
        self._update_dates_timer = None
        self._backup_selected = None

        self._connect_model_signals()
        model.updated.connect(self.__model_updated_cb)

    def enable_drag_and_copy(self):
        self.tree_view.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                                       [Gtk.TargetEntry.new(
                                           'text/uri-list', 0, 0),
                                        Gtk.TargetEntry.new(
                                            'journal-object-id', 0, 0)],
                                       Gdk.DragAction.COPY)

    def disable_drag_and_copy(self):
        self.tree_view.unset_rows_drag_source()

    def __model_updated_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def _is_new_item_visible(self, object_id):
        """Check if the created item is part of the currently selected view"""
        if 'project_id' in self._query:
            # TODO:  Would be best to check if the object_id is in the project.
            #        But there is only ever 1 project listview, so it should
            #        not be very costly.
            return True
        return BaseJournalView._is_new_item_visible(self, object_id)

    def _fixed_column(self, cell, width=None, data_func=None,
                      attributes=()):
        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        if width is not None:
            column.props.fixed_width = width
        column.pack_start(cell, True)
        for attribute, model_column in attributes:
            column.add_attribute(cell, attribute, model_column)
        if data_func is not None:
            column.set_cell_data_func(cell, data_func)
        self.tree_view.append_column(column)
        return column

    def _add_columns(self):
        if self._enable_timeline:
            self._timeline_cell = CellRendererTimeline()
            self._timeline_column = self._fixed_column(
                self._timeline_cell, width=_TIMELINE_COLUMN_WIDTH,
                data_func=self.__timeline_set_data_cb)

        if self._enable_multi_operations:
            cell_select = CellRendererSelect()
            cell_select.connect('toggled', self.__cell_select_toggled_cb)
            cell_select.props.activatable = True
            cell_select.props.xpad = style.DEFAULT_PADDING
            cell_select.props.indicator_size = style.zoom(26)

            self._fixed_column(cell_select, width=style.GRID_CELL_SIZE,
                               data_func=self.__select_set_data_cb)

        cell_favorite = CellRendererFavorite(self._enable_timeline)
        cell_favorite.connect('clicked', self._favorite_clicked_cb)
        cell_favorite.connect_to_scroller(self._scrolling_detector)

        self._fav_column = self._fixed_column(
            cell_favorite, width=cell_favorite.props.width,
            data_func=self.__favorite_set_data_cb)

        self.cell_icon = CellRendererActivityIcon(self._enable_timeline)
        self.cell_icon.connect_to_scroller(self._scrolling_detector)

        self.tree_view.icon_activity_column = self._fixed_column(
            self.cell_icon, width=self.cell_icon.props.width,
            data_func=self._row_set_data_cb,
            attributes=(('file-name', ListModel.COLUMN_ICON),
                        ('xo-color', ListModel.COLUMN_ICON_COLOR)))

        self.cell_title = CellRendererRowText()
        self.cell_title.props.ellipsize = style.ELLIPSIZE_MODE_DEFAULT
        self.cell_title.props.ellipsize_set = True
        if self._enable_timeline:
            self.cell_title.props.scale = 1.15
        self.cell_title.props.ypad = style.DEFAULT_PADDING

        self._title_column = self._fixed_column(
            self.cell_title, data_func=self._row_set_data_cb,
            attributes=(('markup', ListModel.COLUMN_TITLE),))
        self._title_column.props.expand = True
        self._title_column.props.clickable = True

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

        cell_progress = CellRendererRowProgress()
        cell_progress.props.ypad = style.GRID_CELL_SIZE / 4
        buddies_column.pack_start(cell_progress, True)
        buddies_column.add_attribute(cell_progress, 'value',
                                     ListModel.COLUMN_PROGRESS)
        buddies_column.set_cell_data_func(cell_progress,
                                          self.__progress_data_cb)

        cell_text = CellRendererRowText()
        cell_text.props.xalign = 1
        if self._enable_timeline:
            # Matches expandedentry.py's muted "KIND . DATE" caption style.
            cell_text.props.foreground = style.COLOR_BUTTON_GREY.get_html()
            cell_text.props.scale = 0.85

        # Measure the required width for a date in the form of "10 hours, 10
        # minutes ago"
        timestamp = time.time() - 10 * 60 - 10 * 60 * 60
        date = util.timestamp_to_elapsed_string(timestamp)
        date_width = self._get_width_for_string(date)

        self.sort_column = self._fixed_column(
            cell_text, width=date_width, data_func=self._row_set_data_cb,
            attributes=(('text', ListModel.COLUMN_TIMESTAMP),))
        self.sort_column.set_alignment(1)
        self.sort_column.props.resizable = True
        self.sort_column.props.clickable = True

    def _get_width_for_string(self, text):
        # Add some extra margin
        text = text + 'aaaaa'

        widget = Gtk.Label(label='')
        context = widget.get_pango_context()
        layout = Pango.Layout(context)
        layout.set_text(text, len(text))
        width, height_ = layout.get_pixel_size()
        return width

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)
        self.get_child().size_allocate(allocation)

    def do_size_request(self, requisition):
        requisition.width, requisition.height = \
            self.get_child().size_request()

    def __destroy_cb(self, widget):
        self._stop_timeline_sweep()
        if self._model is not None:
            self._model.stop()

    def _apply_fold(self, cell, tree_model, tree_iter, visible=True):
        sliver = self._fold_sliver(tree_iter.user_data)
        if sliver:
            cell.props.visible = False
            cell.props.height = sliver
        else:
            cell.props.visible = visible
            cell.props.height = cell.full_height

    def __buddies_set_data_cb(self, column, cell, tree_model,
                              tree_iter, data):
        buddy = tree_model.do_get_value(tree_iter, cell._model_column_index)
        if buddy is None:
            self._apply_fold(cell, tree_model, tree_iter, visible=False)
            return
        # FIXME workaround for pygobject bug, see
        # https://bugzilla.gnome.org/show_bug.cgi?id=689277
        #
        # add_attribute with 'buddy' attribute in the cell should take
        # care of setting it.
        cell.props.buddy = buddy

        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        self._apply_fold(cell, tree_model, tree_iter,
                         visible=progress >= 100)

    def __progress_data_cb(self, column, cell, tree_model,
                           tree_iter, data):
        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        self._apply_fold(cell, tree_model, tree_iter, visible=progress < 100)

    def _row_set_data_cb(self, column, cell, tree_model, tree_iter, data):
        self._apply_fold(cell, tree_model, tree_iter)

    def __favorite_set_data_cb(self, column, cell, tree_model,
                               tree_iter, data):
        favorite = tree_model[tree_iter][ListModel.COLUMN_FAVORITE]
        if favorite:
            cell.props.xo_color = profile.get_color()
        else:
            cell.props.xo_color = None
        self._apply_fold(cell, tree_model, tree_iter)

    def _favorite_clicked_cb(self, cell, path):
        if not self._pointer_in_card(path):
            return
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
        if self._card_active():
            self.tree_view.queue_draw()

        cell_rect = self.tree_view.get_cell_area(path, self._fav_column)
        self.tree_view.queue_draw_area(cell_rect.x, cell_rect.y,
                                       cell_rect.width, cell_rect.height)

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
        self._apply_fold(cell, tree_model, tree_iter)

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
            self._expanded_sittings = set()
        self._query = query_dict
        self._update_timeline_visible()
        self.refresh(new_query=True)

    def _update_timeline_visible(self):
        if self._timeline_column is None:
            return
        order_by = self._query.get('order_by') or ['+timestamp']
        visible = timeline.is_date_sort(order_by)
        self._timeline_column.props.visible = visible
        self.tree_view.set_margin_top(
            _page_top_margin() if visible else timeline.PAGE_INSET)

    def refresh(self, new_query=False):
        logging.debug('ListView.refresh query %r', self._query)
        if self._defer_refresh(new_query):
            return
        self._stop_progress_bar()
        self._model_ready = False
        window = self.get_toplevel().get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
            Gdk.flush()
        GLib.idle_add(self._do_refresh, new_query)

    def _do_refresh(self, new_query=False):
        self._stop_timeline_sweep()
        self._reset_model(new_query)
        self._model.connect('ready', self.__model_ready_cb)
        self._model.setup(self.__model_updated_cb)
        window = self.get_toplevel().get_window()
        if window is not None:
            window.set_cursor(None)
            Gdk.flush()

    def __model_ready_cb(self, tree_model):
        self._stop_progress_bar()
        self._model_ready = True

        self._scroll_position = self.tree_view.props.vadjustment.props.value
        logging.debug('ListView.__model_ready_cb %r', self._scroll_position)

        x11_window = self.tree_view.get_window()

        if x11_window is not None:
            # prevent glitches while later vadjustment setting, see #1235
            self.tree_view.get_bin_window().hide()

        # if the selection was preserved, restore it
        if self._backup_selected is not None:
            tree_model.restore_selection(self._backup_selected)
            self.emit('selection-changed', len(self._backup_selected))

        self._start_timeline_sweep(tree_model)

        # Cannot set it up earlier because will try to access the model
        # and it needs to be ready.
        self.tree_view.set_model(self._model)

        self.tree_view.props.vadjustment.props.value = self._scroll_position
        self.tree_view.props.vadjustment.value_changed()

        if x11_window is not None:
            # prevent glitches while later vadjustment setting, see #1235
            self.tree_view.get_bin_window().show()

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

    def _stop_timeline_sweep(self):
        if self._timeline_sweep_handler is not None:
            GLib.source_remove(self._timeline_sweep_handler)
            self._timeline_sweep_handler = None

    def _start_timeline_sweep(self, tree_model):
        self._stop_timeline_sweep()
        self._timeline_rows = {}
        self._fold_rows = {}
        self._fold_run = []
        self._fold_run_state = None
        self._timeline_previous = None
        self._timeline_swept = 0
        if not self._enable_timeline:
            return
        try:
            self._sweep_timeline_rows(tree_model, _TIMELINE_SWEEP_PREFIX,
                                      notify=False)
            self._close_fold_run(tree_model, notify=False)
        except Exception:
            logging.exception('Journal: timeline sweep failed, '
                              'falling back to a plain list')
            return
        if self._timeline_swept < len(tree_model):
            self._timeline_sweep_handler = GLib.idle_add(
                self.__timeline_sweep_cb, tree_model)

    def __timeline_sweep_cb(self, tree_model):
        if tree_model is not self._model:
            self._timeline_sweep_handler = None
            return False
        try:
            self._sweep_timeline_rows(tree_model, _TIMELINE_SWEEP_CHUNK,
                                      notify=True)
        except Exception:
            logging.exception('Journal: timeline sweep failed, '
                              'the rest of the list stays plain')
            self._timeline_sweep_handler = None
            return False
        if self._timeline_swept < len(tree_model):
            return True

        self._close_fold_run(tree_model, notify=True)
        self._timeline_sweep_handler = None
        self.tree_view.props.vadjustment.props.value = self._scroll_position
        self.tree_view.props.vadjustment.value_changed()
        return False

    def _sweep_timeline_rows(self, tree_model, count, notify):
        total = len(tree_model)
        limit = min(total, self._timeline_swept + count)
        date_index = (3 if timeline.sort_field(self._query.get('order_by')) ==
                      'creation_time' else 1)
        for index in range(self._timeline_swept, limit):
            facts = tree_model.get_row_facts(index)
            uid = facts[0] if facts else None
            date_value = facts[date_index] if facts else None
            sitting = facts[2] if facts else None
            day = time.localtime(date_value)[:3] if date_value else None
            kind = timeline.band_kind(date_value)
            if self._timeline_previous is None:
                opens_day = opens_band = day is not None
            else:
                previous_day, previous_kind = self._timeline_previous
                opens_day = day is not None and day != previous_day
                opens_band = opens_day or (day is not None and
                                           kind != previous_kind)
            self._timeline_previous = (day, kind)
            self._extend_fold_run(tree_model, index, uid, sitting,
                                  opens_band, notify)
            if not opens_day and not opens_band:
                continue
            self._timeline_rows[index] = (day if opens_day else None,
                                          kind if opens_band else None)
            if notify:
                path = Gtk.TreePath((index,))
                tree_model.row_changed(path, tree_model.get_iter(path))
        self._timeline_swept = limit

    def _extend_fold_run(self, tree_model, index, uid, sitting,
                         opens_band, notify):
        if self._fold_run_state is not None:
            if opens_band or sitting != self._fold_run_state:
                self._close_fold_run(tree_model, notify)
        self._fold_run_state = sitting
        self._fold_run.append((index, uid))

    def _close_fold_run(self, tree_model, notify):
        run, self._fold_run = self._fold_run, []
        self._fold_run_state = None
        if len(run) < timeline.FOLD_MIN_CARDS:
            return
        key = run[0][1]
        for position, (index, uid_) in enumerate(run):
            self._fold_rows[index] = (key, len(run) - 1, position)
            if notify:
                path = Gtk.TreePath((index,))
                tree_model.row_changed(path, tree_model.get_iter(path))

    def _fold_active(self):
        return (_FOLD_SLIVER > 0 and
                self._timeline_column is not None and
                self._timeline_column.props.visible)

    def _fold_sliver(self, index):
        if not self._fold_active():
            return 0
        entry = self._fold_rows.get(index)
        if entry is None:
            return 0
        key, count_, position = entry
        if position == 0 or key in self._expanded_sittings:
            return 0
        if position > 1:
            return _FOLD_RESIDUE
        return _FOLD_SLIVER

    def toggle_sitting(self, path):
        if not self._fold_active():
            return False
        entry = self._fold_rows.get(path.get_indices()[0])
        if entry is None:
            return False
        self._set_sitting_expanded(entry[0], entry[0] not in
                                   self._expanded_sittings)
        return True

    def collapse_sitting(self, path):
        if path is None or not self._fold_active():
            return False
        index = path.get_indices()[0]
        entry = self._fold_rows.get(index)
        if entry is None or entry[0] not in self._expanded_sittings:
            return False
        self._expanding_cursor = True
        try:
            self.tree_view.set_cursor(Gtk.TreePath((index - entry[2],)))
        finally:
            self._expanding_cursor = False
        self._set_sitting_expanded(entry[0], False)
        return True

    def _set_sitting_expanded(self, key, expanded):
        if (key in self._expanded_sittings) == expanded:
            return
        if expanded:
            self._expanded_sittings.add(key)
        else:
            self._expanded_sittings.discard(key)
        model_ = self._model
        indices = sorted(index for index, entry in self._fold_rows.items()
                         if entry[0] == key)
        for index in indices:
            path = Gtk.TreePath((index,))
            model_.row_changed(path, model_.get_iter(path))
        if indices and indices[-1] + 1 < model_.iter_n_children(None):
            path = Gtk.TreePath((indices[-1] + 1,))
            model_.row_changed(path, model_.get_iter(path))

    def __cursor_changed_cb(self, tree_view):
        if self._expanding_cursor or not self._fold_active():
            return
        path, column_ = tree_view.get_cursor()
        if path is None:
            return
        entry = self._fold_rows.get(path.get_indices()[0])
        if entry is None or entry[2] == 0:
            return
        self._expanding_cursor = True
        try:
            self._set_sitting_expanded(entry[0], True)
        finally:
            self._expanding_cursor = False

    def _apply_card_style(self):
        style_context = self.tree_view.get_style_context()
        if self._card_active():
            style_context.add_class('journal-list-cards')
        else:
            style_context.remove_class('journal-list-cards')

    def __timeline_set_data_cb(self, column, cell, tree_model, tree_iter,
                               data):
        index = tree_iter.user_data
        day, kind = self._timeline_rows.get(index, (None, None))
        day_strip, band_strip = _timeline_strips()
        cell.day_strip = day_strip if day is not None else 0
        cell.band_strip = band_strip if kind is not None else 0
        cell.band_kind = kind
        cell.sliver = self._fold_sliver(index)
        entry = self._fold_rows.get(index)
        cell.wash_pad = 0
        if self._card_active():
            opens = entry is not None and entry[2] == 0 and \
                entry[0] in self._expanded_sittings
            prev_entry = self._fold_rows.get(index - 1)
            closes = prev_entry is not None and \
                prev_entry[2] == prev_entry[1] and \
                prev_entry[0] in self._expanded_sittings
            if opens:
                cell.wash_pad += _FOLD_WASH_PAD
            if closes:
                cell.wash_pad += _FOLD_WASH_PAD + _FOLD_WASH_SEAM

    def __timeline_draw_cb(self, tree_view, cr):
        # A cell renderer is clipped to its own cell area, not the column.
        if self._timeline_column is None or \
                not self._timeline_column.props.visible:
            return False
        bin_window = tree_view.get_bin_window()
        if bin_window is None or \
                not Gtk.cairo_should_draw_window(cr, bin_window):
            return False
        visible_range = tree_view.get_visible_range()
        if visible_range is None:
            return False

        day_strip, band_strip = _timeline_strips()
        now = time.time()
        first = visible_range[0].get_indices()[0]
        last = visible_range[1].get_indices()[0]

        cr.save()
        cr.set_antialias(cairo.ANTIALIAS_BEST)
        for index in range(first, last + 1):
            day, kind = self._timeline_rows.get(index, (None, None))
            if day is None and kind is None:
                continue
            # width comes back 0 for a NULL column; only .y is usable
            area = tree_view.get_background_area(Gtk.TreePath((index,)), None)
            top = area.y
            if day is not None:
                if _TIMELINE_DAY_FONT:
                    self._draw_timeline_text(
                        cr, timeline.day_label(day, now), timeline.PAGE_INSET,
                        top, day_strip, _TIMELINE_DAY_FONT,
                        Pango.Weight.BOLD, _TIMELINE_DAY_INK)
                top += day_strip
            if kind is not None and _TIMELINE_BAND_FONT:
                self._draw_timeline_text(
                    cr, timeline.band_label(kind), _TIMELINE_COLUMN_WIDTH, top,
                    band_strip, _TIMELINE_BAND_FONT,
                    Pango.Weight.SEMIBOLD, _TIMELINE_BAND_INK)
        cr.restore()
        return False

    def _card_active(self):
        return (_CARD_INSET > 0 and
                self._timeline_column is not None)

    def _card_lane(self, tree_view):
        width = tree_view.get_allocated_width()
        card_left = (_TIMELINE_COLUMN_WIDTH + _CARD_LEFT_GAP
                     if self._timeline_column.props.visible
                     else _CARD_RIGHT_MARGIN)
        return card_left, width - _CARD_RIGHT_MARGIN

    def _card_rect(self, background_area, card_left, card_right):
        content = _timeline_content_area(background_area)
        return (card_left, content.y + _CARD_INSET, card_right - card_left,
                content.height - 2 * _CARD_INSET)

    def _pointer_in_card(self, path):
        """Re-derive (x, y) the way CellRendererIcon.do_render does."""
        if not self._card_active():
            return True
        card_left, card_right = self._card_lane(self.tree_view)
        if card_right <= card_left:
            return True
        x, y = self.tree_view.get_pointer()
        x, y = self.tree_view.convert_widget_to_bin_window_coords(x, y)
        area = self.tree_view.get_background_area(path, None)
        left, top, width, height = self._card_rect(area, card_left,
                                                   card_right)
        return left <= x <= left + width and top <= y <= top + height

    def _fold_chip_geometry(self, tree_view, path):
        if not self._fold_active():
            return None
        index = path.get_indices()[0]
        entry = self._fold_rows.get(index)
        if entry is None or entry[2] != 0:
            return None
        key, count = entry[0], entry[1]
        text = (_('fewer') if key in self._expanded_sittings
                else ngettext('%d more', '%d more', count) % (count,))
        layout = Pango.Layout(Gtk.Label(label='').get_pango_context())
        layout.set_font_description(
            _timeline_font(_FOLD_CHIP_FONT, Pango.Weight.BOLD))
        layout.set_text(text, -1)
        text_width, text_height_ = layout.get_pixel_size()
        width = text_width + 2 * _FOLD_CHIP_PAD_X
        title_area = tree_view.get_cell_area(path, self._title_column)
        date_area = tree_view.get_cell_area(path, self.sort_column)
        left = title_area.x + title_area.width + _FOLD_CHIP_GAP
        # Buddy icons share this band; start past any occupied cell.
        model = tree_view.get_model()
        tree_iter = model.get_iter(path)
        for column, model_index in zip(
                tree_view.buddies_columns,
                [ListModel.COLUMN_BUDDY_1, ListModel.COLUMN_BUDDY_2,
                 ListModel.COLUMN_BUDDY_3]):
            if model.do_get_value(tree_iter, model_index) is None:
                continue
            cell_area = tree_view.get_cell_area(path, column)
            left = max(left,
                       cell_area.x + cell_area.width + _FOLD_CHIP_GAP)
        right = date_area.x - _FOLD_CHIP_GAP
        if left + width > right:
            return None
        background = tree_view.get_background_area(path, None)
        content = _timeline_content_area(background)
        top = content.y + _CARD_INSET + (content.height - 2 * _CARD_INSET -
                                         _FOLD_CHIP_HEIGHT) / 2.
        return (left, top, width, _FOLD_CHIP_HEIGHT, text)

    def _draw_fold_chip(self, cr, tree_view, path):
        geometry = self._fold_chip_geometry(tree_view, path)
        if geometry is None:
            return
        left, top, width, height, text = geometry
        red, green, blue = timeline.hex_to_rgb01(
            profile.get_color().get_stroke_color())
        timeline.rounded_rect_path(cr, left, top, width, height, height / 2.)
        cr.set_source_rgba(red, green, blue, 0.15)
        cr.fill()
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(
            _timeline_font(_FOLD_CHIP_FONT, Pango.Weight.BOLD))
        layout.set_text(text, -1)
        text_width, text_height = layout.get_pixel_size()
        cr.move_to(left + (width - text_width) / 2.,
                   top + (height - text_height) / 2.)
        cr.set_source_rgb(red, green, blue)
        PangoCairo.show_layout(cr, layout)

    def _draw_fold_wash(self, cr, tree_view, index, entry, left, right,
                        pad, radius):
        key_, count, position = entry
        lead_area = tree_view.get_background_area(
            Gtk.TreePath((index - position,)), None)
        tail_area = tree_view.get_background_area(
            Gtk.TreePath((index - position + count,)), None)
        top = _timeline_content_area(lead_area).y - pad
        bottom = tail_area.y + tail_area.height + pad
        if bottom <= top:
            return
        timeline.rounded_rect_path(cr, left, top, right - left,
                                   bottom - top, radius)
        cr.set_source_rgb(*timeline.hex_to_rgb01(timeline.FOLD_TINT))
        cr.fill()

    def __card_draw_cb(self, tree_view, cr):
        if not self._card_active():
            return False
        # get_background_area is bin-window coordinates.
        bin_window = tree_view.get_bin_window()
        if bin_window is None or \
                not Gtk.cairo_should_draw_window(cr, bin_window):
            return False
        visible_range = tree_view.get_visible_range()
        if visible_range is None:
            return False
        first = visible_range[0].get_indices()[0]
        last = visible_range[1].get_indices()[0]
        card_left, card_right = self._card_lane(tree_view)
        if card_right <= card_left:
            return False

        lead_rows, peek_rows = [], []
        for index in range(first, last + 1):
            sliver = self._fold_sliver(index)
            if sliver == 0:
                lead_rows.append(index)
            elif sliver == _FOLD_SLIVER:
                peek_rows.append(index)

        cr.save()
        cr.set_antialias(cairo.ANTIALIAS_BEST)
        cr.set_source_rgb(*timeline.hex_to_rgb01(_CARD_GROUND))
        cr.rectangle(0, 0, tree_view.get_allocated_width(),
                     tree_view.get_allocated_height())
        cr.fill()

        radius = _CARD_RADIUS
        peek_inset = _CARD_PEEK_INSET

        washed = set()
        if self._fold_active():
            for index in range(first, last + 1):
                entry = self._fold_rows.get(index)
                if entry is None or entry[0] not in self._expanded_sittings \
                        or entry[0] in washed:
                    continue
                washed.add(entry[0])
                self._draw_fold_wash(cr, tree_view, index, entry,
                                     card_left - _FOLD_WASH_INSET,
                                     card_right + _FOLD_WASH_INSET,
                                     _FOLD_WASH_PAD, radius)

        for index in peek_rows:
            peek_area = tree_view.get_background_area(
                Gtk.TreePath((index,)), None)
            depth = min(peek_area.height, _CARD_PEEK_HEIGHT)
            peek_left = card_left + peek_inset
            peek_right = card_right - peek_inset
            if peek_right <= peek_left or depth <= 0:
                continue
            timeline.rounded_rect_path(cr, peek_left, peek_area.y - radius,
                                       peek_right - peek_left,
                                       depth + radius, radius)
            cr.set_source_rgb(*timeline.hex_to_rgb01(timeline.FOLD_TINT))
            cr.fill()

        # render_frame draws inside the box, unlike cr.stroke.
        style_context = tree_view.get_style_context()
        style_context.save()
        style_context.add_class('journal-card')
        style_context.set_state(Gtk.StateFlags.NORMAL)
        for index in lead_rows:
            path = Gtk.TreePath((index,))
            area = tree_view.get_background_area(path, None)
            left, top, card_width, height = self._card_rect(
                area, card_left, card_right)
            if height <= 0:
                continue
            Gtk.render_background(style_context, cr, left, top,
                                  card_width, height)
            Gtk.render_frame(style_context, cr, left, top,
                             card_width, height)
            self._draw_fold_chip(cr, tree_view, path)
        style_context.restore()
        cr.restore()
        return False

    def _draw_timeline_text(self, cr, text, x, top, strip, font_px, weight,
                            ink):
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(_timeline_font(font_px, weight))
        layout.set_text(text, -1)
        width_, height = layout.get_pixel_size()
        cr.set_source_rgb(*timeline.hex_to_rgb01(ink))
        cr.move_to(x, top + (strip - height) / 2.)
        PangoCairo.show_layout(cr, layout)

    def _can_clear_query(self):
        return True

    def __map_cb(self, widget):
        logging.debug('ListView.__map_cb %r', self._scroll_position)
        self.tree_view.props.vadjustment.props.value = self._scroll_position
        self.tree_view.props.vadjustment.value_changed()
        self.set_is_visible(True)

    def __unmap_cb(self, widget):
        self._scroll_position = self.tree_view.props.vadjustment.props.value
        logging.debug('ListView.__unmap_cb %r', self._scroll_position)
        self.set_is_visible(False)

    def update_dates(self):
        if not self.tree_view.get_realized():
            return
        visible_range = self.tree_view.get_visible_range()
        if visible_range is None:
            return

        logging.debug('ListView.update_dates')

        path, end_path = visible_range
        tree_model = self.tree_view.get_model()

        while True:
            cel_rect = self.tree_view.get_cell_area(path,
                                                    self.sort_column)
            x, y = self.tree_view.convert_tree_to_widget_coords(cel_rect.x,
                                                                cel_rect.y)
            self.tree_view.queue_draw_area(x, y, cel_rect.width,
                                           cel_rect.height)
            if path == end_path:
                break
            next_iter = tree_model.iter_next(tree_model.get_iter(path))
            path = tree_model.get_path(next_iter)

    def set_is_visible(self, visible):
        logging.debug('canvas_visibility_notify_event_cb %r', visible)
        BaseJournalView.set_is_visible(self, visible)
        if visible:
            if self._update_dates_timer is None:
                logging.debug('Adding date updating timer')
                self._update_dates_timer = \
                    GLib.timeout_add_seconds(UPDATE_INTERVAL,
                                             self.__update_dates_timer_cb)
        else:
            if self._update_dates_timer is not None:
                logging.debug('Remove date updating timer')
                GLib.source_remove(self._update_dates_timer)
                self._update_dates_timer = None

    def __update_dates_timer_cb(self):
        self.update_dates()
        return True

    def _repaint_selection(self):
        self.tree_view.queue_draw()

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
        'project-view-activate': (GObject.SignalFlags.RUN_FIRST, None,
                                  ([object])),
    }

    def __init__(self, journalactivity, enable_multi_operations=False,
                 enable_timeline=None):
        BaseListView.__init__(self, journalactivity, enable_multi_operations,
                              enable_timeline)
        self._is_dragging = False

        self.tree_view.connect('drag-begin', self.__drag_begin_cb)
        self.tree_view.connect('drag-data-get', self.__drag_data_get_cb)
        self.tree_view.connect('button-release-event',
                               self.__button_release_event_cb)
        self.tree_view.connect('key-press-event', self._key_press_event_cb)

        self.cell_title.connect('edited', self.__cell_title_edited_cb)
        self.cell_title.connect('editing-canceled', self.__editing_canceled_cb)

        self.cell_icon.connect('clicked', self.__icon_clicked_cb)

        cell_detail = CellRendererDetail(self._enable_timeline)
        cell_detail.connect('clicked', self.__detail_cell_clicked_cb)

        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        column.props.fixed_width = cell_detail.props.width
        column.pack_start(cell_detail, True)
        column.set_cell_data_func(cell_detail, self._row_set_data_cb)
        self.tree_view.append_column(column)

    def _key_press_event_cb(self, tree_view, event):
        '''
        Adds keyboard accessibility to the journal.
        Activity can be resumed by pressing 'Enter' key.
        Entry can be renamed by pressing 'Ctrl' + 'F2' keys
        Detail View can be opened with 'Right' arrow key.
        '''
        keyname = Gdk.keyval_name(event.keyval)
        path, col = self.tree_view.get_cursor()

        if self.tree_view.has_focus():
            if keyname == 'Return':
                self.__icon_clicked_cb(None, path)

            if event.state & Gdk.ModifierType.CONTROL_MASK and keyname == 'F2':
                row = self.tree_view.get_model()[path]
                metadata = model.get(row[ListModel.COLUMN_UID])
                self.cell_title.props.editable = model.is_editable(metadata)

                if self.cell_title.props.editable:
                    self.emit('title-edit-started')

                # By reference, not ordinal: projectview.py uses a
                # different column order for its title column.
                column = self._title_column
                tree_view.set_cursor_on_cell(path, column, self.cell_title,
                                         start_editing=True)

            if keyname == 'Right':
                tree_iter = self._model.get_iter(path)
                uid = self._model[tree_iter][ListModel.COLUMN_UID]
                self.emit('detail-clicked', uid)

            if keyname == 'Left':
                self.collapse_sitting(path)


    def is_dragging(self):
        return self._is_dragging

    def __drag_begin_cb(self, widget, drag_context):
        path, _column = self.tree_view.get_cursor()
        if path is None:
            return

        row = self.tree_view.get_model()[path]
        _pixbuf = GdkPixbuf.Pixbuf.new_from_file(row[ListModel.COLUMN_ICON])
        self.tree_view.drag_source_set_icon_pixbuf(_pixbuf)
        self._is_dragging = True

    def __drag_data_get_cb(self, widget, context, selection, info, time):
        # HACK:  Gtk.TreeDragSource does not work for us on Gtk 3.16+, so
        #        use our drag source code instead
        path, _column = self.tree_view.get_cursor()
        model = self.tree_view.get_model()
        model.do_drag_data_get(path, selection)

    def __button_release_event_cb(self, tree_view, event):
        try:
            if self._is_dragging:
                return
        finally:
            self._is_dragging = False

        pos = tree_view.get_path_at_pos(int(event.x), int(event.y))
        if pos is None:
            return

        path, column, x_, y_ = pos
        chip = self._fold_chip_geometry(tree_view, path)
        if chip is not None:
            chip_left, chip_top, chip_width, chip_height, text_ = chip
            if chip_left <= event.x <= chip_left + chip_width and \
                    chip_top <= event.y <= chip_top + chip_height:
                if self.toggle_sitting(path):
                    self._fold_just_toggled = True
                return

        if column is self._timeline_column or \
                self._fold_sliver(path.get_indices()[0]):
            if self.toggle_sitting(path):
                self._fold_just_toggled = True
                return

        if column != self._title_column:
            return
        if self._fold_sliver(path.get_indices()[0]):
            return
        if self._fold_just_toggled:
            self._fold_just_toggled = False
            return

        if self._card_active():
            card_left, card_right = self._card_lane(tree_view)
            if card_right > card_left:
                left, top, card_width, height = self._card_rect(
                    tree_view.get_background_area(path, None),
                    card_left, card_right)
                if not (left <= event.x <= left + card_width and
                        top <= event.y <= top + height):
                    return

        row = self.tree_view.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        self.cell_title.props.editable = model.is_editable(metadata)
        if self.cell_title.props.editable:
            self.emit('title-edit-started')

        tree_view.set_cursor_on_cell(path, column, self.cell_title,
                                     start_editing=True)

    def __detail_cell_clicked_cb(self, cell, path):
        if not self._pointer_in_card(path):
            return
        row = self.tree_view.get_model()[path]
        self.emit('detail-clicked', row[ListModel.COLUMN_UID])

    def __icon_clicked_cb(self, cell, path):
        if cell is not None and not self._pointer_in_card(path):
            return
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
            alert.connect('response', self._cell_title_alert_response_cb,
                          path, new_text)
            journalwindow.get_journal_window().add_alert(alert)
            alert.show()
            return

        if old_text != new_text:
            self._model[iterator][ListModel.COLUMN_TITLE] = new_text
            self.emit('title-edit-finished', new_text, path)

    def _cell_title_alert_response_cb(self, alert, response_id, path,
                                      new_text):
        journalwindow.get_journal_window().remove_alert(alert)

        iterator = self._model.get_iter(path)
        if response_id is Gtk.ResponseType.OK:
            self._model[iterator][ListModel.COLUMN_TITLE] = new_text
            self.emit('title-edit-finished', new_text, path)

    def __editing_canceled_cb(self, cell):
        self.cell_title.props.editable = False


class CellRendererTimeline(Gtk.CellRenderer):
    # HACK: GtkCellRenderer needs fixed_height_mode off and its own
    # column, or GtkTreeView skips a renderer requesting zero width
    # and clips one requesting a single pixel.

    __gtype_name__ = 'JournalCellRendererTimeline'

    def __init__(self):
        Gtk.CellRenderer.__init__(self)
        self.props.xpad = 0
        self.props.ypad = 0
        self.day_strip = 0
        self.band_strip = 0
        self.band_kind = None
        self.sliver = 0
        self.wash_pad = 0

    def do_get_preferred_width(self, widget):
        return (_TIMELINE_COLUMN_WIDTH, _TIMELINE_COLUMN_WIDTH)

    def do_get_preferred_height(self, widget):
        if self.sliver:
            return (self.sliver, self.sliver)
        height = (_ROW_HEIGHT + self.day_strip + self.band_strip +
                  self.wash_pad)
        return (height, height)

    def do_render(self, cr, widget, background_area, cell_area, flags):
        centre = (background_area.x + timeline.PAGE_INSET +
                  timeline.spine_centre_in_slot())
        top = background_area.y
        bottom = top + background_area.height

        if self.sliver:
            cr.save()
            cr.set_antialias(cairo.ANTIALIAS_BEST)
            timeline.draw_spine(cr, centre, top, bottom, [])
            cr.restore()
            return

        swatch = None
        if self.band_kind in timeline.BAND_SKY:
            if self.band_strip:
                swatch = top + self.day_strip + self.band_strip / 2.
            else:
                swatch = (top + self.day_strip + timeline.SWATCH_HALF +
                          timeline.GLYPH_CLEARANCE)

        cr.save()
        cr.set_antialias(cairo.ANTIALIAS_BEST)
        start = top + self.day_strip
        if swatch is not None and self.day_strip:
            start = max(start, swatch)
        timeline.draw_spine(cr, centre, start, bottom, [swatch])
        if swatch is not None:
            cr.save()
            cr.translate(centre - timeline.GLYPH_SIZE / 2.,
                         swatch - timeline.GLYPH_SIZE / 2.)
            timeline.draw_swatch(cr, self.band_kind, timeline.GLYPH_SIZE)
            cr.restore()
        cr.restore()


class CellRendererRowText(Gtk.CellRendererText):
    __gtype_name__ = 'JournalCellRendererRowText'

    def __init__(self):
        Gtk.CellRendererText.__init__(self)
        self.full_height = self.props.height

    def do_render(self, cr, widget, background_area, cell_area, flags):
        Gtk.CellRendererText.do_render(
            self, cr, widget, background_area,
            _timeline_content_area(cell_area), flags)


class CellRendererRowProgress(Gtk.CellRendererProgress):
    __gtype_name__ = 'JournalCellRendererRowProgress'

    def __init__(self):
        Gtk.CellRendererProgress.__init__(self)
        self.full_height = self.props.height

    def do_render(self, cr, widget, background_area, cell_area, flags):
        Gtk.CellRendererProgress.do_render(
            self, cr, widget, background_area,
            _timeline_content_area(cell_area), flags)


class CellRendererSelect(Gtk.CellRendererToggle):
    __gtype_name__ = 'JournalCellRendererSelect'

    def __init__(self):
        Gtk.CellRendererToggle.__init__(self)
        self.full_height = self.props.height

    def do_render(self, cr, widget, background_area, cell_area, flags):
        Gtk.CellRendererToggle.do_render(
            self, cr, widget, background_area,
            _timeline_content_area(cell_area), flags)


class CellRendererFavorite(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererFavorite'

    _BADGE_MARGIN = style.zoom(14)

    def __init__(self, timeline):
        CellRendererIcon.__init__(self)

        height = _ROW_HEIGHT if timeline else style.GRID_CELL_SIZE
        self.props.width = height
        self.props.height = height
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'emblem-favorite'
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

        self.full_height = self.props.height

    def do_render(self, cr, widget, background_area, cell_area, flags):
        # Matches the kept-vs-not distinction drawn by keepicon.py.
        cell_area = _timeline_content_area(cell_area)
        CellRendererIcon.do_render(self, cr, widget, background_area,
                                   cell_area, flags)
        if not self.is_scrolling() and self.props.xo_color is not None:
            radius = (min(cell_area.width, cell_area.height) -
                      2 * self._BADGE_MARGIN) / 2.
            _paint_card_frame(cr, cell_area, self._BADGE_MARGIN, radius)


class _FoldAwareIconRenderer(CellRendererIcon):
    """do_render shared by CellRendererDetail and CellRendererBuddy: just
    clip the icon into the fold-aware content area."""

    def do_render(self, cr, widget, background_area, cell_area, flags):
        CellRendererIcon.do_render(self, cr, widget, background_area,
                                   _timeline_content_area(cell_area), flags)


class CellRendererDetail(_FoldAwareIconRenderer):
    __gtype_name__ = 'JournalCellRendererDetail'

    def __init__(self, timeline):
        CellRendererIcon.__init__(self)

        height = _ROW_HEIGHT if timeline else style.GRID_CELL_SIZE
        self.props.width = height
        self.props.height = height
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'go-right'
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE
        self.props.stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.prelit_stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.prelit_fill_color = style.COLOR_BLACK.get_svg()

        # Restored by BaseListView._apply_fold when a row stops being a sliver.
        self.full_height = self.props.height


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererActivityIcon'

    _FRAME_MARGIN = style.zoom(8)
    _FRAME_RADIUS = style.zoom(16)

    def __init__(self, timeline):
        CellRendererIcon.__init__(self)

        if timeline:
            self.props.width = _ROW_HEIGHT
            self.props.height = _ROW_HEIGHT
            self.props.size = style.zoom(64)
        else:
            self.props.width = style.GRID_CELL_SIZE
            self.props.height = style.GRID_CELL_SIZE
            self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

        # Restored by BaseListView._apply_fold when a row stops being a sliver.
        self.full_height = self.props.height

    def do_render(self, cr, widget, background_area, cell_area, flags):
        cell_area = _timeline_content_area(cell_area)
        CellRendererIcon.do_render(self, cr, widget, background_area,
                                   cell_area, flags)
        if not self.is_scrolling():
            _paint_card_frame(cr, cell_area, self._FRAME_MARGIN,
                              self._FRAME_RADIUS)


class CellRendererBuddy(_FoldAwareIconRenderer):
    __gtype_name__ = 'JournalCellRendererBuddy'

    def __init__(self, column_index):
        CellRendererIcon.__init__(self)

        self.props.width = style.STANDARD_ICON_SIZE
        self.props.height = style.STANDARD_ICON_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

        self._model_column_index = column_index
        self.nick = None

        self.full_height = self.props.height

    def set_buddy(self, buddy):
        if buddy is None:
            self.props.icon_name = None
            self.nick = None
        else:
            self.nick, xo_color = buddy
            self.props.icon_name = 'computer-xo'
            self.props.xo_color = xo_color

    buddy = GObject.Property(type=object, setter=set_buddy)
