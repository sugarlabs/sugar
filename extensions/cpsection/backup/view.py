# Copyright (C) 2013, SugarLabs
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

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor


from jarabe.controlpanel.sectionview import SectionView

from backupmanager import BackupManager
from backupmanager import OPERATION_BACKUP, OPERATION_RESTORE
from backends.backend_tools import PreConditionsError
from backends.backend_tools import PreConditionsChoose


class BackupView(SectionView):
    __gtype_name__ = 'SugarBackupWindow'

    def __init__(self, model, alerts=None):
        SectionView.__init__(self)
        self.needs_restart = False
        self.props.is_deferrable = False

        # add the initial panel
        self.set_canvas(SelectBackupRestorePanel(self))
        self.grab_focus()
        self.show_all()
        self.manager = BackupManager()

    def set_canvas(self, canvas):
        if len(self.get_children()) > 0:
            self.remove(self.get_children()[0])
        if canvas:
            self.add(canvas)

    def undo(self):
        if self.get_children()[0].__class__ == OperationPanel:
            operation_panel = self.get_children()[0]
            if operation_panel._operator is not None:
                operation_panel._operator.cancel()


class _BackupButton(Gtk.EventBox):

    __gproperties__ = {
        'icon-name': (str, None, None, None, GObject.PARAM_READWRITE),
        'pixel-size': (object, None, None, GObject.PARAM_READWRITE),
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
                          xo_color=XoColor('#000000,#000000'))
        self._vbox.pack_start(self._icon, expand=False, fill=False, padding=0)

        self._label = Gtk.Label(label=self._title)
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
        elif pspec.name == 'title':
            if self._title != value:
                self._title = value

    def do_get_property(self, pspec):
        if pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'pixel-size':
            return self._pixel_size
        elif pspec.name == 'title':
            return self._title


class SelectBackupRestorePanel(Gtk.VBox):

    def __init__(self, view):
        Gtk.VBox.__init__(self)

        self._view = view
        hbox = Gtk.HBox()

        self.backup_btn = _BackupButton(
            icon_name='backup-backup',
            title=_('Save the contents of your Journal'),
            pixel_size=style.GRID_CELL_SIZE)
        self.backup_btn.connect('button_press_event',
                                self.__backup_button_press_cb)
        hbox.pack_start(self.backup_btn, False, False, style.DEFAULT_SPACING)

        self.restore_btn = _BackupButton(
            icon_name='backup-restore',
            title=_('Restore the contents of your Journal'),
            pixel_size=style.GRID_CELL_SIZE)
        self.restore_btn.connect('button_press_event',
                                 self.__restore_button_press_cb)
        hbox.pack_start(self.restore_btn, False, False, style.DEFAULT_SPACING)

        hbox.set_valign(Gtk.Align.CENTER)
        hbox.set_halign(Gtk.Align.CENTER)
        self.add(hbox)
        self.show_all()

    def __backup_button_press_cb(self, button, event):
        operation_panel = OperationPanel(OPERATION_BACKUP, self._view)
        self._view.set_canvas(operation_panel)

    def __restore_button_press_cb(self, button, event):
        operation_panel = OperationPanel(OPERATION_RESTORE, self._view)
        self._view.set_canvas(operation_panel)


class OperationPanel(Gtk.Grid):

    def __init__(self, operation, view):
        Gtk.Grid.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_row_spacing(style.DEFAULT_SPACING)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)

        self._view = view
        self._operation = operation
        self._backend = None

        _icon = Icon(icon_name='backup-%s' % operation,
                     pixel_size=style.XLARGE_ICON_SIZE)
        self.add(_icon)
        _icon.show()

        self._message_label = Gtk.Label()
        self._message_label.set_line_wrap(True)
        self._message_label.set_width_chars(40)
        self._message_label.set_single_line_mode(False)
        align = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        align.set_padding(0, 0, style.GRID_CELL_SIZE * 2,
                          style.GRID_CELL_SIZE * 2)
        align.show()
        align.add(self._message_label)
        self.add(align)
        self._message_label.show()

        self._options_combo = Gtk.ComboBox()
        cell = Gtk.CellRendererText()
        self._options_combo.pack_start(cell, True)
        self._options_combo.add_attribute(cell, 'text', 0)
        self.add(self._options_combo)

        self._progress_bar = Gtk.ProgressBar()
        self.add(self._progress_bar)
        self._progress_bar.set_size_request(
            Gdk.Screen.width() - style.GRID_CELL_SIZE * 6, -1)

        self._confirm_restore_chkbtn = Gtk.CheckButton()
        align = Gtk.Alignment()
        align.set_padding(0, 0, style.GRID_CELL_SIZE * 2,
                          style.GRID_CELL_SIZE * 2)
        align.show()
        align.add(self._confirm_restore_chkbtn)
        self.add(align)

        btn_box = Gtk.ButtonBox()
        btn_box.show()
        self._continue_btn = Gtk.Button(_('Continue'))
        btn_box.add(self._continue_btn)
        self.add(btn_box)
        self._continue_btn_handler_id = 0

        self.show()

        # check if there are activities running
        # and request close them if any.
        if self._view.manager.need_stop_activities():
            self._message_label.set_text(
                _('Please close all the activities, and start again'))

        # check the backend availables, if there are more than one
        # show to the user to select one
        if len(self._view.manager.get_backends()) > 1:
            if operation == OPERATION_BACKUP:
                message = _('Select where you want create your backup')
            if operation == OPERATION_RESTORE:
                message = _('Select where you want retrieve your restore')
            combo_options = []
            for backend in self._view.manager.get_backends():
                option = {}
                option['description'] = backend.get_name()
                option['value'] = backend
                combo_options.append(option)

            self._ask_options(message, combo_options, self._select_backend)
        else:
            self._backend = self._view.manager.get_backends()[0]
            GObject.idle_add(self._start_operation)

    def _ask_options(self, message, options, continue_cb):
        """
        message: str
        options: dictionary
        continue_cb: the call back method to assign to the continue button
                     clicked event.
        """
        self._message_label.set_text(message)
        options_store = Gtk.ListStore(GObject.TYPE_STRING,
                                      GObject.TYPE_PYOBJECT)
        for option in options:
            options_store.append([option['description'], option['value']])
        self._options_combo.set_model(options_store)

        self._options_combo.show()

        if self._continue_btn_handler_id != 0:
            self._continue_btn.disconnect(self._continue_btn_handler_id)

        self._continue_btn_handler_id = self._continue_btn.connect(
            'clicked', continue_cb)
        self._continue_btn.set_label(_('Continue'))
        self._continue_btn.show()

    def _show_error_message(self, message):
        self._message_label.set_text(message)
        self._options_combo.hide()
        self._continue_btn.set_label(_('Retry'))
        self._continue_btn.show()
        if self._continue_btn_handler_id != 0:
            self._continue_btn.disconnect(self._continue_btn_handler_id)
        self._continue_btn_handler_id = self._continue_btn.connect(
            'clicked', self.__retry_cb)

    def _select_backend(self, button):
        itererator = self._options_combo.get_active_iter()
        model = self._options_combo.get_model()
        self._backend = model.get(itererator, 1)[0]
        self._start_operation()

    def _start_operation(self):
        logging.error('Starting operation %s with backend %s',
                      self._operation, self._backend.get_name())

        if self._operation == OPERATION_BACKUP:
            self._operator = self._backend.get_backup()
            self._message_label.set_text(_('Starting backup...'))

        if self._operation == OPERATION_RESTORE:
            self._operator = self._backend.get_restore()
            self._message_label.set_text(_('Starting restore...'))

        GObject.idle_add(self._continue_operation)

    def _continue_operation(self, options={}):
        need_more_information = True
        try:
            self._operator.verify_preconditions(options)
            need_more_information = False
        except PreConditionsError as e:
            self._show_error_message(str(e))
        except PreConditionsChoose as e:
            self._backend_parameter = e.options['parameter']
            self._ask_options(str(e), e.options['options'],
                              self._assign_parameter_backend)
        if not need_more_information:
            if self._operation == OPERATION_BACKUP:
                GObject.idle_add(self._internal_start_operation)

            if self._operation == OPERATION_RESTORE:
                # The restore is potentially dangerous
                # because will destroy all the information in the journal
                # ask for a confirmation before doing the restore
                self._request_restore_confirmation()

    def _request_restore_confirmation(self):
        self._message_label.set_text(
            _('I want to restore the content of my Journal. '
              'In order to do this, my Journal will first be emptied of all '
              'its content; then the restored content will be added.'))
        self._confirm_restore_chkbtn.set_label(_('Accept'))
        self._confirm_restore_chkbtn.show()
        self._options_combo.hide()
        self._continue_btn.set_label(_('Confirm'))
        self._continue_btn.show()
        if self._continue_btn_handler_id != 0:
            self._continue_btn.disconnect(self._continue_btn_handler_id)
        self._continue_btn_handler_id = self._continue_btn.connect(
            'clicked', self.__confirm_restore_cb)

    def __confirm_restore_cb(self, button):
        if self._confirm_restore_chkbtn.get_active():
            self._view.props.is_cancellable = False
            self._confirm_restore_chkbtn.hide()
            self._continue_btn.hide()
            self._message_label.set_text('')
            self._internal_start_operation()
            self._view.needs_restart = True

    def _internal_start_operation(self):
        self._operator.connect('started', self.__operation_started_cb)
        self._operator.connect('progress', self.__operation_progress_cb)
        self._operator.connect('finished', self.__operation_finished_cb)
        self._operator.connect('cancelled', self.__operation_cancelled_cb)

        # disable the accept button until the operation finish
        self._view.props.is_valid = False

        GObject.idle_add(self._operator.start)

    def __retry_cb(self, button):
        self._start_operation()

    def _assign_parameter_backend(self, button):
        itererator = self._options_combo.get_active_iter()
        model = self._options_combo.get_model()
        value = model.get(itererator, 1)[0]
        options = {self._backend_parameter: value}
        self._continue_operation(options)

    def __operation_started_cb(self, backend):
        self._message_label.set_text(_('Operation started'))
        self._options_combo.hide()
        self._continue_btn.hide()
        self._progress_bar.set_fraction(0.0)
        self._progress_bar.show()

    def __operation_progress_cb(self, backend, fraction):
        self._progress_bar.set_fraction(fraction)

    def __operation_finished_cb(self, backend):
        self._progress_bar.set_fraction(1.0)
        if self._operation == OPERATION_BACKUP:
            self._message_label.set_text(_('Backup finished successfully'))
        if self._operation == OPERATION_RESTORE:
            self._message_label.set_text(_('Restore realized successfully.'))
        self._view.props.is_valid = True

    def __operation_cancelled_cb(self, backend):
        self._view.props.is_valid = True
