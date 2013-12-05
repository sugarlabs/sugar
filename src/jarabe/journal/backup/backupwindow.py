# Copyright (C) 2013, SugarLabs
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics import style

from jarabe.model import shell
from backupmanager import BackupManager
from backupmanager import OPERATION_BACKUP, OPERATION_RESTORE
from jarabe.journal.backup.backends.backend_tools import PreConditionsError
from jarabe.journal.backup.backends.backend_tools import PreConditionsChoose


class BackupWindow(Gtk.Dialog):
    __gtype_name__ = 'SugarBackupWindow'

    def __init__(self):
        Gtk.Dialog.__init__(self)

        self.set_border_width(style.LINE_WIDTH)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        self._vbox = Gtk.VBox()
        # add the toolbar
        self._main_toolbar = MainToolbar()
        self._main_toolbar.show()
        self._main_toolbar.connect('stop-clicked',
                                   self.__stop_clicked_cb)

        self._vbox.pack_start(self._main_toolbar, False, False, 0)

        # add a container to set the canvas
        self._main_view = Gtk.EventBox()
        self._vbox.pack_start(self._main_view, True, True, 0)
        self._main_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())

        self.get_content_area().add(self._vbox)

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)
        self.connect('realize', self.__realize_cb)
        self.connect('delete-event', self.__delete_event_cb)

        # add the initial panel
        self.set_canvas(SelectBackupRestorePanel(self))
        self.grab_focus()
        self.manager = BackupManager()

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_accept_focus(True)
        # the modal windows counter is updated to disable hot keys - SL#4601
        shell.get_model().push_modal()

    def grab_focus(self):
        # overwrite grab focus in order to grab focus on the view
        if self._main_view.get_child() is not None:
            self._main_view.get_child().grab_focus()

    def __stop_clicked_cb(self, widget):
        # TODO: request confirmation and cancel operation if needed
        shell.get_model().pop_modal()
        self.destroy()

    def set_canvas(self, canvas):
        if self._main_view.get_child() is not None:
            self._main_view.remove(self._main_view.get_child())
        if canvas:
            logging.error('adding canvas %s', canvas)
            self._main_view.add(canvas)

    def __delete_event_cb(self, dialog, event):
        # avoid closing with Escape key
        return True


class MainToolbar(Gtk.Toolbar):
    """ Main toolbar of the backup/restore window
    """
    #__gtype_name__ = 'MainToolbar'

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         ([])),
    }

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        self.stop = ToolButton(icon_name='dialog-cancel')
        self.stop.set_tooltip(_('Done'))
        self.stop.connect('clicked', self.__stop_clicked_cb)
        self.stop.show()
        self.insert(self.stop, -1)
        self.stop.show()

    def __stop_clicked_cb(self, button):
        self.emit('stop-clicked')


class BigButton(Gtk.Button):

    def __init__(self, _icon_name):
        Gtk.Button.__init__(self)
        _icon = Icon(icon_name=_icon_name,
                     pixel_size=style.XLARGE_ICON_SIZE)
        self.add(_icon)
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_BLACK.get_gdk_color())


class SelectBackupRestorePanel(Gtk.HBox):

    def __init__(self, window):
        Gtk.HBox.__init__(self)
        self.set_spacing(style.DEFAULT_SPACING)

        self._window = window
        vbox = Gtk.VBox()
        vbox.set_spacing(style.DEFAULT_SPACING)
        self.backup_btn = BigButton('backup')
        self.backup_btn.connect('clicked', self.__backup_clicked_cb)
        label = Gtk.Label(
            _('Make a safe copy of the content of your Journal'))
        vbox.add(self.backup_btn)
        vbox.add(label)
        self.add(vbox)

        vbox = Gtk.VBox()
        vbox.set_spacing(style.DEFAULT_SPACING)
        self.restore_btn = BigButton('restore')
        self.restore_btn.connect('clicked', self.__restore_clicked_cb)
        label = Gtk.Label(_('Restore a security copy into your Journal'))
        vbox.add(self.restore_btn)
        self.add(vbox)

        self.show_all()

        vbox.add(label)

    def __backup_clicked_cb(self, button):
        operation_panel = OperationPanel(OPERATION_BACKUP, self._window)
        self._window.set_canvas(operation_panel)

    def __restore_clicked_cb(self, button):
        operation_panel = OperationPanel(OPERATION_RESTORE, self._window)
        self._window.set_canvas(operation_panel)


class OperationPanel(Gtk.VBox):

    def __init__(self, operation, window):
        Gtk.VBox.__init__(self)

        self._window = window
        self._operation = operation
        self._backend = None

        _icon = Icon(icon_name=operation,
                     pixel_size=style.XLARGE_ICON_SIZE)
        self.pack_start(_icon, True, True, style.DEFAULT_SPACING)
        _icon.show()

        self._message_label = Gtk.Label()
        self.pack_start(self._message_label, True, True, style.DEFAULT_SPACING)
        self._message_label.show()

        self._options_combo = Gtk.ComboBox()
        cell = Gtk.CellRendererText()
        self._options_combo.pack_start(cell, True)
        self._options_combo.add_attribute(cell, 'text', 0)
        self.pack_start(self._options_combo, False, False,
                        style.DEFAULT_SPACING)

        self._progress_bar = Gtk.ProgressBar()
        self.pack_start(self._progress_bar, False, False,
                        style.DEFAULT_SPACING)

        self._confirm_restore_chkbtn = Gtk.CheckButton()
        self.pack_start(self._confirm_restore_chkbtn, False, False,
                        style.DEFAULT_SPACING)

        self._continue_btn = Gtk.Button(_('Continue'))
        self._window.get_action_area().add(self._continue_btn)
        self._continue_btn_handler_id = 0

        self.show()

        # check if there are activities running
        # and request close them if any.
        if self._window.manager.need_stop_activities():
            self._message_label.set_text(
                _('Please close all the activities, and start again'))

        # check the backend availables, if there are more than one
        # show to the user to select one
        if len(self._window.manager.get_backends()) > 1:
            if operation == OPERATION_BACKUP:
                message = _('Select where you want create your backup')
            if operation == OPERATION_RESTORE:
                message = _('Select where you want retrive your restore')
            combo_options = []
            for backend in self._window.manager.get_backends():
                option = {}
                option['description'] = backend.get_name()
                option['value'] = backend
                combo_options.append(option)

            self._ask_options(message, combo_options, self._select_backend)
        else:
            self._start_operation(self._window.manager.get_backends()[0])

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

        if self._operation == OPERATION_RESTORE:
            self._operator = self._backend.get_restore()

        self._continue_operation()

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
                self._internal_start_operation()

            if self._operation == OPERATION_RESTORE:
                # The restore is potentially dangerous
                # because will destroy all the information in the journal
                # ask for a confirmation before doing the restore
                self._request_restore_confirmation()

    def _request_restore_confirmation(self):
        self._message_label.set_text(_('Please confirm'))
        self._confirm_restore_chkbtn.set_label(
            _('I want remove all the content in my Journal,'
              ' and restore the informatiomn from the selected checkpoint'))
        self._confirm_restore_chkbtn.show()
        self._options_combo.hide()
        self._continue_btn.set_label(_('Confirm'))
        if self._continue_btn_handler_id != 0:
            self._continue_btn.disconnect(self._continue_btn_handler_id)
        self._continue_btn_handler_id = self._continue_btn.connect(
            'clicked', self.__confirm_restore_cb)

    def __confirm_restore_cb(self, button):
        if self._confirm_restore_chkbtn.get_active():
            self._confirm_restore_chkbtn.hide()
            self._internal_start_operation()

    def _internal_start_operation(self):
        self._operator.connect('started', self.__operation_started_cb)
        self._operator.connect('progress', self.__operation_progress_cb)
        self._operator.connect('finished', self.__operation_finished_cb)
        self._operator.connect('cancelled', self.__operation_cancelled_cb)
        self._operator.start()

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
        if self._operation == OPERATION_RESTORE:
            self._message_label.set_text(_('Backup finished successfully'))
        if self._operation == OPERATION_RESTORE:
            self._message_label.set_text(
                _('Restore realized successfully.'
                  'You need restart Sugar to to finish.'))

    def __operation_cancelled_cb(self, backend):
        pass
