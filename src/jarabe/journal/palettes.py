# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2014 Ignacio Rodriguez
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

from gettext import gettext as _
from gettext import ngettext
import logging
import os

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import SugarExt

from sugar3.graphics import style
from sugar3.graphics.palette import Palette
from sugar3.graphics.menuitem import MenuItem
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.alert import Alert
from sugar3 import mime
from sugar3 import profile

from jarabe.model import friends
from jarabe.model import filetransfer
from jarabe.model import mimeregistry
from jarabe.journal import misc
from jarabe.journal import model
from jarabe.journal import journalwindow
from jarabe.webservice import accountsmanager
from jarabe.journal.misc import get_mount_color

PROJECT_BUNDLE_ID = 'org.sugarlabs.Project'


class ObjectPalette(Palette):

    __gtype_name__ = 'ObjectPalette'

    __gsignals__ = {
        'detail-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                           ([str])),
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
        'choose-project': (GObject.SignalFlags.RUN_FIRST, None,
                          ([object])),
    }

    def __init__(self, journalactivity, metadata, detail=False):

        self._journalactivity = journalactivity
        self._metadata = metadata

        activity_icon = Icon(pixel_size=style.STANDARD_ICON_SIZE)
        activity_icon.props.file = misc.get_icon_name(metadata)
        color = misc.get_icon_color(metadata)
        activity_icon.props.xo_color = color

        if 'title' in metadata:
            title = metadata['title']
        else:
            title = _('Untitled')

        Palette.__init__(self, primary_text=title,
                         icon=activity_icon)

        description = metadata.get('description', '')
        if description:
            self.set_secondary_text(description)

        if misc.can_resume(metadata):
            if metadata.get('activity_id', ''):
                resume_label = _('Resume')
                resume_with_label = _('Resume with')
            else:
                resume_label = _('Start')
                resume_with_label = _('Start with')
            menu_item = MenuItem(resume_label, 'activity-start')
            menu_item.connect('activate', self.__start_activate_cb)
            self.menu.append(menu_item)
            menu_item.show()

            menu_item = MenuItem(resume_with_label, 'activity-start')
            self.menu.append(menu_item)
            menu_item.show()
            start_with_menu = StartWithMenu(self._metadata)
            menu_item.set_submenu(start_with_menu)

        elif metadata.get('activity', None) == PROJECT_BUNDLE_ID:
            open_label = _('Open')
            menu_item = MenuItem(open_label, 'project-box')
            menu_item.connect('activate', self.__open_project_activate_cb)
            self.menu.append(menu_item)
            menu_item.show()

        else:
            menu_item = MenuItem(_('No activity to start entry'))
            menu_item.set_sensitive(False)
            self.menu.append(menu_item)
            menu_item.show()

        menu_item = MenuItem(_('Copy to'))
        icon = Icon(icon_name='edit-copy', xo_color=color,
                    pixel_size=style.SMALL_ICON_SIZE)
        menu_item.set_image(icon)
        self.menu.append(menu_item)
        menu_item.show()
        copy_menu = CopyMenu(self._journalactivity, self.__get_uid_list_cb)
        copy_menu.connect('volume-error', self.__volume_error_cb)
        menu_item.set_submenu(copy_menu)

        if not metadata.get('activity', None) == PROJECT_BUNDLE_ID:
            menu_item = MenuItem(_('Send to project...'), 'project-box')
            menu_item.connect('activate', self.__copy_to_project_activated_cb)
            self.menu.append(menu_item)
            menu_item.show()

        if self._metadata['mountpoint'] == '/':
            menu_item = MenuItem(_('Duplicate'))
            icon = Icon(icon_name='edit-duplicate', xo_color=color,
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            menu_item.connect('activate', self.__duplicate_activate_cb)
            self.menu.append(menu_item)
            menu_item.show()

        menu_item = MenuItem(_('Send to'), 'document-send')
        self.menu.append(menu_item)
        menu_item.show()

        friends_menu = FriendsMenu()
        friends_menu.connect('friend-selected', self.__friend_selected_cb)
        menu_item.set_submenu(friends_menu)

        if detail is True:
            menu_item = MenuItem(_('View Details'), 'go-right')
            menu_item.connect('activate', self.__detail_activate_cb)
            self.menu.append(menu_item)
            menu_item.show()

        menu_item = MenuItem(_('Erase'), 'list-remove')
        menu_item.connect('activate', self.__erase_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __get_uid_list_cb(self):
        return [self._metadata['uid']]

    def __copy_to_project_activated_cb(self, menu_item):
        self.emit('choose-project', self._metadata)
        self.destroy()

    def __open_project_activate_cb(self, menu_item):
        self._journalactivity.project_view_activated_cb(
            list_view=None,
            metadata=self._metadata)

    def __start_activate_cb(self, menu_item):
        misc.resume(self._metadata,
                    alert_window=journalwindow.get_journal_window())

    def __duplicate_activate_cb(self, menu_item):
        try:
            model.copy(self._metadata, '/')
        except IOError as e:
            logging.exception('Error while copying the entry. %s', e.strerror)
            self.emit('volume-error',
                      _('Error while copying the entry. %s') % e.strerror,
                      _('Error'))

    def __erase_activate_cb(self, menu_item):
        alert = Alert()
        erase_string = _('Erase')
        alert.props.title = erase_string
        alert.props.msg = _('Do you want to permanently erase \"%s\"?') \
            % self._metadata['title']
        icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), icon)
        icon.show()
        ok_icon = Icon(icon_name='dialog-ok')
        alert.add_button(Gtk.ResponseType.OK, erase_string, ok_icon)
        ok_icon.show()
        alert.connect('response', self.__erase_alert_response_cb)
        journalwindow.get_journal_window().add_alert(alert)
        alert.show()

    def __erase_alert_response_cb(self, alert, response_id):
        journalwindow.get_journal_window().remove_alert(alert)
        if response_id is Gtk.ResponseType.OK:
            model.delete(self._metadata['uid'])

    def __detail_activate_cb(self, menu_item):
        self.emit('detail-clicked', self._metadata['uid'])

    def __volume_error_cb(self, menu_item, message, severity):
        self.emit('volume-error', message, severity)

    def __friend_selected_cb(self, menu_item, buddy):
        logging.debug('__friend_selected_cb')
        file_name = model.get_file(self._metadata['uid'])

        if not file_name or not os.path.exists(file_name):
            logging.warn('Entries without a file cannot be sent.')
            self.emit('volume-error',
                      _('Entries without a file cannot be sent.'),
                      _('Warning'))
            return

        title = str(self._metadata['title'])
        description = str(self._metadata.get('description', ''))
        mime_type = str(self._metadata['mime_type'])

        if not mime_type:
            mime_type = mime.get_for_file(file_name)

        filetransfer.start_transfer(buddy, file_name, title, description,
                                    mime_type)

    def popup(self, immediate=False, state=None):
        if self._journalactivity.get_list_view().is_dragging():
            return

        Palette.popup(self, immediate)


class CopyMenu(Gtk.Menu):
    __gtype_name__ = 'JournalCopyMenu'

    __gsignals__ = {
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, journalactivity, get_uid_list_cb):
        Gtk.Menu.__init__(self)
        CopyMenuBuilder(journalactivity, get_uid_list_cb,
                        self.__volume_error_cb, self)

    def __volume_error_cb(self, menu_item, message, severity):
        self.emit('volume-error', message, severity)


class CopyMenuBuilder():

    def __init__(self, journalactivity, get_uid_list_cb, __volume_error_cb,
                 menu, add_clipboard_menu=True, add_webservices_menu=True):

        self._journalactivity = journalactivity
        self._get_uid_list_cb = get_uid_list_cb
        self.__volume_error_cb = __volume_error_cb
        self._menu = menu
        self._add_clipboard_menu = add_clipboard_menu
        self._add_webservices_menu = add_webservices_menu

        self._mount_added_hid = None
        self._mount_removed_hid = None
        self._create_menu_items()

    def _create_menu_items(self):
        if self._add_clipboard_menu:
            clipboard_menu = ClipboardMenu(self._get_uid_list_cb)
            clipboard_menu.set_image(Icon(icon_name='toolbar-edit',
                                          pixel_size=style.SMALL_ICON_SIZE))
            clipboard_menu.connect('volume-error', self.__volume_error_cb)
            self._menu.append(clipboard_menu)
            clipboard_menu.show()

        if self._journalactivity.get_mount_point() != '/':
            color = profile.get_color()
            journal_menu = VolumeMenu(self._journalactivity,
                                      self._get_uid_list_cb, _('Journal'), '/')
            journal_menu.set_image(Icon(icon_name='activity-journal',
                                        xo_color=color,
                                        pixel_size=style.SMALL_ICON_SIZE))
            journal_menu.connect('volume-error', self.__volume_error_cb)
            self._menu.append(journal_menu)
            journal_menu.show()

        documents_path = model.get_documents_path()
        if documents_path is not None and \
                self._journalactivity.get_mount_point() != documents_path:
            documents_menu = VolumeMenu(self._journalactivity,
                                        self._get_uid_list_cb, _('Documents'),
                                        documents_path)
            documents_menu.set_image(Icon(icon_name='user-documents',
                                          pixel_size=style.SMALL_ICON_SIZE))
            documents_menu.connect('volume-error', self.__volume_error_cb)
            self._menu.append(documents_menu)
            documents_menu.show()

        volume_monitor = Gio.VolumeMonitor.get()
        self._volumes = {}
        for mount in volume_monitor.get_mounts():
            self._add_mount(mount)

        self._mount_added_hid = volume_monitor.connect('mount-added',
                                                       self.__mount_added_cb)
        self._mount_removed_hid = volume_monitor.connect(
            'mount-removed',
            self.__mount_removed_cb)

        if self._add_webservices_menu:
            for account in accountsmanager.get_configured_accounts():
                if hasattr(account, 'get_shared_journal_entry'):
                    entry = account.get_shared_journal_entry()
                    if hasattr(entry, 'get_share_menu'):
                        self._menu.append(entry.get_share_menu(
                                          self._get_uid_list_cb))

    def update_mount_point(self):
        for menu_item in self._menu.get_children():
            if isinstance(menu_item, MenuItem):
                self._menu.remove(menu_item)
        self._create_menu_items()

    def __mount_added_cb(self, volume_monitor, mount):
        self._add_mount(mount)

    def _add_mount(self, mount):
        mount_path = mount.get_root().get_path()
        if mount_path in self._volumes:
            return
        if self._journalactivity.get_mount_point() == mount_path:
            return
        volume_menu = VolumeMenu(self._journalactivity,
                                 self._get_uid_list_cb, mount.get_name(),
                                 mount.get_root().get_path())
        icon_name = misc.get_mount_icon_name(mount, Gtk.IconSize.MENU)
        icon = Icon(pixel_size=style.SMALL_ICON_SIZE,
                    icon_name=icon_name,
                    xo_color=get_mount_color(mount))

        volume_menu.set_image(icon)
        volume_menu.connect('volume-error', self.__volume_error_cb)
        self._menu.append(volume_menu)
        self._volumes[mount.get_root().get_path()] = volume_menu
        volume_menu.show()

    def __mount_removed_cb(self, volume_monitor, mount):
        volume_menu = self._volumes[mount.get_root().get_path()]
        self._menu.remove(volume_menu)
        del self._volumes[mount.get_root().get_path()]

    def __destroy_cb(self, widget):
        volume_monitor = Gio.VolumeMonitor.get()
        volume_monitor.disconnect(self._mount_added_hid)
        volume_monitor.disconnect(self._mount_removed_hid)


class VolumeMenu(MenuItem):
    __gtype_name__ = 'JournalVolumeMenu'

    __gsignals__ = {
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, journalactivity, get_uid_list_cb, label, mount_point):
        MenuItem.__init__(self, label)
        self._get_uid_list_cb = get_uid_list_cb
        self._journalactivity = journalactivity
        self._mount_point = mount_point
        self.connect('activate', self.__copy_to_volume_cb)

    def __copy_to_volume_cb(self, menu_item):
        uid_list = self._get_uid_list_cb()
        if len(uid_list) == 1:
            uid = uid_list[0]
            file_path = model.get_file(uid)

            if not file_path or not os.path.exists(file_path):
                logging.warn('Entries without a file cannot be copied.')
                self.emit('volume-error',
                          _('Entries without a file cannot be copied.'),
                          _('Warning'))
                return

            try:
                metadata = model.get(uid)
                model.copy(metadata, self._mount_point)
            except IOError as e:
                logging.exception('Error while copying the entry. %s',
                                  e.strerror)
                self.emit('volume-error',
                          _('Error while copying the entry. %s') % e.strerror,
                          _('Error'))
        else:
            BatchOperator(
                self._journalactivity, uid_list, _('Copy'),
                self._get_confirmation_alert_message(len(uid_list)),
                self._perform_copy)

    def _get_confirmation_alert_message(self, entries_len):
        return ngettext('Do you want to copy %d entry?',
                        'Do you want to copy %d entries?',
                        entries_len) % (entries_len)

    def _perform_copy(self, metadata):
        file_path = model.get_file(metadata['uid'])
        if not file_path or not os.path.exists(file_path):
            logging.warn('Entries without a file cannot be copied.')
            return
        try:
            model.copy(metadata, self._mount_point)
        except IOError as e:
            logging.exception('Error while copying the entry. %s',
                              e.strerror)


class ClipboardMenu(MenuItem):
    __gtype_name__ = 'JournalClipboardMenu'

    __gsignals__ = {
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, get_uid_list_cb):
        MenuItem.__init__(self, _('Clipboard'))

        self._temp_file_path = None
        self._get_uid_list_cb = get_uid_list_cb
        self.connect('activate', self.__copy_to_clipboard_cb)

    def __copy_to_clipboard_cb(self, menu_item):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        uid_list = self._get_uid_list_cb()
        if len(uid_list) == 1:
            uid = uid_list[0]
            file_path = model.get_file(uid)
            if not file_path or not os.path.exists(file_path):
                logging.warn('Entries without a file cannot be copied.')
                self.emit('volume-error',
                          _('Entries without a file cannot be copied.'),
                          _('Warning'))
                return

            # XXX SL#4307 - until set_with_data bindings are fixed upstream
            if hasattr(clipboard, 'set_with_data'):
                clipboard.set_with_data(
                    [Gtk.TargetEntry.new('text/uri-list', 0, 0)],
                    self.__clipboard_get_func_cb,
                    self.__clipboard_clear_func_cb,
                    None)
            else:
                SugarExt.clipboard_set_with_data(
                    clipboard,
                    [Gtk.TargetEntry.new('text/uri-list', 0, 0)],
                    self.__clipboard_get_func_cb,
                    self.__clipboard_clear_func_cb,
                    None)

    def __clipboard_get_func_cb(self, clipboard, selection_data, info, data):
        # Get hold of a reference so the temp file doesn't get deleted
        for uid in self._get_uid_list_cb():
            self._temp_file_path = model.get_file(uid)
            logging.debug('__clipboard_get_func_cb %r', self._temp_file_path)
            selection_data.set_uris(['file://' + self._temp_file_path])

    def __clipboard_clear_func_cb(self, clipboard, data):
        # Release and delete the temp file
        self._temp_file_path = None


class FriendsMenu(Gtk.Menu):
    __gtype_name__ = 'JournalFriendsMenu'

    __gsignals__ = {
        'friend-selected': (GObject.SignalFlags.RUN_FIRST, None,
                            ([object])),
    }

    def __init__(self):
        Gtk.Menu.__init__(self)

        if filetransfer.file_transfer_available():
            friends_model = friends.get_model()
            for friend in friends_model:
                if friend.is_present():
                    menu_item = MenuItem(text_label=friend.get_nick(),
                                         icon_name='computer-xo',
                                         xo_color=friend.get_color())
                    menu_item.connect('activate', self.__item_activate_cb,
                                      friend)
                    self.append(menu_item)
                    menu_item.show()

            if not self.get_children():
                menu_item = MenuItem(_('No friends present'))
                menu_item.set_sensitive(False)
                self.append(menu_item)
                menu_item.show()
        else:
            menu_item = MenuItem(_('No valid connection found'))
            menu_item.set_sensitive(False)
            self.append(menu_item)
            menu_item.show()

    def __item_activate_cb(self, menu_item, friend):
        self.emit('friend-selected', friend)


class StartWithMenu(Gtk.Menu):
    __gtype_name__ = 'JournalStartWithMenu'

    def __init__(self, metadata):
        Gtk.Menu.__init__(self)

        self._metadata = metadata

        for activity_info in misc.get_activities(metadata):
            menu_item = MenuItem(activity_info.get_name())
            menu_item.set_image(Icon(file=activity_info.get_icon(),
                                     pixel_size=style.SMALL_ICON_SIZE))
            menu_item.connect('activate', self.__item_activate_cb,
                              activity_info.get_bundle_id())
            self.append(menu_item)
            menu_item.show()

        if not self.get_children():
            if metadata.get('activity_id', ''):
                resume_label = _('No activity to resume entry')
            else:
                resume_label = _('No activity to start entry')
            menu_item = MenuItem(resume_label)
            menu_item.set_sensitive(False)
            self.append(menu_item)
            menu_item.show()

    def __item_activate_cb(self, menu_item, service_name):
        mime_type = self._metadata.get('mime_type', '')
        if mime_type:
            mime_registry = mimeregistry.get_registry()
            mime_registry.set_default_activity(mime_type, service_name)
        misc.resume(self._metadata, bundle_id=service_name,
                    alert_window=journalwindow.get_journal_window())


class BuddyPalette(Palette):

    def __init__(self, buddy):
        self._buddy = buddy

        nick, colors = buddy
        buddy_icon = Icon(icon_name='computer-xo',
                          pixel_size=style.STANDARD_ICON_SIZE,
                          xo_color=XoColor(colors))

        Palette.__init__(self, primary_text=nick, icon=buddy_icon)

        # TODO: Support actions on buddies, like make friend, invite, etc.


class BatchOperator(GObject.GObject):
    """
    This class implements the course of actions that happens when clicking
    upon an BatchOperation  (eg. Batch-Copy-Toolbar-button;
                             Batch-Copy-To-Journal-button;
                             Batch-Copy-To-Documents-button;
                             Batch-Copy-To-Mounted-Drive-button;
                             Batch-Copy-To-Clipboard-button;
                             Batch-Erase-Button;
    """

    def __init__(self, journalactivity,
                 uid_list,
                 alert_title, alert_message,
                 operation_cb):
        GObject.GObject.__init__(self)

        self._journalactivity = journalactivity

        self._uid_list = uid_list[:]
        self._alert_title = alert_title
        self._alert_message = alert_message
        self._operation_cb = operation_cb

        self._show_confirmation_alert()

    def _show_confirmation_alert(self):
        self._journalactivity.freeze_ui()
        GObject.idle_add(self.__show_confirmation_alert_internal)

    def __show_confirmation_alert_internal(self):
        # Show a alert requesting confirmation before run the batch operation
        self._confirmation_alert = Alert()
        self._confirmation_alert.props.title = self._alert_title
        self._confirmation_alert.props.msg = self._alert_message

        stop_icon = Icon(icon_name='dialog-cancel')
        self._confirmation_alert.add_button(Gtk.ResponseType.CANCEL,
                                            _('Stop'), stop_icon)
        stop_icon.show()

        ok_icon = Icon(icon_name='dialog-ok')
        self._confirmation_alert.add_button(Gtk.ResponseType.OK,
                                            _('Continue'), ok_icon)
        ok_icon.show()

        self._journalactivity.add_alert(self._confirmation_alert)
        self._confirmation_alert.connect('response',
                                         self.__confirmation_response_cb)
        self._confirmation_alert.show()

    def __confirmation_response_cb(self, alert, response):
        if response == Gtk.ResponseType.CANCEL:
            self._journalactivity.unfreeze_ui()
            self._journalactivity.remove_alert(alert)
            # this is only in the case the operation already started
            # and the user want stop it.
            self._stop_batch_execution()
        elif hasattr(self, '_object_index') == False:
            self._object_index = 0
            GObject.idle_add(self._operate_by_uid_internal)

    def _operate_by_uid_internal(self):
        # If there is still some uid left, proceed with the operation.
        # Else, proceed to post-operations.
        if self._object_index < len(self._uid_list):
            uid = self._uid_list[self._object_index]
            metadata = model.get(uid)
            title = None
            if 'title' in metadata:
                title = metadata['title']
            if title is None or title == '':
                title = _('Untitled')
            alert_message = _('%(index)d of %(total)d : %(object_title)s') % {
                'index': self._object_index + 1,
                'total': len(self._uid_list),
                'object_title': title}

            self._confirmation_alert.props.msg = alert_message
            GObject.idle_add(self._operate_per_metadata, metadata)
        else:
            self._finish_batch_execution()

    def _operate_per_metadata(self, metadata):
        self._operation_cb(metadata)

        # process the next
        self._object_index = self._object_index + 1
        GObject.idle_add(self._operate_by_uid_internal)

    def _stop_batch_execution(self):
        self._object_index = len(self._uid_list)

    def _finish_batch_execution(self):
        del self._object_index
        self._journalactivity.unfreeze_ui()
        self._journalactivity.remove_alert(self._confirmation_alert)
        self._journalactivity.update_selected_items_ui()
