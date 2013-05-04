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

from gettext import gettext as _
import logging
import os

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GConf
from gi.repository import Gio
from gi.repository import GLib

from sugar3.graphics import style
from sugar3.graphics.palette import Palette
from sugar3.graphics.menuitem import MenuItem
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.alert import Alert
from sugar3 import mime

from jarabe.model import friends
from jarabe.model import filetransfer
from jarabe.model import mimeregistry
from jarabe.journal import misc
from jarabe.journal import model
from jarabe.journal import journalwindow


class ObjectPalette(Palette):

    __gtype_name__ = 'ObjectPalette'

    __gsignals__ = {
        'detail-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                           ([str])),
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, metadata, detail=False):

        self._metadata = metadata

        activity_icon = Icon(icon_size=Gtk.IconSize.LARGE_TOOLBAR)
        activity_icon.props.file = misc.get_icon_name(metadata)
        color = misc.get_icon_color(metadata)
        activity_icon.props.xo_color = color

        if 'title' in metadata:
            title = GObject.markup_escape_text(metadata['title'])
        else:
            title = GLib.markup_escape_text(_('Untitled'))

        Palette.__init__(self, primary_text=title,
                         icon=activity_icon)

        if misc.get_activities(metadata) or misc.is_bundle(metadata):
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

        else:
            menu_item = MenuItem(_('No activity to start entry'))
            menu_item.set_sensitive(False)
            self.menu.append(menu_item)
            menu_item.show()

        menu_item = MenuItem(_('Copy to'))
        icon = Icon(icon_name='edit-copy', xo_color=color,
                    icon_size=Gtk.IconSize.MENU)
        menu_item.set_image(icon)
        self.menu.append(menu_item)
        menu_item.show()
        copy_menu = CopyMenu(metadata)
        copy_menu.connect('volume-error', self.__volume_error_cb)
        menu_item.set_submenu(copy_menu)

        if self._metadata['mountpoint'] == '/':
            menu_item = MenuItem(_('Duplicate'))
            icon = Icon(icon_name='edit-duplicate', xo_color=color,
                        icon_size=Gtk.IconSize.MENU)
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

        if detail == True:
            menu_item = MenuItem(_('View Details'), 'go-right')
            menu_item.connect('activate', self.__detail_activate_cb)
            self.menu.append(menu_item)
            menu_item.show()

        menu_item = MenuItem(_('Erase'), 'list-remove')
        menu_item.connect('activate', self.__erase_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __start_activate_cb(self, menu_item):
        misc.resume(self._metadata)

    def __duplicate_activate_cb(self, menu_item):
        try:
            model.copy(self._metadata, '/')
        except IOError, e:
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


class CopyMenu(Gtk.Menu):
    __gtype_name__ = 'JournalCopyMenu'

    __gsignals__ = {
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, metadata):
        Gtk.Menu.__init__(self)

        self._metadata = metadata

        clipboard_menu = ClipboardMenu(self._metadata)
        clipboard_menu.set_image(Icon(icon_name='toolbar-edit',
                                      icon_size=Gtk.IconSize.MENU))
        clipboard_menu.connect('volume-error', self.__volume_error_cb)
        self.append(clipboard_menu)
        clipboard_menu.show()

        if self._metadata['mountpoint'] != '/':
            client = GConf.Client.get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            journal_menu = VolumeMenu(self._metadata, _('Journal'), '/')
            journal_menu.set_image(Icon(icon_name='activity-journal',
                                        xo_color=color,
                                        icon_size=Gtk.IconSize.MENU))
            journal_menu.connect('volume-error', self.__volume_error_cb)
            self.append(journal_menu)
            journal_menu.show()

        documents_path = model.get_documents_path()
        if documents_path is not None and not \
                self._metadata['uid'].startswith(documents_path):
            documents_menu = VolumeMenu(self._metadata, _('Documents'),
                                        documents_path)
            documents_menu.set_image(Icon(icon_name='user-documents',
                                          icon_size=Gtk.IconSize.MENU))
            documents_menu.connect('volume-error', self.__volume_error_cb)
            self.append(documents_menu)
            documents_menu.show()

        volume_monitor = Gio.VolumeMonitor.get()
        icon_theme = Gtk.IconTheme.get_default()
        for mount in volume_monitor.get_mounts():
            if self._metadata['mountpoint'] == mount.get_root().get_path():
                continue
            volume_menu = VolumeMenu(self._metadata, mount.get_name(),
                                   mount.get_root().get_path())
            for name in mount.get_icon().props.names:
                if icon_theme.has_icon(name):
                    volume_menu.set_image(Icon(icon_name=name,
                                               icon_size=Gtk.IconSize.MENU))
                    break
            volume_menu.connect('volume-error', self.__volume_error_cb)
            self.append(volume_menu)
            volume_menu.show()

    def __volume_error_cb(self, menu_item, message, severity):
        self.emit('volume-error', message, severity)


class VolumeMenu(MenuItem):
    __gtype_name__ = 'JournalVolumeMenu'

    __gsignals__ = {
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, metadata, label, mount_point):
        MenuItem.__init__(self, label)
        self._metadata = metadata
        self.connect('activate', self.__copy_to_volume_cb, mount_point)

    def __copy_to_volume_cb(self, menu_item, mount_point):
        file_path = model.get_file(self._metadata['uid'])

        if not file_path or not os.path.exists(file_path):
            logging.warn('Entries without a file cannot be copied.')
            self.emit('volume-error',
                      _('Entries without a file cannot be copied.'),
                      _('Warning'))
            return

        try:
            model.copy(self._metadata, mount_point)
        except IOError, e:
            logging.exception('Error while copying the entry. %s', e.strerror)
            self.emit('volume-error',
                      _('Error while copying the entry. %s') % e.strerror,
                      _('Error'))


class ClipboardMenu(MenuItem):
    __gtype_name__ = 'JournalClipboardMenu'

    __gsignals__ = {
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, metadata):
        MenuItem.__init__(self, _('Clipboard'))

        self._temp_file_path = None
        self._metadata = metadata
        self.connect('activate', self.__copy_to_clipboard_cb)

    def __copy_to_clipboard_cb(self, menu_item):
        file_path = model.get_file(self._metadata['uid'])
        if not file_path or not os.path.exists(file_path):
            logging.warn('Entries without a file cannot be copied.')
            self.emit('volume-error',
                      _('Entries without a file cannot be copied.'),
                      _('Warning'))
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_with_data([Gtk.TargetEntry.new('text/uri-list', 0, 0)],
                                self.__clipboard_get_func_cb,
                                self.__clipboard_clear_func_cb, None)

    def __clipboard_get_func_cb(self, clipboard, selection_data, info, data):
        # Get hold of a reference so the temp file doesn't get deleted
        self._temp_file_path = model.get_file(self._metadata['uid'])
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
                                     icon_size=Gtk.IconSize.MENU))
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
        misc.resume(self._metadata, service_name)


class BuddyPalette(Palette):
    def __init__(self, buddy):
        self._buddy = buddy

        nick, colors = buddy
        buddy_icon = Icon(icon_name='computer-xo',
                          icon_size=style.STANDARD_ICON_SIZE,
                          xo_color=XoColor(colors))

        Palette.__init__(self, primary_text=GLib.markup_escape_text(nick),
                         icon=buddy_icon)

        # TODO: Support actions on buddies, like make friend, invite, etc.
