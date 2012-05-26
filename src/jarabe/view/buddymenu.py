# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

import gtk
import gconf
import glib
import dbus

from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon

from jarabe.model import shell
from jarabe.model import friends
from jarabe.model.session import get_session_manager
from jarabe.controlpanel.gui import ControlPanel
import jarabe.desktop.homewindow


class BuddyMenu(Palette):
    def __init__(self, buddy):
        self._buddy = buddy

        buddy_icon = Icon(icon_name='computer-xo',
                          xo_color=buddy.get_color(),
                          icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
        nick = buddy.get_nick()
        Palette.__init__(self, None,
                         primary_text=glib.markup_escape_text(nick),
                         icon=buddy_icon)
        self._invite_menu = None
        self._active_activity_changed_hid = None
        self.connect('destroy', self.__destroy_cb)

        self._buddy.connect('notify::nick', self.__buddy_notify_nick_cb)

        if buddy.is_owner():
            self._add_my_items()
        else:
            self._add_buddy_items()

    def __destroy_cb(self, menu):
        if self._active_activity_changed_hid is not None:
            home_model = shell.get_model()
            home_model.disconnect(self._active_activity_changed_hid)
        self._buddy.disconnect_by_func(self.__buddy_notify_nick_cb)

    def _add_buddy_items(self):
        if friends.get_model().has_buddy(self._buddy):
            menu_item = MenuItem(_('Remove friend'), 'list-remove')
            menu_item.connect('activate', self._remove_friend_cb)
        else:
            menu_item = MenuItem(_('Make friend'), 'list-add')
            menu_item.connect('activate', self._make_friend_cb)

        self.menu.append(menu_item)
        menu_item.show()

        self._invite_menu = MenuItem('')
        self._invite_menu.connect('activate', self._invite_friend_cb)
        self.menu.append(self._invite_menu)

        home_model = shell.get_model()
        self._active_activity_changed_hid = home_model.connect(
                'active-activity-changed', self._cur_activity_changed_cb)
        activity = home_model.get_active_activity()
        self._update_invite_menu(activity)

    def _add_my_items(self):
        item = MenuItem(_('Shutdown'), 'system-shutdown')
        item.connect('activate', self.__shutdown_activate_cb)
        self.menu.append(item)
        item.show()

        client = gconf.client_get_default()

        if client.get_bool('/desktop/sugar/show_restart'):
            item = MenuItem(_('Restart'), 'system-restart')
            item.connect('activate', self.__reboot_activate_cb)
            self.menu.append(item)
            item.show()

        if client.get_bool('/desktop/sugar/show_logout'):
            item = MenuItem(_('Logout'), 'system-logout')
            item.connect('activate', self.__logout_activate_cb)
            self.menu.append(item)
            item.show()

        item = MenuItem(_('My Settings'), 'preferences-system')
        item.connect('activate', self.__controlpanel_activate_cb)
        self.menu.append(item)
        item.show()

    def _quit(self, action):
        home_window = jarabe.desktop.homewindow.get_instance()
        home_window.busy_during_delayed_action(action)

    def __logout_activate_cb(self, menu_item):
        self._quit(get_session_manager().logout)

    def __reboot_activate_cb(self, menu_item):
        self._quit(get_session_manager().reboot)

    def __shutdown_activate_cb(self, menu_item):
        self._quit(get_session_manager().shutdown)

    def __controlpanel_activate_cb(self, menu_item):
        panel = ControlPanel()
        panel.set_transient_for(self.get_toplevel())
        panel.show()

    def _update_invite_menu(self, activity):
        buddy_activity = self._buddy.props.current_activity
        if buddy_activity is not None:
            buddy_activity_id = buddy_activity.activity_id
        else:
            buddy_activity_id = None

        if activity is None or activity.is_journal() or \
           activity.get_activity_id() == buddy_activity_id:
            self._invite_menu.hide()
        else:
            title = activity.get_title()
            label = self._invite_menu.get_children()[0]
            label.set_text(_('Invite to %s') % title)

            icon = Icon(file=activity.get_icon_path())
            icon.props.xo_color = activity.get_icon_color()
            self._invite_menu.set_image(icon)
            icon.show()

            self._invite_menu.show()

    def _cur_activity_changed_cb(self, home_model, activity_model):
        self._update_invite_menu(activity_model)

    def __buddy_notify_nick_cb(self, buddy, pspec):
        self.set_primary_text(glib.markup_escape_text(buddy.props.nick))

    def _make_friend_cb(self, menuitem):
        friends.get_model().make_friend(self._buddy)

    def _remove_friend_cb(self, menuitem):
        friends.get_model().remove(self._buddy)

    def _invite_friend_cb(self, menuitem):
        activity = shell.get_model().get_active_activity()
        service = activity.get_service()
        if service:
            try:
                service.InviteContact(self._buddy.props.account,
                                      self._buddy.props.contact_id)
            except dbus.DBusException, e:
                expected_exceptions = [
                        'org.freedesktop.DBus.Error.UnknownMethod',
                        'org.freedesktop.DBus.Python.NotImplementedError']
                if e.get_dbus_name() in expected_exceptions:
                    logging.warning('Trying deprecated Activity.Invite')
                    service.Invite(self._buddy.props.key)
                else:
                    raise
        else:
            logging.error('Invite failed, activity service not ')
