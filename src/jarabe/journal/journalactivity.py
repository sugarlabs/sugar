# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
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
import uuid
import json

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import Gio
import dbus
import statvfs
import os

from sugar3.graphics import style
from sugar3.graphics.alert import ErrorAlert
from sugar3.graphics import iconentry
from sugar3.graphics.toolbutton import ToolButton

from sugar3 import env
from sugar3.datastore import datastore
from sugar3.activity import activityfactory
from gi.repository import SugarExt

from jarabe.journal.journaltoolbox import MainToolbox
from jarabe.journal.journaltoolbox import DetailToolbox
from jarabe.journal.journaltoolbox import EditToolbox
from jarabe.journal.expandedentry import TextView, BuddyList 

from jarabe.journal.listview import ListView
from jarabe.journal.detailview import DetailView
from jarabe.journal.volumestoolbar import VolumesToolbar
from jarabe.journal import misc
from jarabe.journal.objectchooser import ObjectChooser
from jarabe.journal.modalalert import ModalAlert
from jarabe.journal import model
from jarabe.journal.journalwindow import JournalWindow
from jarabe.journal.bundlelauncher import launch_bundle, get_bundle

from jarabe.view.friendlistpopup import FriendListPopup

from jarabe.model import session


J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'

_SPACE_TRESHOLD = 52428800
_BUNDLE_ID = 'org.laptop.JournalActivity'

_journal = None


class JournalActivityDBusService(dbus.service.Object):
    def __init__(self, parent):
        self._parent = parent
        session_bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(J_DBUS_SERVICE,
                                        bus=session_bus,
                                        replace_existing=False,
                                        allow_replacement=False)
        logging.debug('bus_name: %r', bus_name)
        dbus.service.Object.__init__(self, bus_name, J_DBUS_PATH)

    @dbus.service.method(J_DBUS_INTERFACE, in_signature='ss',
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
        else:
            return bundle.get_path()

    @dbus.service.method(J_DBUS_INTERFACE, in_signature='ss',
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

    @dbus.service.method(J_DBUS_INTERFACE,
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
        chooser.destroy()
        del chooser

    @dbus.service.method(J_DBUS_INTERFACE, in_signature='is',
                         out_signature='s')
    def ChooseObject(self, parent_xid, what_filter=''):
        """
        This method is keep for backwards compatibility
        """
        chooser_id = uuid.uuid4().hex
        if parent_xid > 0:
            display = Gdk.Display.get_default()
            parent = GdkX11.X11Window.foreign_new_for_display(
                display, parent_xid)
        else:
            parent = None
        chooser = ObjectChooser(parent, what_filter)
        chooser.connect('response', self._chooser_response_cb, chooser_id)
        chooser.show()

        return chooser_id

    @dbus.service.method(J_DBUS_INTERFACE, in_signature='issb',
                         out_signature='s')
    def ChooseObjectWithFilter(self, parent_xid, what_filter='',
                               filter_type=None, show_preview=False):
        chooser_id = uuid.uuid4().hex
        if parent_xid > 0:
            display = Gdk.Display.get_default()
            parent = GdkX11.X11Window.foreign_new_for_display(
                display, parent_xid)
        else:
            parent = None
        chooser = ObjectChooser(parent, what_filter, filter_type, show_preview)
        chooser.connect('response', self._chooser_response_cb, chooser_id)
        chooser.show()

        return chooser_id

    @dbus.service.signal(J_DBUS_INTERFACE, signature='ss')
    def ObjectChooserResponse(self, chooser_id, object_id):
        pass

    @dbus.service.signal(J_DBUS_INTERFACE, signature='s')
    def ObjectChooserCancelled(self, chooser_id):
        pass


class JournalActivity(JournalWindow):
    def __init__(self):
        logging.debug('STARTUP: Loading the journal')
        JournalWindow.__init__(self)

        self.set_title(_('Journal'))

        self._main_view = None
        self._project_view = None
        self._secondary_view = None
        self._list_view = None
        self._detail_view = None
        self._main_toolbox = None
        self._detail_toolbox = None
        self._volumes_toolbar = None
        self._mount_point = '/'
        self._main_view_active = True
        self.project_metadata = None
        self._editing_mode = False

        self._setup_main_view()
        self._setup_secondary_view()
        self._setup_project_view()

        self.add_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self._realized_sid = self.connect('realize', self.__realize_cb)
        self.connect('window-state-event', self.__window_state_event_cb)
        self.connect('key-press-event', self._key_press_event_cb)
        self.connect('focus-in-event', self._focus_in_event_cb)
        self.connect('focus-out-event', self._focus_out_event_cb)

        model.created.connect(self.__model_created_cb)
        model.updated.connect(self.__model_updated_cb)
        model.deleted.connect(self.__model_deleted_cb)

        self._dbus_service = JournalActivityDBusService(self)

        self.iconify()

        self._critical_space_alert = None
        self._check_available_space()

        session.get_session_manager().shutdown_signal.connect(
            self._session_manager_shutdown_cb)

    def volume_error_cb(self, gobject, message, severity):
        alert = ErrorAlert(title=severity, msg=message)
        alert.connect('response', self.__alert_response_cb)
        self.add_alert(alert)
        alert.show()

    def __alert_response_cb(self, alert, response_id):
        self.remove_alert(alert)

    def __realize_cb(self, window):
        xid = window.get_window().get_xid()
        SugarExt.wm_set_bundle_id(xid, _BUNDLE_ID)
        activity_id = activityfactory.create_activity_id()
        SugarExt.wm_set_activity_id(xid, str(activity_id))
        self.disconnect(self._realized_sid)
        self._realized_sid = None

    def _session_manager_shutdown_cb(self, event):
        self.destroy()

    def can_close(self):
        return False

    def _setup_main_view(self):
        self._main_toolbox = MainToolbox()
        self._edit_toolbox = EditToolbox(self)
        self._main_view = Gtk.VBox()

        hbox = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
        add_new_button = ToolButton('list-add') # suggest icon for this
        add_new_button.set_tooltip(_('Add New'))
        add_new_button.connect('clicked', self._add_new_button_clicked_cb)
        hbox.pack_start(add_new_button, False, True, 0)
        add_new_button.show()

        self._entry = iconentry.IconEntry()
        self._entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'activity-journal')
        text = _('Add new entry')
        self._entry.set_placeholder_text(text)
        self._entry.add_clear_button()
        hbox.pack_start(self._entry, True, True, 0)
        self._entry.show()
        hbox.show()
        self._main_view.pack_start(hbox, False, True, 0)
        self._main_view.set_can_focus(True)

        self._list_view = ListView(self, enable_multi_operations=True)
        self._list_view.connect('detail-clicked', self.__detail_clicked_cb)
        self._list_view.connect('clear-clicked', self.__clear_clicked_cb)
        self._list_view.connect('volume-error', self.volume_error_cb)
        self._list_view.connect('title-edit-started',
                                self.__title_edit_started_cb)
        self._list_view.connect('title-edit-finished',
                                self.__title_edit_finished_cb)
        self._list_view.connect('selection-changed',
                                self.__selection_changed_cb)
        self._list_view.connect('project-view-activate',
                                self.__project_view_activated_cb)
        self._main_view.pack_start(self._list_view, True, True, 0)
        self._list_view.show()

        self._volumes_toolbar = VolumesToolbar()
        self._volumes_toolbar.connect('volume-changed',
                                      self.__volume_changed_cb)
        self._volumes_toolbar.connect('volume-error', self.volume_error_cb)
        self._main_view.pack_start(self._volumes_toolbar, False, True, 0)

        self._main_toolbox.connect('query-changed', self._query_changed_cb)

        self._main_toolbox.search_entry.connect('icon-press',
                                                self.__search_icon_pressed_cb)
        self._main_toolbox.set_mount_point(self._mount_point)

    def _setup_project_view(self):
        self._project_view = Gtk.VBox()
        description_box = TextView()
        #description_box.size_allocate((10 , 15))
        self._project_view.pack_start(description_box, True, True, 0)
        logging.debug('Project view setup')
        description_box.show()
        #self._description.show()
        hbox = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)

        add_buddy_button = ToolButton('list-add') # suggest icon for this
        add_buddy_button.set_tooltip(_('Add Buddy'))
        add_buddy_button.connect('clicked',self._add_buddy_button_clicked_cb)
        hbox.pack_start(add_buddy_button, False, True, 0)
        add_buddy_button.show()
        
        self._buddy_list = Gtk.VBox()
        hbox.pack_start(self._buddy_list, True, False, 0)
        self._project_view.pack_start(hbox, True, True, 0)
        
        hbox.show()

    def _add_buddy_button_clicked_cb(self, button):
        logging.debug('[GSoC]_add_buddy_button_clicked_cb')
        pop_up = FriendListPopup()
        pop_up.connect('friend-selected', self.__friend_selected_cb)

    def __friend_selected_cb(self, xyz, selected):
        logging.debug('[GSoC]__friend_selected_cb %r' %selected)
        buddies = []
        if not self.project_metadata.get('buddies'):
            self.project_metadata['buddies'] = []
        for buddy in selected:
            self.project_metadata['buddies'].append((buddy.nick, buddy.color))

        #datastore._update_ds_entry(self.project_metadata['uid'])
        #model.write(self.project_metadata['uid'])
        self._project_buddies(self.project_metadata)
        logging.debug('[GSoC]friend finally selected')

    def _project_buddies(self, metadata):
        logging.debug('[GSoC]_project_buddies')
        for child in self._buddy_list.get_children():
            self._buddy_list.remove(child)
            # FIXME: self._buddy_list.foreach(self._buddy_list.remove)
        self._buddy_list.pack_start(self._create_buddy_list(metadata), False, False,
                                    style.DEFAULT_SPACING)
        self._buddy_list.show_all()
        logging.debug('[GSoC]project_buddies ended')                

    def _create_buddy_list(self, metadata):

        vbox = Gtk.VBox()
        #vbox.props.spacing = style.DEFAULT_SPACING

        #text = Gtk.Label()
        #text.set_markup('<span foreground="%s">%s</span>' % (
        #    style.COLOR_BUTTON_GREY.get_html(), _('Participants:')))
        #halign = Gtk.Alignment.new(0, 0, 0, 0)
        #halign.add(text)
        #vbox.pack_start(halign, False, False, 0)

        if metadata.get('buddies'):
            #buddies = json.loads(metadata['buddies']).values()
            buddies = metadata['buddies']
            logging.debug('[GSoC]buddies are %r' %buddies)
            #for buddy in metadata['buddies']:
            #    buddies.append((buddy.nick, buddy.color))
            vbox.pack_start(BuddyList(buddies), False, False, 0)
            logging.debug('[GSoC]created_buddy_list ')
            vbox.show_all()
            return vbox
        else:
            vbox.show()
            return vbox

    '''
    def _create_description(self):
        widget = TextView()
        widget.connect('focus-out-event',
                       self._description_tags_focus_out_event_cb)
        return self._create_scrollable(widget, label=_('Description:')), widget

    def _description_tags_focus_out_event_cb(self, text_view, event):
        logging.debug('[GSoC]blah here')

    def _create_scrollable(self, widget, label=None):
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        if label is not None:
            logging.debug('[GSoC]create_scrollable')
            text = Gtk.Label()
            text.set_markup('<span foreground="%s">%s</span>' % (
                style.COLOR_BUTTON_GREY.get_html(), label))

            halign = Gtk.Alignment.new(0, 0, 0, 0)
            halign.add(text)
            vbox.pack_start(halign, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        scrolled_window.add(widget)
        vbox.pack_start(scrolled_window, True, True, 0)

        return vbox
    '''

    def get_list_view(self):
        return self._list_view

    def get_entry(self):
        return self._entry

    def __project_view_activated_cb(self, list_view, metadata):
        self.project_metadata = metadata
        self._main_view_active = False
        self._project_buddies(metadata)
        logging.debug('project_view_activate signal handler')
        self.set_canvas(self._project_view)
        self._project_view.show()

    def _setup_secondary_view(self):
        self._secondary_view = Gtk.VBox()

        self._detail_toolbox = DetailToolbox(self)
        self._detail_toolbox.connect('volume-error', self.volume_error_cb)

        self._detail_view = DetailView(self)
        self._detail_view.connect('go-back-clicked', self.__go_back_clicked_cb)
        self._secondary_view.pack_end(self._detail_view, True, True, 0)
        self._detail_view.show()

    def _add_new_button_clicked_cb(self, button):
        # This method only implements Add-New-Project
        # TODO: Add-New-Entry for other activities
        if self.get_list_view().get_projects_view_active():
            self._initialize_journal_object()

    def _initialize_journal_object(self):
        logging.debug('[GSoC]initializing journal object for project')
        title = _(self.get_entry().props.text)
        settings = Gio.Settings('org.sugarlabs.user')
        icon_color = settings.get_string('color')

        jobject = datastore.create()
        jobject.metadata['title'] = title
        jobject.metadata['title_set_by_user'] = '0'
        jobject.metadata['activity'] = 'Project'

        # TODO: Implement activity_id for projects
        #jobject.metadata['activity_id'] = self.get_id()

        jobject.metadata['keep'] = '0'
        jobject.metadata['preview'] = ''
        #jobject.metadata['share-scope'] = SCOPE_PRIVATE
        jobject.metadata['icon-color'] = icon_color
        #jobject.metadata['launch-times'] = str(int(time.time()))
        #jobject.metadata['spent-times'] = '0'

        jobject.file_path = ''

        # FIXME: We should be able to get an ID synchronously from the DS,
        # then call async the actual create.
        # http://bugs.sugarlabs.org/ticket/2169
        datastore.write(jobject)

        # TODO: list of handle.object_id for every entry to be implemented
        # Let the list contains first object_id of project itself
        jobject.metadata['objects']= [jobject.object_id]
        model.write(jobject.metadata)
        return jobject


    def _key_press_event_cb(self, widget, event):
        #if not self._main_toolbox.search_entry.has_focus():
        #self._main_toolbox.search_entry.grab_focus()

        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self._main_toolbox.clear_query()
            self.show_main_view()

    def __detail_clicked_cb(self, list_view, object_id):
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
        self._list_view.update_with_query(query)
        self.show_main_view()

    def __search_icon_pressed_cb(self, entry, icon_pos, event):
        self._main_view.grab_focus()

    def __title_edit_started_cb(self, list_view):
        self.disconnect_by_func(self._key_press_event_cb)

    def __title_edit_finished_cb(self, list_view):
        self.connect('key-press-event', self._key_press_event_cb)

    def show_main_view(self):
        self._main_view_active = True
        if self._editing_mode:
            self._toolbox = self._edit_toolbox
            self._toolbox.set_total_number_of_entries(
                self.get_total_number_of_entries())
        else:
            self._toolbox = self._main_toolbox

        self.set_toolbar_box(self._toolbox)
        self._toolbox.show()

        if self.canvas != self._main_view:
            self.set_canvas(self._main_view)
            self._main_view.show()

    def _show_secondary_view(self, object_id):
        self._main_view_active = False
        metadata = model.get(object_id)
        try:
            self._detail_toolbox.set_metadata(metadata)
        except Exception:
            logging.exception('Exception while displaying entry:')

        self.set_toolbar_box(self._detail_toolbox)
        self._detail_toolbox.show()

        try:
            self._detail_view.props.metadata = metadata
        except Exception:
            logging.exception('Exception while displaying entry:')

        self.set_canvas(self._secondary_view)
        self._secondary_view.show()

    def show_object(self, object_id):
        metadata = model.get(object_id)
        if metadata is None:
            return False
        else:
            self._show_secondary_view(object_id)
            return True

    def __volume_changed_cb(self, volume_toolbar, mount_point):
        logging.debug('Selected volume: %r.', mount_point)
        self._mount_point = mount_point
        self.set_editing_mode(False)
        self._main_toolbox.set_mount_point(mount_point)
        self._edit_toolbox.batch_copy_button.update_mount_point()

    def __model_created_cb(self, sender, **kwargs):
        misc.handle_bundle_installation(model.get(kwargs['object_id']))
        self._main_toolbox.refresh_filters()
        self._check_available_space()

    def __model_updated_cb(self, sender, **kwargs):
        misc.handle_bundle_installation(model.get(kwargs['object_id']))

        if self.canvas == self._secondary_view and \
                kwargs['object_id'] == self._detail_view.props.metadata['uid']:
            self._detail_view.refresh()

        self._check_available_space()

    def __model_deleted_cb(self, sender, **kwargs):
        if self.canvas == self._secondary_view and \
                kwargs['object_id'] == self._detail_view.props.metadata['uid']:
            self.show_main_view()

    def _focus_in_event_cb(self, window, event):
        if not self._main_view_active:
            return
        self._list_view.set_is_visible(True)

    def _focus_out_event_cb(self, window, event):
        self._list_view.set_is_visible(False)

    def __window_state_event_cb(self, window, event):
        logging.debug('window_state_event_cb %r', self)
        if not self._main_view_active:
            return

        if event.changed_mask & Gdk.WindowState.ICONIFIED:
            state = event.new_window_state
            visible = not state & Gdk.WindowState.ICONIFIED
            self._list_view.set_is_visible(visible)

    def _check_available_space(self):
        """Check available space on device

            If the available space is below 50MB an alert will be
            shown which encourages to delete old journal entries.
        """

        if self._critical_space_alert:
            return
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        if free_space < _SPACE_TRESHOLD:
            self._critical_space_alert = ModalAlert()
            self._critical_space_alert.connect('destroy',
                                               self.__alert_closed_cb)
            self._critical_space_alert.show()

    def __alert_closed_cb(self, data):
        self.show_main_view()
        self.reveal()
        self._critical_space_alert = None

    def set_active_volume(self, mount):
        self._volumes_toolbar.set_active_volume(mount)

    def show_journal(self):
        """Become visible and show main view"""
        self.reveal()
        self.show_main_view()

    def get_list_view(self):
        return self._list_view

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
        _journal.show()
    return _journal


def start():
    get_journal()
