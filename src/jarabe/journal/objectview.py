# Copyright (C) 2009, Tomeu Vizoso, Aleksey Lim
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

import logging
from gettext import gettext as _
import time

import gobject
import gtk
import hippo

from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon, Icon

from jarabe.journal import model
from jarabe.journal.listview import ListView
from jarabe.journal.thumbsview import ThumbsView
from jarabe.journal.listmodel import ListModel
from jarabe.journal.objectmodel import ObjectModel
from jarabe.journal.source import Source, LocalSource

UPDATE_INTERVAL = 300

MESSAGE_EMPTY_JOURNAL = 0
MESSAGE_NO_MATCH = 1

VIEW_LIST = 0
VIEW_THUMBS = 1

VIEW_TYPES = [ListView, ThumbsView]

PAGE_SIZE = 10

class ObjectsView(gtk.Bin):
    __gsignals__ = {
        'clear-clicked': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([])),
        'detail-clicked': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([object])),
        'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE,
                            ([str])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._query = {}
        self._result_set = None
        self._progress_bar = None
        self._last_progress_bar_pulse = None
        self._model = ObjectModel()
        self._view_widgets = []
        self._view = VIEW_LIST

        self.connect('destroy', self.__destroy_cb)

        for view_class in VIEW_TYPES:
            view = view_class()
            view.modify_base(gtk.STATE_NORMAL,
                    style.COLOR_WHITE.get_gdk_color())
            view.connect('detail-clicked', self.__detail_clicked_cb)
            view.connect('button-release-event', self.__button_release_event_cb)
            view.show()

            widget = gtk.ScrolledWindow()
            widget.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            widget.show()
            widget.add(view)
            widget.view = view
            self._view_widgets.append(widget)

        # Auto-update stuff
        self._fully_obscured = True
        self._dirty = False
        self._refresh_idle_handler = None
        self._update_dates_timer = None

        model.created.connect(self.__model_created_cb)
        model.updated.connect(self.__model_updated_cb)
        model.deleted.connect(self.__model_deleted_cb)

    def set_hover_selection(self, hover_selection):
        for i in self._view_widgets:
            i.view.props.hover_selection = hover_selection

    hover_selection = gobject.property(type=bool, default=False,
            setter=set_hover_selection)

    def update_with_query(self, query_dict):
        logging.debug('ListView.update_with_query')
        self._query = query_dict

        if 'order_by' not in self._query:
            self._query['order_by'] = ['+timestamp']

        self._refresh()

    def update_dates(self):
        if self._view == VIEW_LIST:
            # TODO in 0.88 VIEW_LIST will use lazymodel
            self._view_widgets[VIEW_LIST].view.update_dates()
            return
        self._model.recalc([Source.FIELD_MODIFY_TIME])

    def change_view(self, view):
        if self._view_widgets[view].parent is not None:
            return
        self._view = view
        if self.child is not None:
            self.remove(self.child)
        self.add(self._view_widgets[view])
        self._view_widgets[view].show()
        if view == VIEW_LIST:
            # TODO in 0.88 VIEW_LIST will use lazymodel
            return
        self._model.view = self._view_widgets[view].view

    def set_is_visible(self, visible):
        logging.debug('canvas_visibility_notify_event_cb %r' % visible)
        if visible:
            self._fully_obscured = False
            if self._dirty:
                self._refresh()
            if self._update_dates_timer is None:
                logging.debug('Adding date updating timer')
                self._update_dates_timer = \
                        gobject.timeout_add_seconds(UPDATE_INTERVAL,
                                            self.__update_dates_timer_cb)
        else:
            self._fully_obscured = True
            if self._update_dates_timer is not None:
                logging.debug('Remove date updating timer')
                gobject.source_remove(self._update_dates_timer)
                self._update_dates_timer = None

    def _refresh(self):
        logging.debug('ListView._refresh query %r' % self._query)
        self._stop_progress_bar()

        if self._result_set is not None:
            self._result_set.stop()

        self._result_set = model.find(self._query, PAGE_SIZE)
        self._result_set.ready.connect(self.__result_set_ready_cb)
        self._result_set.progress.connect(self.__result_set_progress_cb)
        self._result_set.setup()

    def __result_set_ready_cb(self, **kwargs):
        self._stop_progress_bar()

        if self._result_set.length == 0:
            if self._is_query_empty():
                self._show_message(MESSAGE_EMPTY_JOURNAL)
            else:
                self._show_message(MESSAGE_NO_MATCH)
        else:
            # TODO in 0.88 VIEW_LIST will use lazymodel
            self._view_widgets[VIEW_LIST].view.set_model(
                    ListModel(self._result_set))
            self._model.source = LocalSource(self._result_set)
            self.change_view(self._view)

    def __result_set_progress_cb(self, **kwargs):
        if self._progress_bar is None:
            self._start_progress_bar()

        if time.time() - self._last_progress_bar_pulse > 0.05:
            if self._progress_bar is not None:
                self._progress_bar.pulse()
                self._last_progress_bar_pulse = time.time()

    def _is_query_empty(self):
        # FIXME: This is a hack, we shouldn't have to update this every time
        # a new search term is added.
        if self._query.get('query', '') or self._query.get('mime_type', '') or \
                self._query.get('keep', '') or self._query.get('mtime', '') or \
                self._query.get('activity', ''):
            return False
        else:
            return True

    def __model_created_cb(self, sender, **kwargs):
        self._set_dirty()

    def __model_updated_cb(self, sender, **kwargs):
        self._set_dirty()

    def __model_deleted_cb(self, sender, **kwargs):
        self._set_dirty()

    def __destroy_cb(self, widget):
        if self._result_set is not None:
            self._result_set.stop()

    def _start_progress_bar(self):
        alignment = gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0.5)
        if self.child is not None:
            self.remove(self.child)
        self.add(alignment)
        alignment.show()

        self._progress_bar = gtk.ProgressBar()
        self._progress_bar.props.pulse_step = 0.01
        self._last_progress_bar_pulse = time.time()
        alignment.add(self._progress_bar)
        self._progress_bar.show()

    def _stop_progress_bar(self):
        if self.child != self._progress_bar:
            return
        if self.child is not None:
            self.remove(self.child)
        self.add(self._view_widgets[self._view])
        self._view_widgets[self._view].show()
        self._progress_bar = None

    def _show_message(self, message):
        canvas = hippo.Canvas()
        if self.child is not None:
            self.remove(self.child)
        self.add(canvas)
        canvas.show()

        box = hippo.CanvasBox(orientation=hippo.ORIENTATION_VERTICAL,
                              background_color=style.COLOR_WHITE.get_int(),
                              yalign=hippo.ALIGNMENT_CENTER,
                              spacing=style.DEFAULT_SPACING,
                              padding_bottom=style.GRID_CELL_SIZE)
        canvas.set_root(box)

        icon = CanvasIcon(size=style.LARGE_ICON_SIZE,
                          icon_name='activity-journal',
                          stroke_color = style.COLOR_BUTTON_GREY.get_svg(),
                          fill_color = style.COLOR_TRANSPARENT.get_svg())
        box.append(icon)

        if message == MESSAGE_EMPTY_JOURNAL:
            text = _('Your Journal is empty')
        elif message == MESSAGE_NO_MATCH:
            text = _('No matching entries')
        else:
            raise ValueError('Invalid message')

        text = hippo.CanvasText(text=text,
                xalign=hippo.ALIGNMENT_CENTER,
                font_desc=style.FONT_BOLD.get_pango_desc(),
                color = style.COLOR_BUTTON_GREY.get_int())
        box.append(text)

        if message == MESSAGE_NO_MATCH:
            button = gtk.Button(label=_('Clear search'))
            button.connect('clicked', self.__clear_button_clicked_cb)
            button.props.image = Icon(icon_name='dialog-cancel',
                                      icon_size=gtk.ICON_SIZE_BUTTON)
            canvas_button = hippo.CanvasWidget(widget=button,
                                               xalign=hippo.ALIGNMENT_CENTER)
            box.append(canvas_button)

    def __clear_button_clicked_cb(self, button):
        self.emit('clear-clicked')

    def _set_dirty(self):
        if self._fully_obscured:
            self._dirty = True
        else:
            self._refresh()

    def __update_dates_timer_cb(self):
        self.update_dates()
        return True

    def __detail_clicked_cb(self, list_view, object_id):
        self.emit('detail-clicked', object_id)

    def __button_release_event_cb(self, tree_view, event):
        if not tree_view.props.hover_selection:
            return False

        if event.window != tree_view.get_bin_window():
            return False

        pos = tree_view.get_path_at_pos(event.x, event.y)
        if pos is None:
            return False

        path, column_, x_, y_ = pos
        uid = tree_view.get_model()[path][Source.FIELD_UID]
        self.emit('entry-activated', uid)

        return False

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        self.child.size_allocate(allocation)

    def do_size_request(self, requisition):
        requisition.width, requisition.height = self.child.size_request()
