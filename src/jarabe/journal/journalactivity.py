# Copyright (C) 2006, Red Hat, Inc.
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

import logging
from gettext import gettext as _
import uuid
import time
import dbus
import os
from dbus import service

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GLib

from sugar4.graphics.alert import ErrorAlert
from sugar4 import env
from sugar4.datastore import datastore
from sugar4.activity import activityfactory

from jarabe.journal.journaltoolbox import MainToolbox
from jarabe.journal.journaltoolbox import AddNewBar
from jarabe.journal.journaltoolbox import DetailToolbox
from jarabe.journal.journaltoolbox import EditToolbox
from jarabe.journal.projectview import ProjectView

from jarabe.journal.listview import ListView
from jarabe.journal.listmodel import ListModel
from jarabe.journal.detailview import DetailView
from jarabe.journal.volumestoolbar import VolumesToolbar
from jarabe.journal import misc
from jarabe.journal.objectchooser import ObjectChooser
from jarabe.desktop.activitychooser import ActivityChooser
from jarabe.journal.modalalert import ModalAlert
from jarabe.journal import model
from jarabe.journal.journalwindow import JournalWindow
from jarabe.journal.bundlelauncher import launch_bundle, get_bundle
from jarabe.journal import journalwindow
from jarabe.journal.listmodel import ListModel

from jarabe.model import session, shell

from sugar4.graphics import style

J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'

_SPACE_THRESHOLD = 50  # MiB
_BUNDLE_ID = 'org.laptop.JournalActivity'
SCOPE_PRIVATE = 'private'
_journal = None
PROJECT_BUNDLE_ID = 'org.sugarlabs.Project'


class JournalActivityDBusService(service.Object):

    def __init__(self, parent):
        self._parent = parent
        session_bus = dbus.SessionBus()
        bus_name = service.BusName(J_DBUS_SERVICE,
                                        bus=session_bus,
                                        replace_existing=False,
                                        allow_replacement=False)
        logging.debug('bus_name: %r', bus_name)
        service.Object.__init__(self, bus_name, J_DBUS_PATH)

    @service.method(J_DBUS_INTERFACE, in_signature='ss',
                         out_signature='s')
    def GetBundlePath(self, bundle_id, object_id):
        '''
        Get bundle path given object_id and/or bundle_id.
        This is used in the toolkit to provide the bundle information
        to other activities using activity.get_bundle()
        '''
        # Convert dbus empty strings to None, is the only way to pass
        # optional parameters with dbus.
        if bundle_id == "":
            bundle_id = None
        if object_id == "":
            object_id = None

        bundle = get_bundle(bundle_id, object_id)
        if bundle is None:
            return ''
        return bundle.get_path()

    @service.method(J_DBUS_INTERFACE, in_signature='ss',
                         out_signature='b')
    def LaunchBundle(self, bundle_id, object_id):
        '''
        Launch an activity with a given object_id and/or bundle_id.

        See `jarabe.journal.bundlelauncher.launch_bundle` for
        further documentation
        '''
        # Convert dbus empty strings to None, is the only way to pass
        # optional parameters with dbus.
        if bundle_id == "":
            bundle_id = None
        if object_id == "":
            object_id = None

        return launch_bundle(bundle_id, object_id)

    @service.method(J_DBUS_INTERFACE,
                         in_signature='s', out_signature='')
    def ShowObject(self, object_id):
        """Pop-up journal and show object with object_id"""

        logging.debug('Trying to show object %s', object_id)

        if self._parent.show_object(object_id):
            self._parent.reveal()

    def _chooser_response_cb(self, chooser, response_id, chooser_id):
        logging.debug('JournalActivityDBusService._chooser_response_cb')
        if response_id == Gtk.ResponseType.ACCEPT:
            object_id = chooser.get_selected_object_id()
            self.ObjectChooserResponse(chooser_id, object_id)
        else:
            self.ObjectChooserCancelled(chooser_id)
        chooser.close()
        del chooser

    @service.method(J_DBUS_INTERFACE, in_signature='is',
                         out_signature='s')
    def ChooseObject(self, parent_id, what_filter=''):
        """
        This method is kept for backwards compatibility
        """
        chooser_id = uuid.uuid4().hex
        parent = None
        chooser = ObjectChooser(parent, what_filter)
        chooser.connect('response', self._chooser_response_cb, chooser_id)
        chooser.present()

        return chooser_id

    @service.method(J_DBUS_INTERFACE, in_signature='issb',
                         out_signature='s')
    def ChooseObjectWithFilter(self, parent_id, what_filter='',
                               filter_type=None, show_preview=False):
        chooser_id = uuid.uuid4().hex
        parent = None
        chooser = ObjectChooser(parent, what_filter, filter_type, show_preview)
        chooser.connect('response', self._chooser_response_cb, chooser_id)
        chooser.present()

        return chooser_id

    @service.signal(J_DBUS_INTERFACE, signature='ss')
    def ObjectChooserResponse(self, chooser_id, object_id):
        pass

    @service.signal(J_DBUS_INTERFACE, signature='s')
    def ObjectChooserCancelled(self, chooser_id):
        pass


class JournalViews(object):
    MAIN = 1
    DETAIL = 2
    PROJECT = 3


class JournalActivity(JournalWindow):

    def __init__(self):
        logging.debug('STARTUP: Loading the journal')
        JournalWindow.__init__(self)
        self.add_css_class('journal-window')
        self.add_css_class('background')

        activity_id = activityfactory.create_activity_id()
        self.activity_id = str(activity_id)
        self.bundle_id = _BUNDLE_ID

        self._main_view = None
        self._project_view = None
        self._secondary_view = None
        self._list_view = None
        self._detail_view = None
        self._main_toolbox = None
        self._edit_toolbox = None
        self._detail_toolbox = None
        self._volumes_toolbar = None
        self._key_controller = None
        self._toolbox = None
        self._mount_point = '/'
        self._active_view = JournalViews.MAIN
        self.project_metadata = None
        self._editing_mode = False
        self._init_done = False
        self._critical_space_alert = None

        self._dbus_service = JournalActivityDBusService(self)

        model.created.connect(self.__model_created_cb)
        model.updated.connect(self.__model_updated_cb)
        model.deleted.connect(self.__model_deleted_cb)

        session.get_session_manager().shutdown_signal.connect(
            self._session_manager_shutdown_cb)

    def _setup(self):
        """Create all child widgets.

        Must be called after self has been added to the shell Gtk.Stack so
        that a native GdkSurface ancestor exists; GTK4 popovers crash
        without one ('gdk_surface_new_popup: assertion GDK_IS_SURFACE (parent) failed').
        """
        self._setup_main_view()
        self._setup_secondary_view()
        self._setup_project_view()

        self._realized_sid = self.connect('realize', self.__realize_cb)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self.__key_press_event_cb)
        self.add_controller(key_controller)
        self._key_controller = key_controller

        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect('enter', self._focus_in_event_cb)
        focus_controller.connect('leave', self._focus_out_event_cb)
        self.add_controller(focus_controller)

        self._init_done = True
        self.show_main_view()
        self.minimize()
        self._check_available_space()

    def volume_error_cb(self, gobject, message, severity):
        alert = ErrorAlert(title=severity, msg=message)
        alert.connect('response', self.__alert_response_cb)
        self.add_alert(alert)
        alert.set_visible(True)

    def __alert_response_cb(self, alert, response_id):
        self.remove_alert(alert)

    def __realize_cb(self, window):
        self.disconnect(self._realized_sid)
        self._realized_sid = None

    def _session_manager_shutdown_cb(self, event):
        self.close()

    def can_close(self):
        return False

    def list_view_signal_connect(self, list_view):
        list_view.connect('detail-clicked', self.__detail_clicked_cb)
        list_view.connect('clear-clicked', self.__clear_clicked_cb)
        list_view.connect('volume-error', self.volume_error_cb)
        list_view.connect('title-edit-started',
                          self.__title_edit_started_cb)
        list_view.connect('title-edit-finished',
                          self.__title_edit_finished_cb)
        list_view.connect('title-edit-canceled',
                          self.__title_edit_canceled_cb)
        list_view.connect('selection-changed',
                          self.__selection_changed_cb)
        list_view.connect('project-view-activate',
                          self.project_view_activated_cb)

    def _create_volumes_toolbar(self):
        self._volumes_toolbar = VolumesToolbar()
        self._volumes_toolbar.connect('volume-changed',
                                      self.__volume_changed_cb)
        self._volumes_toolbar.connect('volume-error', self.volume_error_cb)
        return self._volumes_toolbar

    def _setup_main_view(self):
        self._main_toolbox = MainToolbox()
        self._edit_toolbox = EditToolbox(self)
        self._main_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._add_new_box = AddNewBar(_('Add new project'))
        self._add_new_box.activate.connect(self.__add_project_activate_cb)
        self._add_new_box.set_margin_top(style.DEFAULT_SPACING)
        self._add_new_box.set_margin_bottom(style.DEFAULT_SPACING)
        self._main_view.append(self._add_new_box)
        self._main_view.set_focusable(True)

        self._list_view = ListView(self, enable_multi_operations=True)
        self.list_view_signal_connect(self._list_view)
        tree_view = self._list_view.tree_view
        tree_view.connect('choose-project', self.__choose_project_cb)
        self._list_view.set_vexpand(True)
        self._main_view.append(self._list_view)
        self._list_view.set_visible(True)

        volumes_toolbar = self._create_volumes_toolbar()
        self._main_view.append(volumes_toolbar)

        self._main_toolbox.connect('query-changed', self._query_changed_cb)


        self._main_toolbox.set_mount_point(self._mount_point)

    def _setup_project_view(self):
        self._project_view = ProjectView()
        project_vbox = self._project_view.get_vbox()

        add_new_box = AddNewBar()
        add_new_box.activate.connect(self.__add_new_activate_cb)
        add_new_box.set_visible(True)
        add_new_box.set_margin_top(style.DEFAULT_SPACING // 3)
        add_new_box.set_margin_bottom(style.DEFAULT_SPACING // 3)
        project_vbox.append(add_new_box)

        self._entry_project = add_new_box.get_entry()
        self._list_view_project = self._project_view.create_list_view_project()
        self.list_view_signal_connect(self._list_view_project)
        self._list_view_project.set_vexpand(True)
        project_vbox.append(self._list_view_project)
        self._list_view_project.set_visible(True)

    def get_add_new_box(self):
        return self._add_new_box

    def get_list_view(self):
        return self._list_view

    def project_view_activated_cb(self, list_view, metadata):
        if not self._init_done:
            return
        self.project_metadata = metadata
        self._project_view.set_project_metadata(self.project_metadata)

        self._project_view.connect('go-back-clicked',
                                   self.__go_back_clicked_cb)
        self._active_view = JournalViews.PROJECT
        self.set_canvas(self._project_view)
        self._toolbox = self._main_toolbox
        self.set_toolbar_box(self._toolbox)
        self._toolbox.set_visible(True)

        query = {}
        query['project_id'] = self.project_metadata['uid']
        self._list_view_project.update_with_query(query)
        self._project_view.set_visible(True)

    def _setup_secondary_view(self):
        self._secondary_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._detail_toolbox = DetailToolbox(self)
        self._detail_toolbox.connect('volume-error', self.volume_error_cb)

        self._detail_view = DetailView(self)
        self._detail_view.connect('go-back-clicked', self.__go_back_clicked_cb)
        self._detail_view.set_vexpand(True)
        self._secondary_view.append(self._detail_view)
        self._detail_view.set_visible(True)

    def __add_project_activate_cb(self, bar, title):
        initialize_journal_object(
            title=title, bundle_id=PROJECT_BUNDLE_ID,
            activity_id=None, project_metadata=None)

    def __add_new_activate_cb(self, bar, title):
        shell_model = shell.get_model()
        activity = shell_model.get_active_activity()
        if activity and activity.has_shell_window():
            return

        if shell.get_model().has_modal():
            return

        chooser = ActivityChooser()
        if activity:
            activity.push_shell_window(chooser)
            chooser.connect('unmap', activity.pop_shell_window)

        text = _("Choose an activity to start '%s' with") % title
        chooser.set_title(text)
        chooser.connect('activity-selected',
                        self.__activity_selected_cb,
                        title)
        chooser.set_visible(True)

    def __activity_selected_cb(self, widget, bundle_id, activity_id, title):
        initialize_journal_object(
            title=title, bundle_id=bundle_id,
            activity_id=activity_id, project_metadata=self.project_metadata)

    def __key_press_event_cb(self, controller, keyval, keycode, state):
        '''
        Entries can be scrolled with 'Up'/'Down' arrow keys.
        Search can be started by pressing 'Ctrl' + 'F' keys
        Search can be stopped by pressing `Escape` key
        Return from Detail view to Main view by pressing 'Left' arrow key
        Pressing 'Return' in Detail View starts the activity
        '''

        keyname = Gdk.keyval_name(keyval)

        if self._active_view == JournalViews.MAIN:
            if keyname == 'Up' or keyname == 'Down':
                if not self._list_view.tree_view.has_focus():
                    self._list_view.tree_view.grab_focus()
                    return True

            elif keyname == 'Escape':
                self._main_toolbox.clear_query()
                if not self._list_view.tree_view.has_focus():
                    self._list_view.tree_view.grab_focus()
                return True

            elif state & Gdk.ModifierType.CONTROL_MASK and keyname == 'f':
                self._main_toolbox.search_entry.grab_focus()
                return True

        elif self._active_view == JournalViews.DETAIL:
            if keyname == 'Left':
                path, col = self._list_view.tree_view.get_cursor()
                self._list_view.tree_view.grab_focus()
                column = self._list_view.tree_view.get_column(5)
                if path and column:
                    self._list_view.tree_view.set_cursor_on_cell(path, column, None, True)
                self._detail_view.emit('go-back-clicked')
                return True

            if keyname == 'Return':
                metadata = self._detail_toolbox.get_metadata()
                misc.resume(metadata,
                    alert_window=journalwindow.get_journal_window())
                return True

        return False

    def __choose_project_cb(self, tree_view, metadata_to_send):
        project_chooser = ObjectChooser(None)
        project_chooser.present()
        project_chooser.connect('response', self.__project_chooser_response_cb,
                                metadata_to_send)
        project_chooser._toolbar._proj_list_button_clicked_cb(None)

    def __project_chooser_response_cb(self, project_chooser, response_value,
                                      metadata_to_send):
        if response_value == Gtk.ResponseType.DELETE_EVENT:
            project_chooser.close()
            return

        object_id = project_chooser.get_selected_object_id()
        metadata = model.get(object_id)
        jobject_to_send = datastore.get(metadata_to_send['uid'])
        datastore.delete(metadata_to_send['uid'])
        jobject_to_send.metadata['project_id'] = metadata['uid']
        datastore.write(jobject_to_send)
        project_chooser.close()

    def __detail_clicked_cb(self, list_view, object_id):
        metadata = model.get(object_id)
        activity = metadata.get('activity', None)
        if activity == PROJECT_BUNDLE_ID:
            self.project_view_activated_cb(list_view, metadata)
        else:
            self._show_secondary_view(object_id)

    def __clear_clicked_cb(self, list_view):
        self._main_toolbox.clear_query()

    def __selection_changed_cb(self, list_view, selected_items):
        self._editing_mode = selected_items != 0
        self._edit_toolbox.set_selected_entries(selected_items)
        self._edit_toolbox.display_selected_entries_status()
        self.show_main_view()

    def update_selected_items_ui(self):
        selected_items = \
            len(self.get_list_view().get_model().get_selected_items())
        self.__selection_changed_cb(None, selected_items)

    def __go_back_clicked_cb(self, detail_view):
        self.show_main_view()

    def _query_changed_cb(self, toolbar, query):
        if not self._init_done:
            return
        self._list_view.update_with_query(query)
        self.show_main_view()
        self._main_toolbox.search_entry.grab_focus()
        # setting cursor position directly
        self._main_toolbox.search_entry.set_position(-1)
        self._add_new_box.props.visible = \
            query.get('activity') == PROJECT_BUNDLE_ID

    def __search_icon_pressed_cb(self, entry, icon_pos, event=None):
        self._main_view.grab_focus()

    def __title_edit_started_cb(self, list_view):
        GLib.idle_add(self.remove_controller, self._key_controller)

    def __title_edit_finished_cb(self, list_view, new_text, path):
        self.add_controller(self._key_controller)
        list_view_model = list_view.get_model()
        iterator = list_view_model.get_iter(path)
        list_view_model[iterator][ListModel.COLUMN_TITLE] = new_text

    def __title_edit_canceled_cb(self, list_view):
        self.add_controller(self._key_controller)

    def show_main_view(self):
        if not self._init_done:
            return
        self._active_view = JournalViews.MAIN
        self.project_metadata = None
        if self._editing_mode:
            self._toolbox = self._edit_toolbox
            self._toolbox.set_total_number_of_entries(
                self.get_total_number_of_entries())
        else:
            self._toolbox = self._main_toolbox

        self.set_toolbar_box(self._toolbox)
        self._toolbox.set_visible(True)

        if self.canvas != self._main_view:
            self.set_canvas(self._main_view)
            self._main_view.set_visible(True)

    def _show_secondary_view(self, object_id):
        if not self._init_done:
            return
        self._active_view = JournalViews.DETAIL
        metadata = model.get(object_id)
        try:
            self._detail_toolbox.set_metadata(metadata)
        except Exception:
            logging.exception('Exception while displaying entry:')

        self.set_toolbar_box(self._detail_toolbox)
        self._detail_toolbox.set_visible(True)

        try:
            self._detail_view.props.metadata = metadata
        except Exception:
            logging.exception('Exception while displaying entry:')

        self.set_canvas(self._secondary_view)
        self._secondary_view.set_visible(True)

    def show_object(self, object_id):
        metadata = model.get(object_id)
        if metadata is None:
            return False
        self._show_secondary_view(object_id)
        return True

    def __volume_changed_cb(self, volume_toolbar, mount_point):
        logging.debug('Selected volume: %r.', mount_point)
        self._mount_point = mount_point
        self.set_editing_mode(False)
        self._main_toolbox.set_mount_point(mount_point)
        self._edit_toolbox.batch_copy_button.update_mount_point()

    def __model_created_cb(self, sender, **kwargs):
        if not self._init_done:
            return
        misc.handle_bundle_installation(model.get(kwargs['object_id']))
        self._main_toolbox.refresh_filters()
        self._check_available_space()

    def __model_updated_cb(self, sender, **kwargs):
        if not self._init_done:
            return
        misc.handle_bundle_installation(model.get(kwargs['object_id']))

        if self.canvas == self._secondary_view and \
                kwargs['object_id'] == self._detail_view.props.metadata['uid']:
            self._detail_view.refresh()

        self._check_available_space()

    def __model_deleted_cb(self, sender, **kwargs):
        if not self._init_done:
            return
        if self.canvas == self._secondary_view and \
                kwargs['object_id'] == self._detail_view.props.metadata['uid']:
            self.show_main_view()

    def _focus_in_event_cb(self, controller):
        self._set_is_visible(True)

    def _focus_out_event_cb(self, controller):
        self._set_is_visible(False)

    def _set_is_visible(self, visible):
        if not self._init_done:
            return
        if self._active_view == JournalViews.MAIN:
            self._list_view.set_is_visible(visible)
        elif self._active_view == JournalViews.PROJECT:
            self._list_view_project.set_is_visible(visible)

    def _check_available_space(self):
        """Check available space on device

            If the available space is below threshold an alert will be
            shown which suggests deleting old journal entries.
        """

        if self._critical_space_alert:
            return
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[0] * stat[4]
        if free_space < (_SPACE_THRESHOLD * 1024 * 1024):
            self._critical_space_alert = ModalAlert()
            self._critical_space_alert.connect('close-request',
                                               self.__alert_closed_cb)
            self._critical_space_alert.set_visible(True)

    def __alert_closed_cb(self, data):
        self.show_main_view()
        self.reveal()
        self._critical_space_alert = None
        return False

    def set_active_volume(self, mount):
        self._volumes_toolbar.set_active_volume(mount)

    def show_journal(self):
        """Become visible, show main view, and focus the search entry."""
        self.reveal()
        self.show_main_view()
        # Focus the search entry so the user can type immediately.
        if self._init_done and self._main_toolbox is not None:
            GLib.idle_add(self._main_toolbox.search_entry.grab_focus)
        else:
            self.grab_focus()

    def get_total_number_of_entries(self):
        list_view_model = self.get_list_view().get_model()
        return len(list_view_model)

    def get_editing_mode(self):
        return self._editing_mode

    def set_editing_mode(self, editing_mode):
        if editing_mode == self._editing_mode:
            return
        self._editing_mode = editing_mode
        if self._editing_mode:
            self.get_list_view().disable_drag_and_copy()
        else:
            self.get_list_view().enable_drag_and_copy()
        self.show_main_view()

    def get_mount_point(self):
        return self._mount_point

    def _set_widgets_sensitive_state(self, sensitive_state):
        self._toolbox.set_sensitive(sensitive_state)
        self._list_view.set_sensitive(sensitive_state)
        if sensitive_state:
            self._list_view.enable_updates()
        else:
            self._list_view.disable_updates()
        self._volumes_toolbar.set_sensitive(sensitive_state)

    def freeze_ui(self):
        self._set_widgets_sensitive_state(False)

    def unfreeze_ui(self):
        self._set_widgets_sensitive_state(True)


def get_journal():
    global _journal
    if _journal is None:
        _journal = JournalActivity()

        shell.get_model().stack.add_named(_journal, "journal")

        _journal._setup()

        # register with the shell model so the frame (F6) can track it
        from jarabe.model.shell import Activity
        from jarabe.model.bundleregistry import get_registry
        from jarabe.model.buddy import get_owner_instance

        registry = get_registry()
        journal_info = registry.get_bundle('org.laptop.JournalActivity')
        
        home_activity = Activity(
            activity_info=journal_info,
            activity_id=_journal.activity_id,
            color=get_owner_instance().props.color,
            window=_journal
        )
        
        # The Journal is instantiated internally, so we must manually mark it as launched.
        # Otherwise, the JournalPalette will be stuck on "Starting..." forever.
        home_activity._set_launch_status(Activity.LAUNCHED)
        
        shell.get_model()._add_activity(home_activity)

    return _journal


def initialize_journal_object(title=None, bundle_id=None,
                              activity_id=None, project_metadata=None,
                              icon_color=None, invited=False):

    if not icon_color:
        settings = Gio.Settings.new('org.sugarlabs.user')
        icon_color = settings.get_string('color')

    if not activity_id:
        activity_id = activityfactory.create_activity_id()

    jobject = datastore.create()
    jobject.metadata['title'] = title
    jobject.metadata['title_set_by_user'] = '0'
    jobject.metadata['activity_id'] = activity_id
    jobject.metadata['keep'] = '0'
    jobject.metadata['preview'] = ''
    jobject.metadata['icon-color'] = icon_color
    jobject.file_path = ''

    if bundle_id == PROJECT_BUNDLE_ID:
        jobject.metadata['activity'] = PROJECT_BUNDLE_ID

    elif project_metadata is not None:
        jobject.metadata['mountpoints'] = ['/']
        jobject.metadata['activity'] = bundle_id
        jobject.metadata['share-scope'] = SCOPE_PRIVATE
        jobject.metadata['launch-times'] = str(int(time.time()))
        jobject.metadata['spent-times'] = '0'
        jobject.metadata['project_id'] = project_metadata['uid']
    # FIXME: We should be able to get an ID synchronously from the DS,
    # then call async the actual create.
    # http://bugs.sugarlabs.org/ticket/2169
    datastore.write(jobject)
    return jobject


def start():
    get_journal()
