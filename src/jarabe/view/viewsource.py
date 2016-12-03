# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2011 Walter Bender
# Copyright (C) 2014-15 Ignacio Rodriguez
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

import os
import shutil
import sys
import logging
from gettext import gettext as _

import gi
gi.require_version('GtkSource', '3.0')
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GtkSource
from gi.repository import GdkPixbuf
import dbus
from gi.repository import Gio

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.alert import Alert
from sugar3.graphics.alert import ConfirmationAlert
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.bundle.activitybundle import get_bundle_instance
from sugar3.datastore import datastore
from sugar3.env import get_user_activities_path
from sugar3 import mime

from jarabe.view import customizebundle

_EXCLUDE_EXTENSIONS = ('.pyc', '.pyo', '.so', '.o', '.a', '.la', '.mo', '~',
                       '.xo', '.tar', '.bz2', '.zip', '.gz')
_EXCLUDE_NAMES = ['.deps', '.libs']

_IMPORT_TYPES = {'sugar3': 3, 'from gi.repository import Gtk': 3,
                 'sugar.': 2, 'import pygtk': 2, 'pygtk.require': 2}

_SOURCE_FONT = Pango.FontDescription('Monospace %d' % style.FONT_SIZE)

_logger = logging.getLogger('ViewSource')


def _is_web_activity(bundle_path):
    activity_bundle = get_bundle_instance(bundle_path)
    return activity_bundle.get_command() == 'sugar-activity-web'


def _is_gtk3_activity(bundle_path, bundle_id):
    setup_py_path = os.path.join(bundle_path, 'setup.py')
    main_filename = '/'.join(bundle_id.split('.')[-1]) + '.py'
    main_file_path = os.path.join(bundle_path, main_filename)
    all_files = os.listdir(bundle_path)
    try_paths = [setup_py_path, main_file_path] + all_files

    for path in try_paths:
        if os.path.isfile(path):
            with open(path) as f:
                text = f.read()
                for sign in _IMPORT_TYPES:
                    if sign in text:
                        version = _IMPORT_TYPES[sign]
                        return version == 3

    # Fallback to assuming GTK3
    return True


def _get_toolkit_path(bundle_path, bundle_id):
    sugar_toolkit_path = None

    if _is_web_activity(bundle_path):
        sugar_web_path = os.path.join(bundle_path, 'lib', 'sugar-web')
        if os.path.exists(sugar_web_path):
            return sugar_web_path
        else:
            return None

    if _is_gtk3_activity(bundle_path, bundle_id):
        sugar_module = 'sugar3'
    else:
        sugar_module = 'sugar'

    for path in sys.path:
        if path.endswith(('site-packages', 'dist-packages')):
            sugar_toolkit_path = os.path.join(path, sugar_module)
            if os.path.exists(sugar_toolkit_path):
                return sugar_toolkit_path

    return None


def setup_view_source(activity):
    service = activity.get_service()
    if service is not None:
        try:
            service.HandleViewSource()
            return
        except dbus.DBusException as e:
            expected_exceptions = [
                'org.freedesktop.DBus.Error.UnknownMethod',
                'org.freedesktop.DBus.Python.NotImplementedError']
            if e.get_dbus_name() not in expected_exceptions:
                logging.exception('Exception occured in HandleViewSource():')
        except Exception:
            logging.exception('Exception occured in HandleViewSource():')

    window_xid = activity.get_xid()
    if window_xid is None:
        _logger.error('Activity without a window xid')
        return

    bundle_path = activity.get_bundle_path()
    bundle_id = activity.get_bundle_id()

    if activity.has_shell_window():
        _logger.debug('A window is already open for %s %s', window_xid,
                      bundle_path)
        return

    document_path = None
    if service is not None:
        try:
            document_path = service.GetDocumentPath()
        except dbus.DBusException as e:
            expected_exceptions = [
                'org.freedesktop.DBus.Error.UnknownMethod',
                'org.freedesktop.DBus.Python.NotImplementedError']
            if e.get_dbus_name() not in expected_exceptions:
                logging.exception('Exception occured in GetDocumentPath():')
        except Exception:
            logging.exception('Exception occured in GetDocumentPath():')

    if bundle_path is None and document_path is None:
        _logger.debug('Activity without bundle_path nor document_path')
        return

    sugar_toolkit_path = _get_toolkit_path(bundle_path, bundle_id)

    if sugar_toolkit_path is None:
        _logger.error("Path to toolkit not found.")

    view_source = ViewSource(window_xid, bundle_path, document_path,
                             sugar_toolkit_path, activity.get_title())
    activity.push_shell_window(view_source)
    view_source.connect('hide', activity.pop_shell_window)
    view_source.show()


class ViewSource(Gtk.Window):
    __gtype_name__ = 'SugarViewSource'

    def __init__(self, window_xid, bundle_path, document_path,
                 sugar_toolkit_path, title):
        Gtk.Window.__init__(self)

        _logger.debug('ViewSource paths: %r %r %r', bundle_path,
                      document_path, sugar_toolkit_path)

        self.set_modal(True)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)

        self._parent_window_xid = window_xid
        self._sugar_toolkit_path = sugar_toolkit_path
        self._gdk_window = self.get_root_window()

        self.connect('realize', self.__realize_cb)
        self.connect('destroy', self.__destroy_cb, document_path)
        self.connect('key-press-event', self.__key_press_event_cb)

        self._vbox = Gtk.VBox()
        self.add(self._vbox)
        self._vbox.show()

        toolbar = Toolbar(title, bundle_path, document_path,
                          sugar_toolkit_path)
        self._vbox.pack_start(toolbar, False, True, 0)
        toolbar.connect('stop-clicked', self.__stop_clicked_cb)
        toolbar.connect('source-selected', self.__source_selected_cb)
        toolbar.show()

        pane = Gtk.HPaned()
        self._vbox.pack_start(pane, True, True, 0)
        pane.show()

        self._selected_bundle_file = None
        self._selected_sugar_file = None
        file_name = ''

        activity_bundle = get_bundle_instance(bundle_path)
        command = activity_bundle.get_command()

        if _is_web_activity(bundle_path):
            file_name = 'index.html'

        elif len(command.split(' ')) > 1:
            name = command.split(' ')[1].split('.')[-1]
            tmppath = command.split(' ')[1].replace('.', '/')
            file_name = tmppath[0:-(len(name) + 1)] + '.py'

        if file_name:
            path = os.path.join(bundle_path, file_name)
            if os.path.exists(path):
                self._selected_bundle_file = path

        # Split the tree pane into two vertical panes, one of which
        # will be hidden
        tree_panes = Gtk.VPaned()
        tree_panes.show()

        self._bundle_source_viewer = FileViewer(bundle_path, file_name)
        self._bundle_source_viewer.connect('file-selected',
                                           self.__file_selected_cb)
        tree_panes.add1(self._bundle_source_viewer)
        self._bundle_source_viewer.show()

        self._sugar_source_viewer = None

        if sugar_toolkit_path is not None:
            if _is_web_activity(bundle_path):
                file_name = 'env.js'
            else:
                file_name = 'env.py'

            self._selected_sugar_file = os.path.join(sugar_toolkit_path,
                                                     file_name)

            self._sugar_source_viewer = FileViewer(sugar_toolkit_path,
                                                   file_name)

            self._sugar_source_viewer.connect('file-selected',
                                              self.__file_selected_cb)

            tree_panes.add2(self._sugar_source_viewer)
            self._sugar_source_viewer.hide()

        pane.add1(tree_panes)

        self._source_display = SourceDisplay()
        pane.add2(self._source_display)
        self._source_display.show()
        self._source_display.file_path = self._selected_bundle_file

        if document_path is not None:
            self._select_source(document_path)

    def add_alert(self, alert):
        self._vbox.pack_start(alert, False, False, 0)
        self._vbox.reorder_child(alert, 1)
        alert.show()

    def remove_alert(self, alert):
        self._vbox.remove(alert)

    def _calculate_char_width(self, char_count):
        widget = Gtk.Label(label='')
        context = widget.get_pango_context()
        pango_font = context.load_font(_SOURCE_FONT)
        metrics = pango_font.get_metrics()
        return Pango.PIXELS(metrics.get_approximate_char_width()) * char_count

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)

        display = Gdk.Display.get_default()
        parent = GdkX11.X11Window.foreign_new_for_display(
            display, self._parent_window_xid)
        window.set_transient_for(parent)

    def __stop_clicked_cb(self, widget):
        self.destroy()

    def __source_selected_cb(self, widget, path):
        self._select_source(path)

    def _select_source(self, path):
        if os.path.isfile(path):
            _logger.debug('_select_source called with file: %r', path)
            self._source_display.file_path = path
            self._bundle_source_viewer.hide()

            if self._sugar_source_viewer is not None:
                self._sugar_source_viewer.hide()

        elif path == self._sugar_toolkit_path:
            _logger.debug('_select_source called with sugar toolkit path: %r',
                          path)
            self._sugar_source_viewer.set_path(path)
            self._source_display.file_path = self._selected_sugar_file
            self._sugar_source_viewer.show()
            self._bundle_source_viewer.hide()
        else:
            _logger.debug('_select_source called with path: %r', path)
            self._bundle_source_viewer.set_path(path)
            self._source_display.file_path = self._selected_bundle_file
            self._bundle_source_viewer.show()

            if self._sugar_source_viewer is not None:
                self._sugar_source_viewer.hide()

    def __destroy_cb(self, window, document_path):
        if document_path is not None and os.path.exists(document_path):
            os.unlink(document_path)

        self._gdk_window.set_cursor(Gdk.Cursor(Gdk.CursorType.LEFT_PTR))

    def __key_press_event_cb(self, window, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.destroy()

    def __file_selected_cb(self, file_viewer, file_path):
        if file_path is not None and os.path.isfile(file_path):
            self._source_display.file_path = file_path
            if file_viewer == self._bundle_source_viewer:
                self._selected_bundle_file = file_path
            else:
                self._selected_sugar_file = file_path
        else:
            self._source_display.file_path = None


class DocumentButton(RadioToolButton):
    __gtype_name__ = 'SugarDocumentButton'

    def __init__(self, file_name, document_path, activity_name, title,
                 bundle=False):
        RadioToolButton.__init__(self)

        self._document_path = document_path
        self._title = title
        self._jobject = None
        self._activity_name = activity_name

        self.props.tooltip = _('Instance Source')

        settings = Gio.Settings('org.sugarlabs.user')
        self._color = settings.get_string('color')
        icon = Icon(file=file_name,
                    pixel_size=style.STANDARD_ICON_SIZE,
                    xo_color=XoColor(self._color))
        self.set_icon_widget(icon)
        icon.show()

        box = PaletteMenuBox()
        self.props.palette.set_content(box)
        box.show()

        if bundle:
            menu_item = PaletteMenuItem(_('Duplicate'), 'edit-duplicate',
                                        xo_color=XoColor(self._color))
            menu_item.connect('activate', self.__show_duplicate_alert)
        else:
            menu_item = PaletteMenuItem(_('Keep'), 'document-save',
                                        xo_color=XoColor(self._color))
            menu_item.connect('activate', self.__keep_in_journal_cb)

        box.append_item(menu_item)
        menu_item.show()

    def __show_duplicate_alert(self, menu_item):
        alert = ConfirmationAlert()
        alert.props.title = _('Do you want to duplicate %s Activity?') % \
            self._activity_name
        alert.props.msg = _('This may take a few minutes')
        alert.connect('response', self.__duplicate_alert_response_cb)
        self.get_toplevel().add_alert(alert)

    def __duplicate_alert_response_cb(self, alert, response_id):
        self.get_toplevel().remove_alert(alert)

        if response_id == Gtk.ResponseType.OK:
            self.__set_busy_cursor(True)

            def internal_callback(new_alert):
                self.__copy_to_home_cb(None, new_alert)

            new_alert = Alert()
            new_alert.props.title = _("Duplicating activity...")

            self.get_toplevel().add_alert(new_alert)
            GObject.idle_add(internal_callback, new_alert)

    def __set_busy_cursor(self, busy):
        cursor = None

        if busy:
            cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        else:
            cursor = Gdk.Cursor(Gdk.CursorType.LEFT_PTR)

        gdk_window = self.get_root_window()
        gdk_window.set_cursor(cursor)

    def __copy_to_home_cb(self, menu_item, copy_alert=None):
        """Make a local copy of the activity bundle in user_activities_path"""
        user_activities_path = get_user_activities_path()
        nick = customizebundle.generate_unique_id()
        new_basename = '%s_copy_of_%s' % (
            nick, os.path.basename(self._document_path))
        if not os.path.exists(os.path.join(user_activities_path,
                                           new_basename)):
            self.__set_busy_cursor(True)

            def async_copy_activity_tree():
                try:
                    shutil.copytree(self._document_path,
                                    os.path.join(
                                        user_activities_path,
                                        new_basename),
                                    symlinks=True)
                    customizebundle.generate_bundle(nick, new_basename)

                    if copy_alert:
                        self.get_toplevel().remove_alert(copy_alert)

                    alert = NotifyAlert(10)
                    alert.props.title = _('Duplicated')
                    alert.props.msg = _('The activity has been duplicated')
                    alert.connect('response', self.__alert_response_cb)
                    self.get_toplevel().add_alert(alert)
                finally:
                    self.__set_busy_cursor(False)

            GObject.idle_add(async_copy_activity_tree)
        else:
            if copy_alert:
                self.get_toplevel().remove_alert(copy_alert)

            self.__set_busy_cursor(False)

            alert = NotifyAlert(10)
            alert.props.title = _('Duplicated activity already exists')
            alert.props.msg = _('Delete your copy before trying to duplicate'
                                ' the activity again')

            alert.connect('response', self.__alert_response_cb)
            self.get_toplevel().add_alert(alert)

    def __alert_response_cb(self, alert, response_id):
        self.get_toplevel().remove_alert(alert)

    def __keep_in_journal_cb(self, menu_item):
        mime_type = mime.get_from_file_name(self._document_path)
        if mime_type == 'application/octet-stream':
            mime_type = mime.get_for_file(self._document_path)

        self._jobject = datastore.create()
        title = _('Source') + ': ' + self._title
        self._jobject.metadata['title'] = title
        self._jobject.metadata['keep'] = '0'
        self._jobject.metadata['buddies'] = ''
        self._jobject.metadata['preview'] = ''
        self._jobject.metadata['icon-color'] = self._color
        self._jobject.metadata['mime_type'] = mime_type
        self._jobject.metadata['source'] = '1'
        self._jobject.file_path = self._document_path
        datastore.write(self._jobject, transfer_ownership=True,
                        reply_handler=self.__internal_save_cb,
                        error_handler=self.__internal_save_error_cb)

    def __internal_save_cb(self):
        _logger.debug('Saved Source object to datastore.')
        self._jobject.destroy()

    def __internal_save_error_cb(self, err):
        _logger.debug('Error saving Source object to datastore: %s', err)
        self._jobject.destroy()


class Toolbar(Gtk.Toolbar):
    __gtype_name__ = 'SugarViewSourceToolbar'

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'source-selected': (GObject.SignalFlags.RUN_FIRST, None,
                            ([str])),
    }

    def __init__(self, title, bundle_path, document_path, sugar_toolkit_path):
        Gtk.Toolbar.__init__(self)

        document_button = None
        self.bundle_path = bundle_path
        self.sugar_toolkit_path = sugar_toolkit_path

        self._add_separator()

        activity_bundle = get_bundle_instance(bundle_path)
        file_name = activity_bundle.get_icon()
        activity_name = activity_bundle.get_name()

        if document_path is not None and os.path.exists(document_path):
            document_button = DocumentButton(file_name, document_path,
                                             activity_name, title)
            document_button.connect('toggled', self.__button_toggled_cb,
                                    document_path)
            self.insert(document_button, -1)
            document_button.show()
            self._add_separator()

        if bundle_path is not None and os.path.exists(bundle_path):
            activity_button = DocumentButton(file_name, bundle_path,
                                             activity_name, title, bundle=True)
            icon = Icon(file=file_name,
                        pixel_size=style.STANDARD_ICON_SIZE,
                        fill_color=style.COLOR_TRANSPARENT.get_svg(),
                        stroke_color=style.COLOR_WHITE.get_svg())
            activity_button.set_icon_widget(icon)
            icon.show()
            if document_button is not None:
                activity_button.props.group = document_button
            activity_button.props.tooltip = _('Activity Bundle Source')
            activity_button.connect('toggled', self.__button_toggled_cb,
                                    bundle_path)
            self.insert(activity_button, -1)
            activity_button.show()
            self._add_separator()

        if sugar_toolkit_path is not None:
            sugar_button = RadioToolButton()
            icon = Icon(icon_name='computer-xo',
                        pixel_size=style.STANDARD_ICON_SIZE,
                        fill_color=style.COLOR_TRANSPARENT.get_svg(),
                        stroke_color=style.COLOR_WHITE.get_svg())
            sugar_button.set_icon_widget(icon)
            icon.show()
            if document_button is not None:
                sugar_button.props.group = document_button
            else:
                sugar_button.props.group = activity_button
            sugar_button.props.tooltip = _('Sugar Toolkit Source')
            sugar_button.connect('toggled', self.__button_toggled_cb,
                                 sugar_toolkit_path)
            self.insert(sugar_button, -1)
            sugar_button.show()
            self._add_separator()

        self.activity_title_text = _('View source: %s') % title
        self.sugar_toolkit_title_text = _('View source: %r') % 'Sugar Toolkit'
        self.label = Gtk.Label()
        self.label.set_markup('<b>%s</b>' % self.activity_title_text)
        self.label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        self.label.set_alignment(0, 0.5)
        self._add_widget(self.label, expand=True)

        self._add_separator(False)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Close'))
        stop.connect('clicked', self.__stop_clicked_cb)
        self.insert(stop, -1)
        stop.show()

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.insert(separator, -1)
        separator.show()

    def _add_widget(self, widget, expand=False):
        tool_item = Gtk.ToolItem()
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
        if path == self.sugar_toolkit_path:
            self.label.set_markup('<b>%s</b>' % self.sugar_toolkit_title_text)
        else:  # Use activity title for either bundle path or document path
            self.label.set_markup('<b>%s</b>' % self.activity_title_text)


class FileViewer(Gtk.ScrolledWindow):
    __gtype_name__ = 'SugarFileViewer'

    __gsignals__ = {
        'file-selected': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          ([str])),
    }

    def __init__(self, path, initial_filename):
        Gtk.ScrolledWindow.__init__(self)

        self.props.hscrollbar_policy = Gtk.PolicyType.AUTOMATIC
        self.props.vscrollbar_policy = Gtk.PolicyType.AUTOMATIC
        self.set_size_request(style.GRID_CELL_SIZE * 3, -1)

        self._path = None
        self._initial_filename = initial_filename

        self._tree_view = Gtk.TreeView()
        self._tree_view.connect('cursor-changed', self.__cursor_changed_cb)
        self.add(self._tree_view)
        self._tree_view.show()

        self._tree_view.props.headers_visible = False
        selection = self._tree_view.get_selection()
        selection.connect('changed', self.__selection_changed_cb)

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn()
        column.pack_start(cell, True)
        column.add_attribute(cell, 'text', 0)
        self._tree_view.append_column(column)
        self._tree_view.set_search_column(0)

        self.set_path(path)

    def set_path(self, path):
        self.emit('file-selected', None)
        if self._path == path:
            return

        self._path = path
        self._tree_view.set_model(Gtk.TreeStore(str, str))
        self._model = self._tree_view.get_model()
        self._add_dir_to_model(path)

    def _add_dir_to_model(self, dir_path, parent=None):
        for f in os.listdir(dir_path):
            if f.endswith(_EXCLUDE_EXTENSIONS) or f in _EXCLUDE_NAMES:
                continue

            full_path = os.path.join(dir_path, f)
            if os.path.isdir(full_path):
                new_iter = self._model.append(parent, [f, full_path])
                self._add_dir_to_model(full_path, new_iter)
            else:
                current_iter = self._model.append(parent, [f, full_path])
                if f == self._initial_filename:
                    selection = self._tree_view.get_selection()
                    selection.select_iter(current_iter)

    def __selection_changed_cb(self, selection):
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            file_path = None
        else:
            file_path = model.get_value(tree_iter, 1)
        self.emit('file-selected', file_path)

    def __cursor_changed_cb(self, treeview):
        selection = treeview.get_selection()
        if selection is None:
            return
        store, iter_ = selection.get_selected()
        if iter_ is None:
            # Nothing selected. This happens at startup
            return
        if store.iter_has_child(iter_):
            path = store.get_path(iter_)
            if treeview.row_expanded(path):
                treeview.collapse_row(path)
            else:
                treeview.expand_row(path, False)


class SourceDisplay(Gtk.ScrolledWindow):
    __gtype_name__ = 'SugarSourceDisplay'

    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)

        self.props.hscrollbar_policy = Gtk.PolicyType.AUTOMATIC
        self.props.vscrollbar_policy = Gtk.PolicyType.AUTOMATIC

        self._file_path = None

    def _replace(self, child):
        self._remove_children()
        self.add(child)

    def _replace_with_viewport(self, child):
        self._remove_children()
        self.add_with_viewport(child)

    def _remove_children(self):
        for child in self.get_children():
            self.remove(child)

    def _set_file_path(self, file_path):
        self._file_path = file_path

        if self._file_path is None:
            self._show_no_file()
            return

        mime_type = mime.get_for_file(self._file_path)
        if 'image/' in mime_type:
            self._show_image_viewer(image=True)
        elif 'audio/' in mime_type:
            self._show_image_viewer(icon='audio-x-generic')
        elif 'video/' in mime_type:
            self._show_image_viewer(icon='video-x-generic')
        else:
            response = self._show_text_viewer()
            if not response:
                self._show_image_viewer(icon='application-x-generic')

    def _show_text_viewer(self):
        source_buffer = GtkSource.Buffer()
        source_buffer.set_highlight_syntax(True)

        source_view = GtkSource.View(buffer=source_buffer)
        source_view.set_editable(False)
        source_view.set_cursor_visible(True)
        source_view.set_show_line_numbers(True)
        source_view.set_show_right_margin(True)
        source_view.set_right_margin_position(80)
        source_view.modify_font(_SOURCE_FONT)
        # source_view.set_highlight_current_line(True) #FIXME: Ugly color

        mime_type = mime.get_for_file(self._file_path)

        _logger.debug('Detected mime type: %r', mime_type)

        language_manager = GtkSource.LanguageManager.get_default()
        detected_language = None
        for language_id in language_manager.get_language_ids():
            language = language_manager.get_language(language_id)
            if mime_type in language.get_mime_types():
                detected_language = language
                break

        if detected_language is not None:
            _logger.debug('Detected language: %r',
                          detected_language.get_name())

        source_buffer.set_language(detected_language)
        text = open(self._file_path, 'r').read()
        try:
            text.encode()
            source_buffer.set_text(text)
        except UnicodeDecodeError:
            return False

        source_view.show()
        self._replace(source_view)

        return True

    def _get_file_path(self):
        return self._file_path

    file_path = property(_get_file_path, _set_file_path)

    def _show_image_viewer(self, icon=None, image=False):
        media_box = ImageBox()

        if image:
            image = Gtk.Image()
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self._file_path)
            image.set_from_pixbuf(pixbuf)
            media_box.add(image)

        if icon:
            h = Gdk.Screen.width() / 3
            icon = Icon(icon_name=icon, pixel_size=h)
            media_box.add(icon)

        media_box.show_all()
        self._replace_with_viewport(media_box)

    def _show_no_file(self):
        nofile_label = Gtk.Label()
        nofile_label.set_text(_("Please select a file in the left panel."))

        nofile_box = Gtk.EventBox()
        nofile_box.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('white'))

        nofile_box.add(nofile_label)
        nofile_box.show_all()
        self._replace_with_viewport(nofile_box)


class ImageBox(Gtk.EventBox):
    __gtype_name__ = 'SugarViewSourceImageBox'

    def __init__(self):
        Gtk.EventBox.__init__(self)
