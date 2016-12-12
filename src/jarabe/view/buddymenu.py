# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
import dbus

from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.icon import Icon
from sugar3.graphics.alert import TimeoutAlert
from sugar3.graphics import style
from sugar3.bundle.activitybundle import ActivityBundle

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
                          pixel_size=style.STANDARD_ICON_SIZE)
        nick = buddy.get_nick()
        Palette.__init__(self, None, primary_text=nick, icon=buddy_icon)
        self.menu_box = Gtk.VBox()
        self.set_content(self.menu_box)
        self.menu_box.show_all()
        self._invite_menu = None
        self._active_activity_changed_hid = None
        # Fixme: we need to make the widget accessible through the Palette API
        self._widget.connect('destroy', self.__destroy_cb)

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
        menu_item = None
        if friends.get_model().has_buddy(self._buddy):
            menu_item = PaletteMenuItem(_('Remove friend'), 'list-remove')
            menu_item.connect('activate', self._remove_friend_cb)
        else:
            menu_item = PaletteMenuItem(_('Make friend'), 'list-add')
            menu_item.connect('activate', self._make_friend_cb)

        self.menu_box.pack_start(menu_item, True, True, 0)

        self._invite_menu = PaletteMenuItem('')
        self._invite_menu.connect('activate', self._invite_friend_cb)
        self.menu_box.pack_start(self._invite_menu, True, True, 0)

        home_model = shell.get_model()
        self._active_activity_changed_hid = home_model.connect(
            'active-activity-changed', self._cur_activity_changed_cb)
        activity = home_model.get_active_activity()
        self._update_invite_menu(activity)

    def _add_my_items(self):
        settings = Gio.Settings('org.sugarlabs')

        show_shutdown = settings.get_boolean('show-shutdown')
        show_restart = settings.get_boolean('show-restart')
        show_logout = settings.get_boolean('show-logout')

        if "SUGAR_SHOW_SHUTDOWN" in os.environ:
            show_shutdown = os.environ["SUGAR_SHOW_SHUTDOWN"] == "yes"

        if "SUGAR_SHOW_RESTART" in os.environ:
            show_restart = os.environ["SUGAR_SHOW_RESTART"] == "yes"

        if "SUGAR_SHOW_LOGOUT" in os.environ:
            show_logout = os.environ["SUGAR_SHOW_LOGOUT"] == "yes"

        if show_shutdown:
            item = PaletteMenuItem(_('Shutdown'), 'system-shutdown')
            item.connect('activate', self.__shutdown_activate_cb)
            self.menu_box.pack_start(item, True, True, 0)

        if show_restart:
            item = PaletteMenuItem(_('Restart'), 'system-restart')
            item.connect('activate', self.__reboot_activate_cb)
            self.menu_box.pack_start(item, True, True, 0)
            item.show()

        if show_logout:
            item = PaletteMenuItem(_('Logout'), 'system-logout')
            item.connect('activate', self.__logout_activate_cb)
            self.menu_box.pack_start(item, True, True, 0)
            item.show()

        item = PaletteMenuItem(_('My Settings'), 'preferences-system')
        item.connect('activate', self.__controlpanel_activate_cb)
        self.menu_box.pack_start(item, True, True, 0)
        item.show()

    def _quit(self, action):
        jarabe.desktop.homewindow.get_instance().busy()
        action()
        GObject.timeout_add_seconds(3, self.__quit_timeout_cb)

    def __quit_timeout_cb(self):
        jarabe.desktop.homewindow.get_instance().unbusy()
        alert = TimeoutAlert(30)
        alert.props.title = _('An activity is not responding.')
        alert.props.msg = _('You may lose unsaved work if you continue.')
        alert.connect('response', self.__quit_accept_cb)

        jarabe.desktop.homewindow.get_instance().add_alert(alert)
        alert.show()

    def __quit_accept_cb(self, alert, response_id):
        jarabe.desktop.homewindow.get_instance().remove_alert(alert)
        if response_id is Gtk.ResponseType.CANCEL:
            get_session_manager().cancel_shutdown()
        else:
            jarabe.desktop.homewindow.get_instance().busy()
            get_session_manager().shutdown_completed()

    def __logout_activate_cb(self, menu_item):
        self._quit(get_session_manager().logout)

    def __reboot_activate_cb(self, menu_item):
        self._quit(get_session_manager().reboot)

    def __shutdown_activate_cb(self, menu_item):
        self._quit(get_session_manager().shutdown)

    def __controlpanel_activate_cb(self, menu_item):
        # hide the frame when control panel is shown
        import jarabe.frame
        frame = jarabe.frame.get_view()
        frame.hide()

        # show the control panel
        panel = ControlPanel()
        panel.show()

    def _update_invite_menu(self, activity):
        buddy_activity = self._buddy.props.current_activity
        if buddy_activity is not None:
            buddy_activity_id = buddy_activity.activity_id
        else:
            buddy_activity_id = None

        self._invite_menu.hide()
        if activity is None or \
           activity.is_journal() or \
           activity.get_activity_id() == buddy_activity_id:
            return

        bundle_activity = ActivityBundle(activity.get_bundle_path())
        if bundle_activity.get_max_participants() > 1:
            title = activity.get_title()
            self._invite_menu.set_label(_('Invite to %s') % title)

            icon = Icon(file=activity.get_icon_path(),
                        pixel_size=style.SMALL_ICON_SIZE)
            icon.props.xo_color = activity.get_icon_color()
            self._invite_menu.set_image(icon)
            icon.show()

            self._invite_menu.show()

    def _cur_activity_changed_cb(self, home_model, activity_model):
        self._update_invite_menu(activity_model)

    def __buddy_notify_nick_cb(self, buddy, pspec):
        self.set_primary_text(buddy.props.nick)

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
            except dbus.DBusException as e:
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
