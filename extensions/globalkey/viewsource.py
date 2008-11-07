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

import os
import logging
import traceback
from gettext import gettext as _

import gobject
import pango
import gtk
import gtksourceview2
import dbus

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar import mime

from jarabe.model import shell

BOUND_KEYS = ['0xEC', '<alt><shift>v']

_SOURCE_FONT = pango.FontDescription('Monospace %d' % style.zoom(6))

_logger = logging.getLogger('ViewSource')
map_activity_to_window = {}

def handle_key_press(key):
    shell_model = shell.get_model()
    activity = shell_model.get_active_activity()

    service = activity.get_service()
    if service is not None:
        try:
            service.HandleViewSource()
            return
        except dbus.DBusException, e:
            expected_exceptions = ['org.freedesktop.DBus.Error.UnknownMethod',
                    'org.freedesktop.DBus.Python.NotImplementedError']
            if e.get_dbus_name() not in expected_exceptions:
                logging.error(traceback.format_exc())
        except Exception:
            logging.error(traceback.format_exc())

    window_xid = activity.get_xid()
    if window_xid is None:
        _logger.error('Activity without a window xid')
        return

    if window_xid in map_activity_to_window:
        _logger.debug('Viewsource window already open for %s %s' % \
                (window_xid, bundle_path))
        return

    bundle_path = activity.get_bundle_path()

    document_path = None
    if service is not None:
        try:
            document_path = service.GetDocumentPath()
        except dbus.DBusException, e:
            expected_exceptions = ['org.freedesktop.DBus.Error.UnknownMethod',
                    'org.freedesktop.DBus.Python.NotImplementedError']
            if e.get_dbus_name() not in expected_exceptions:
                logging.error(traceback.format_exc())
        except Exception:
            logging.error(traceback.format_exc())

    if bundle_path is None and document_path is None:
        _logger.debug('Activity without bundle_path nor document_path')
        return

    view_source = ViewSource(window_xid, bundle_path, document_path,
                             activity.get_title())
    map_activity_to_window[window_xid] = view_source
    view_source.show()

class ViewSource(gtk.Window):
    __gtype_name__ = 'SugarViewSource'

    def __init__(self, window_xid, bundle_path, document_path, title):
        gtk.Window.__init__(self)

        logging.debug('ViewSource paths: %r %r' % (bundle_path, document_path))

        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)

        width = gtk.gdk.screen_width() - style.GRID_CELL_SIZE * 2
        height = gtk.gdk.screen_height() - style.GRID_CELL_SIZE * 2        
        self.set_size_request(width, height)

        self._parent_window_xid = window_xid

        self.connect('realize', self.__realize_cb)
        self.connect('destroy', self.__destroy_cb, document_path)
        self.connect('key-press-event', self.__key_press_event_cb)

        vbox = gtk.VBox()
        self.add(vbox)
        vbox.show()

        toolbar = Toolbar(title, bundle_path, document_path)
        vbox.pack_start(toolbar, expand=False)
        toolbar.connect('stop-clicked', self.__stop_clicked_cb)
        toolbar.connect('source-selected', self.__source_selected_cb)
        toolbar.show()

        hbox = gtk.HBox()
        vbox.pack_start(hbox)
        hbox.show()

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_size_request(style.GRID_CELL_SIZE * 3, -1)
        hbox.pack_start(scrolled_window, expand=False)
        scrolled_window.show()
        
        self._file_viewer = FileViewer(bundle_path)
        self._file_viewer.connect('file-selected', self.__file_selected_cb)
        scrolled_window.add(self._file_viewer)
        self._file_viewer.show()

        scrolled_window = gtk.ScrolledWindow()
        #scrolled_window.set_size_request(self._calculate_char_width(80), -1)
        hbox.pack_start(scrolled_window, expand=True)
        scrolled_window.show()

        self._source_display = SourceDisplay()
        scrolled_window.add(self._source_display)
        self._source_display.show()

    def _calculate_char_width(self, char_count):
        widget = gtk.Label('')
        context = widget.get_pango_context()
        pango_font = context.load_font(_SOURCE_FONT)
        metrics = pango_font.get_metrics()
        return pango.PIXELS(metrics.get_approximate_char_width()) * char_count

    def __realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(True)

        parent = gtk.gdk.window_foreign_new(self._parent_window_xid)
        self.window.set_transient_for(parent)

    def __stop_clicked_cb(self, widget):
        self.destroy()

    def __source_selected_cb(self, widget, path):
        if os.path.isfile(path):
            self._source_display.file_path = path
            self._file_viewer.get_parent().hide()
        else:
            self._file_viewer.set_path(path)
            self._file_viewer.get_parent().show()

    def __destroy_cb(self, window, document_path):
        del map_activity_to_window[self._parent_window_xid]
        if document_path is not None and os.path.exists(document_path):
            os.unlink(document_path)

    def __key_press_event_cb(self, window, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.destroy()

    def __file_selected_cb(self, file_viewer, file_path):
        if file_path is not None and os.path.isfile(file_path):
            self._source_display.file_path = file_path
        else:
            self._source_display.file_path = None
    
class Toolbar(gtk.Toolbar):
    __gtype_name__ = 'SugarViewSourceToolbar'

    __gsignals__ = {
        'stop-clicked':    (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE,
                            ([])),
        'source-selected': (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE,
                            ([str])),
    }

    def __init__(self, title, bundle_path, document_path):
        gtk.Toolbar.__init__(self)

        text = _('View source: %r') % title
        label = gtk.Label()
        label.set_markup('<b>%s</b>' % text)
        label.set_alignment(0, 0.5)
        self._add_widget(label)

        if bundle_path is not None and document_path is not None and \
                os.path.exists(bundle_path) and os.path.exists(document_path):
            activity_button = RadioToolButton(named_icon='printer')
            activity_button.props.tooltip = _('Activity')
            activity_button.connect('toggled', self.__button_toggled_cb, bundle_path)
            self.insert(activity_button, -1)
            activity_button.show()

            document_button = RadioToolButton(named_icon='view-radial')
            document_button.props.tooltip = _('Document')
            document_button.props.group = activity_button
            document_button.connect('toggled', self.__button_toggled_cb, document_path)
            self.insert(document_button, -1)
            document_button.show()

        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Close'))
        stop.connect('clicked', self.__stop_clicked_cb)
        stop.show()
        self.insert(stop, -1)
        stop.show()

    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def __stop_clicked_cb(self, button):
        self.emit('stop-clicked')

    def __button_toggled_cb(self, button, path):
        if button.props.active:
            self.emit('source-selected', path)

class FileViewer(gtk.TreeView):
    __gtype_name__ = 'SugarFileViewer'

    __gsignals__ = {
        'file-selected': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([str])),
    }

    def __init__(self, path):
        gtk.TreeView.__init__(self)

        self._path = None

        self.props.headers_visible = False
        self.get_selection().connect('changed', self.__selection_changed_cb)
        
        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn()
        column.pack_start(cell, True)
        column.add_attribute(cell, 'text', 0)
        self.append_column(column)
        self.set_search_column(0)

        self.set_path(path)

    def set_path(self, path):
        self.emit('file-selected', None)
        if self._path == path:
            return
        self._path = path
        self.set_model(gtk.TreeStore(str, str))
        self._add_dir_to_model(path)

    def _add_dir_to_model(self, dir_path, parent=None):
        model = self.get_model()
        for f in os.listdir(dir_path):
            full_path = os.path.join(dir_path, f)
            if os.path.isdir(full_path):
                new_iter = model.append(parent, [f, full_path])
                self._add_dir_to_model(full_path, new_iter)
            else:
                model.append(parent, [f, full_path])

    def __selection_changed_cb(self, selection):
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            file_path = None
        else:
            file_path = model.get_value(tree_iter, 1)
        self.emit('file-selected', file_path)

class SourceDisplay(gtksourceview2.View):
    __gtype_name__ = 'SugarSourceDisplay'

    def __init__(self):
        self._buffer = gtksourceview2.Buffer()
        gtksourceview2.View.__init__(self, self._buffer)

        self._buffer.set_highlight_syntax(True)
        self._file_path = None

        self.set_editable(False)
        self.set_cursor_visible(True)
        self.set_show_line_numbers(True)
        self.set_show_right_margin(True)
        self.set_right_margin_position(80)
        
        # TODO: Activate again when we get a better style scheme
        #self.set_highlight_current_line(True)

        self.modify_font(_SOURCE_FONT)

    def _set_file_path(self, file_path):
        if file_path == self._file_path:
            return
        self._file_path = file_path
        
        if self._file_path is None:
            self._buffer.set_text('')
            return

        mime_type = mime.get_for_file(self._file_path)
        logging.debug('Detected mime type: %r' % mime_type)

        language_manager = gtksourceview2.language_manager_get_default()
        detected_language = None
        for language_id in language_manager.get_language_ids():
            language = language_manager.get_language(language_id)
            if mime_type in language.get_mime_types():
                detected_language = language
                break

        if detected_language is not None:
            logging.debug('Detected language: %r' % \
                    detected_language.get_name())

        self._buffer.set_language(detected_language)
        self._buffer.set_text(open(self._file_path, 'r').read())

    def _get_file_path(self):
        return self._file_path

    file_path = property(_get_file_path, _set_file_path)

