# Copyright (C) 2008 One Laptop Per Child
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
import logging
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11

from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.graphics.alert import Alert, TimeoutAlert

from jarabe.model.session import get_session_manager
from jarabe.controlpanel.toolbar import MainToolbar
from jarabe.controlpanel.toolbar import SectionToolbar
from jarabe import config
from jarabe.model import shell

_logger = logging.getLogger('ControlPanel')


class ControlPanel(Gtk.Window):
    __gtype_name__ = 'SugarControlPanel'

    def __init__(self, window_xid=0):
        self.parent_window_xid = window_xid
        Gtk.Window.__init__(self)

        self._calculate_max_columns()
        self.set_border_width(style.LINE_WIDTH)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        self.set_can_focus(True)
        self.connect('key-press-event', self.__key_press_event_cb)

        self._toolbar = None
        self._canvas = None
        self._table = None
        self._scrolledwindow = None
        self._separator = None
        self._section_view = None
        self._section_toolbar = None
        self._main_toolbar = None

        self._vbox = Gtk.VBox()
        self._hbox = Gtk.HBox()
        self._vbox.pack_start(self._hbox, True, True, 0)
        self._hbox.show()

        self._main_view = Gtk.EventBox()
        self._hbox.pack_start(self._main_view, True, True, 0)
        self._main_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())
        self._main_view.show()

        self.add(self._vbox)
        self._vbox.show()

        self.connect('realize', self.__realize_cb)

        self._options = self._get_options()
        self._current_option = None
        self._setup_main()
        self._setup_section()
        self._show_main_view()
        Gdk.Screen.get_default().connect(
            'size-changed', self.__size_changed_cb)

        self._busy_count = 0
        self._selected = []

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)
        if self.parent_window_xid > 0:
            display = Gdk.Display.get_default()
            parent = GdkX11.X11Window.foreign_new_for_display(
                display, self.parent_window_xid)
            window.set_transient_for(parent)

        # the modal windows counter is updated to disable hot keys - SL#4601
        shell.get_model().push_modal()

    def __size_changed_cb(self, event):
        self._calculate_max_columns()

    def busy(self):
        if self._busy_count == 0:
            self._old_cursor = self.get_window().get_cursor()
            self._set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        self._busy_count += 1

    def unbusy(self):
        self._busy_count -= 1
        if self._busy_count == 0:
            self._set_cursor(self._old_cursor)

    def _set_cursor(self, cursor):
        self.get_window().set_cursor(cursor)
        Gdk.flush()

    def add_alert(self, alert):
        self._vbox.pack_start(alert, False, False, 0)
        self._vbox.reorder_child(alert, 2)

    def remove_alert(self, alert):
        self._vbox.remove(alert)

    def grab_focus(self):
        # overwrite grab focus in order to grab focus on the view
        self._main_view.get_child().grab_focus()

    def _calculate_max_columns(self):
        self._max_columns = int(0.285 * (float(Gdk.Screen.width()) /
                                         style.GRID_CELL_SIZE - 3))
        offset = style.GRID_CELL_SIZE
        width = Gdk.Screen.width() - offset * 2
        height = Gdk.Screen.height() - offset * 2
        self.set_size_request(width, height)
        if hasattr(self, '_table'):
            for child in self._table.get_children():
                child.destroy()
            self._setup_options()

    def _set_canvas(self, canvas):
        if self._canvas in self._main_view:
            self._main_view.remove(self._canvas)
        if canvas:
            self._main_view.add(canvas)
        self._canvas = canvas

    def _set_toolbar(self, toolbar):
        if self._toolbar:
            self._vbox.remove(self._toolbar)
        self._vbox.pack_start(toolbar, False, False, 0)
        self._vbox.reorder_child(toolbar, 0)
        self._toolbar = toolbar
        if not self._separator:
            self._separator = Gtk.HSeparator()
            self._vbox.pack_start(self._separator, False, False, 0)
            self._vbox.reorder_child(self._separator, 1)
            self._separator.show()

    def _setup_main(self):
        self._main_toolbar = MainToolbar()

        self._table = Gtk.Table()
        self._table.set_col_spacings(style.GRID_CELL_SIZE)
        self._table.set_row_spacings(style.GRID_CELL_SIZE)
        self._table.set_border_width(style.GRID_CELL_SIZE)

        self._scrolledwindow = Gtk.ScrolledWindow()
        self._scrolledwindow.set_can_focus(False)
        self._scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                        Gtk.PolicyType.AUTOMATIC)
        self._scrolledwindow.add_with_viewport(self._table)
        child = self._scrolledwindow.get_child()
        child.modify_bg(
            Gtk.StateType.NORMAL, style.COLOR_BLACK.get_gdk_color())

        self._setup_options()
        self._main_toolbar.connect('stop-clicked',
                                   self.__stop_clicked_cb)
        self._main_toolbar.connect('search-changed',
                                   self.__search_changed_cb)

    def _setup_options(self):
        # If the screen width only supports two columns, start
        # placing from the second row.
        if self._max_columns == 2:
            row = 1
            column = 0
        else:
            # About Me and About my computer are hardcoded below to use the
            # first two slots so we need to leave them free.
            row = 0
            column = 2

        options = self._options.keys()
        options.sort()

        for option in options:
            sectionicon = _SectionIcon(icon_name=self._options[option]['icon'],
                                       title=self._options[option]['title'],
                                       xo_color=self._options[option]['color'],
                                       pixel_size=style.GRID_CELL_SIZE)
            sectionicon.connect('button_press_event',
                                self.__select_option_cb, option)
            sectionicon.show()

            if option == 'aboutme':
                self._table.attach(sectionicon, 0, 1, 0, 1)
            elif option == 'aboutcomputer':
                self._table.attach(sectionicon, 1, 2, 0, 1)
            else:
                self._table.attach(sectionicon,
                                   column, column + 1,
                                   row, row + 1)
                column += 1
                if column == self._max_columns:
                    column = 0
                    row += 1

            self._options[option]['button'] = sectionicon

    def _show_main_view(self):
        if self._section_view is not None:
            self._section_view.destroy()
            self._section_view = None

        self._set_toolbar(self._main_toolbar)
        self._main_toolbar.show()
        self._set_canvas(self._scrolledwindow)
        self._main_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())
        self._table.show()
        self._scrolledwindow.show()
        entry = self._main_toolbar.get_entry()
        entry.set_text('')
        entry.connect('icon-press', self.__clear_icon_pressed_cb)
        self.grab_focus()

    def __key_press_event_cb(self, window, event):
        if event.keyval == Gdk.KEY_Return:
            if len(self._selected) == 1:
                self.show_section_view(self._selected[0])
                return True

        if event.keyval == Gdk.KEY_Escape:
            if self._toolbar == self._main_toolbar:
                self.__stop_clicked_cb(None)
                self.destroy()
            else:
                self.__cancel_clicked_cb(None)
            return True

        # if the user clicked out of the window - fix SL #3188
        if not self.is_active():
            self.present()

        entry = self._main_toolbar.get_entry()
        if not entry.has_focus():
            entry.grab_focus()
        return False

    def __clear_icon_pressed_cb(self, entry, icon_pos, event):
        self.grab_focus()

    def _update(self, query):
        self._selected = []
        for option in self._options:
            found = False
            for key in self._options[option]['keywords']:
                if query.lower() in key.lower():
                    self._options[option]['button'].set_sensitive(True)
                    self._selected.append(option)
                    found = True
                    break
            if not found:
                self._options[option]['button'].set_sensitive(False)

    def _setup_section(self):
        self._section_toolbar = SectionToolbar()
        self._section_toolbar.connect('cancel-clicked',
                                      self.__cancel_clicked_cb)
        self._section_toolbar.connect('accept-clicked',
                                      self.__accept_clicked_cb)

    def show_section_view(self, option):
        self._set_toolbar(self._section_toolbar)

        icon = self._section_toolbar.get_icon()
        icon.set_from_icon_name(self._options[option]['icon'],
                                Gtk.IconSize.LARGE_TOOLBAR)
        icon.props.xo_color = self._options[option]['color']
        title = self._section_toolbar.get_title()
        title.set_text(self._options[option]['title'])
        self._section_toolbar.show()

        self._current_option = option

        mod = __import__('.'.join(('cpsection', option, 'view')),
                         globals(), locals(), ['view'])
        view_class = getattr(mod, self._options[option]['view'], None)

        mod = __import__('.'.join(('cpsection', option, 'model')),
                         globals(), locals(), ['model'])
        model = ModelWrapper(mod)

        try:
            self.busy()
            self._section_view = view_class(model,
                                            self._options[option]['alerts'])

            self._set_canvas(self._section_view)
            self._section_view.show()
        finally:
            self.unbusy()

        self._section_view.connect('notify::is-valid',
                                   self.__valid_section_cb)
        self._section_view.connect('notify::is-cancellable',
                                   self.__cancellable_section_cb)
        self._section_view.connect('request-close',
                                   self.__close_request_cb)
        self._section_view.connect('add-alert',
                                   self.__create_restart_alert_cb)
        self._section_view.connect('set-toolbar-sensitivity',
                                   self.__set_toolbar_sensitivity_cb)
        self._main_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_WHITE.get_gdk_color())

    def set_section_view_auto_close(self):
        """Automatically close the control panel if there is "nothing to do"
        """
        self._section_view.auto_close = True

    def _get_options(self):
        """Get the available option information from the extensions
        """
        options = {}

        path = os.path.join(config.ext_path, 'cpsection')
        folder = os.listdir(path)

        for item in folder:
            if os.path.isdir(os.path.join(path, item)) and \
                    os.path.exists(os.path.join(path, item, '__init__.py')):
                try:
                    mod = __import__('.'.join(('cpsection', item)),
                                     globals(), locals(), [item])
                    view_class = getattr(mod, 'CLASS', None)
                    if view_class is not None:
                        options[item] = {}
                        options[item]['alerts'] = []
                        options[item]['view'] = view_class
                        options[item]['icon'] = getattr(mod, 'ICON', item)
                        options[item]['title'] = getattr(mod, 'TITLE', item)
                        options[item]['color'] = getattr(mod, 'COLOR', None)
                        keywords = getattr(mod, 'KEYWORDS', [])
                        keywords.append(options[item]['title'].lower())
                        if item not in keywords:
                            keywords.append(item)
                        options[item]['keywords'] = keywords
                    else:
                        _logger.debug('no CLASS attribute in %r', item)
                except Exception:
                    logging.exception('Exception while loading extension:')

        return options

    def __cancel_clicked_cb(self, widget):
        self._section_view.undo()
        self._options[self._current_option]['alerts'] = []
        self._section_toolbar.accept_button.set_sensitive(True)
        self._show_main_view()

    def __accept_clicked_cb(self, widget):
        if hasattr(self._section_view, "apply"):
            self._section_view.apply()

        if self._section_view.needs_restart:
            self.__set_toolbar_sensitivity_cb(False)
            if self._section_view.show_restart_alert:
                self.__create_restart_alert_cb()
        else:
            self._show_main_view()

    def __set_toolbar_sensitivity_cb(self, value=True,
                                     widget=None, event=None):
        self._section_toolbar.accept_button.set_sensitive(value)
        self._section_toolbar.cancel_button.set_sensitive(value)

    def __create_restart_alert_cb(self, widget=None, event=None):
        alert = Alert()
        alert.props.title = _('Warning')
        alert.props.msg = self._section_view.restart_msg

        if self._section_view.props.is_cancellable:
            icon = Icon(icon_name='dialog-cancel')
            alert.add_button(Gtk.ResponseType.CANCEL,
                             _('Cancel changes'), icon)
            icon.show()

        if self._section_view.props.is_deferrable:
            icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.ACCEPT, _('Later'), icon)
            icon.show()

        icon = Icon(icon_name='system-restart')
        alert.add_button(Gtk.ResponseType.APPLY, _('Restart now'), icon)
        icon.show()

        self.add_alert(alert)
        alert.connect('response', self.__response_cb)
        alert.show()

    def __response_cb(self, alert, response_id):
        self.remove_alert(alert)
        self._section_toolbar.accept_button.set_sensitive(True)
        self._section_toolbar.cancel_button.set_sensitive(True)
        if response_id is Gtk.ResponseType.CANCEL:
            self._section_view.undo()
            self._section_view.setup()
            self._options[self._current_option]['alerts'] = []
        elif response_id is Gtk.ResponseType.ACCEPT:
            self._options[self._current_option]['alerts'] = \
                self._section_view.restart_alerts
            self._show_main_view()
        elif response_id is Gtk.ResponseType.APPLY:
            self.busy()
            self._section_toolbar.accept_button.set_sensitive(False)
            self._section_toolbar.cancel_button.set_sensitive(False)
            get_session_manager().logout()
            GObject.timeout_add_seconds(4, self.__quit_timeout_cb)

    def __quit_timeout_cb(self):
        self.unbusy()
        alert = TimeoutAlert(30)
        alert.props.title = _('An activity is not responding.')
        alert.props.msg = _('You may lose unsaved work if you continue.')
        alert.connect('response', self.__quit_accept_cb)

        self.add_alert(alert)
        alert.show()

    def __quit_accept_cb(self, alert, response_id):
        self.remove_alert(alert)
        if response_id is Gtk.ResponseType.CANCEL:
            get_session_manager().cancel_shutdown()
            self._section_toolbar.accept_button.set_sensitive(True)
            self._section_toolbar.cancel_button.set_sensitive(True)
        else:
            self.busy()
            get_session_manager().shutdown_completed()

    def __select_option_cb(self, button, event, option):
        self.show_section_view(option)

    def __search_changed_cb(self, maintoolbar, query):
        self._update(query)

    def __stop_clicked_cb(self, widget):
        shell.get_model().pop_modal()
        self.destroy()

    def __close_request_cb(self, widget, event=None):
        self.destroy()

    def __valid_section_cb(self, section_view, pspec):
        section_is_valid = section_view.props.is_valid
        self._section_toolbar.accept_button.set_sensitive(section_is_valid)

    def __cancellable_section_cb(self, section_view, pspec):
        cancellable = section_view.props.is_cancellable
        self._section_toolbar.cancel_button.set_sensitive(cancellable)


class ModelWrapper(object):

    def __init__(self, module):
        self._module = module
        self._options = {}
        self._setup()

    def _setup(self):
        methods = dir(self._module)
        for method in methods:
            if method.startswith('get_') and method[4:] != 'color':
                try:
                    self._options[method[4:]] = getattr(self._module, method)()
                except Exception:
                    self._options[method[4:]] = None

    def __getattr__(self, name):
        return getattr(self._module, name)

    def undo(self):
        for key in self._options.keys():
            method = getattr(self._module, 'set_' + key, None)
            if method and self._options[key] is not None:
                try:
                    method(self._options[key])
                except Exception as detail:
                    _logger.debug('Error undo option: %s', detail)
if hasattr(ControlPanel, 'set_css_name'):
    ControlPanel.set_css_name('controlpanel')


class _SectionIcon(Gtk.EventBox):
    __gtype_name__ = 'SugarSectionIcon'

    __gproperties__ = {
        'icon-name': (str, None, None, None, GObject.PARAM_READWRITE),
        'pixel-size': (object, None, None, GObject.PARAM_READWRITE),
        'xo-color': (object, None, None, GObject.PARAM_READWRITE),
        'title': (str, None, None, None, GObject.PARAM_READWRITE),
    }

    def __init__(self, **kwargs):
        self._icon_name = None
        self._pixel_size = style.GRID_CELL_SIZE
        self._xo_color = None
        self._title = 'No Title'

        Gtk.EventBox.__init__(self, **kwargs)

        self._vbox = Gtk.VBox()
        self._icon = Icon(icon_name=self._icon_name,
                          pixel_size=self._pixel_size,
                          xo_color=self._xo_color)
        self._vbox.pack_start(self._icon, expand=False, fill=False, padding=0)

        self._label = Gtk.Label(label=self._title)
        self._label.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_WHITE.get_gdk_color())
        self._vbox.pack_start(self._label, expand=False, fill=False, padding=0)

        self._vbox.set_spacing(style.DEFAULT_SPACING)
        self.set_visible_window(False)
        self.set_app_paintable(True)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        self.add(self._vbox)
        self._vbox.show()
        self._label.show()
        self._icon.show()

    def get_icon(self):
        return self._icon

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            if self._icon_name != value:
                self._icon_name = value
        elif pspec.name == 'pixel-size':
            if self._pixel_size != value:
                self._pixel_size = value
        elif pspec.name == 'xo-color':
            if self._xo_color != value:
                self._xo_color = value
        elif pspec.name == 'title':
            if self._title != value:
                self._title = value

    def do_get_property(self, pspec):
        if pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'pixel-size':
            return self._pixel_size
        elif pspec.name == 'xo-color':
            return self._xo_color
        elif pspec.name == 'title':
            return self._title
