# Copyright (C) 2006-2007 Red Hat, Inc.
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

import logging
from gettext import gettext as _
import gtk

from sugar.graphics import style
from sugar.graphics.tray import HTray
from sugar.graphics.xocolor import XoColor
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette, WidgetInvoker
from sugar.graphics.menuitem import MenuItem
from sugar import activity

from model import shellmodel
from view.palettes import JournalPalette, CurrentActivityPalette
from view.pulsingicon import PulsingIcon
from view.frame.frameinvoker import FrameWidgetInvoker
from view.frame.notification import NotificationIcon
import view.frame.frame

class ActivityButton(RadioToolButton):
    def __init__(self, home_activity, group):
        RadioToolButton.__init__(self, group=group)

        self._home_activity = home_activity

        self._icon = PulsingIcon()
        self._icon.props.base_color = home_activity.get_icon_color()
        self._icon.props.pulse_color = \
                XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                   style.COLOR_TOOLBAR_GREY.get_svg()))
        if home_activity.get_icon_path():
            self._icon.props.file = home_activity.get_icon_path()
        else:
            self._icon.props.icon_name = 'image-missing'
        self.set_icon_widget(self._icon)
        self._icon.show()

        if self._home_activity.get_type() == "org.laptop.JournalActivity":
            palette = JournalPalette(self._home_activity)
        else:
            palette = CurrentActivityPalette(self._home_activity)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        self.set_palette(palette)

        if home_activity.props.launching:
            self._icon.props.pulsing = True
            self._notify_launching_hid = home_activity.connect( \
                    'notify::launching', self.__notify_launching_cb)

            self._notif_icon = NotificationIcon()
            self._notif_icon.props.xo_color = home_activity.get_icon_color()
            if home_activity.get_icon_path():
                icon_path = home_activity.get_icon_path()
                self._notif_icon.props.icon_filename = icon_path
            else:
                self._notif_icon.props.icon_name = 'image-missing'
            frame = view.frame.frame.get_instance()
            frame.add_notification(self._notif_icon, view.frame.frame.TOP_LEFT)
        else:
            self._notify_launching_hid = None
            self._notif_icon = None

    def __notify_launching_cb(self, home_activity, pspec):
        if not home_activity.props.launching:
            if self._notif_icon is not None:
                frame = view.frame.frame.get_instance()
                frame.remove_notification(self._notif_icon)
                self._notif_icon = None
            self._icon.props.pulsing = False
            home_activity.disconnect(self._notify_launching_hid)

class InviteButton(ToolButton):
    def __init__(self, activity_model):
        ToolButton.__init__(self)

        self._activity_model = activity_model

        self._icon = Icon()
        self._icon.props.xo_color = activity_model.get_color()
        if activity_model.get_icon_name():
            self._icon.props.file = activity_model.get_icon_name()
        else:
            self._icon.props.icon_name = 'image-missing'
        self.set_icon_widget(self._icon)
        self._icon.show()

        palette = InvitePalette(activity_model)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        self.set_palette(palette)

        self.connect('clicked', self.__clicked_cb)
        self.connect('destroy', self.__destroy_cb)

        self._notif_icon = NotificationIcon()
        self._notif_icon.props.xo_color = activity_model.get_color()
        if activity_model.get_icon_name():
            icon_name = activity_model.get_icon_name()
            self._notif_icon.props.icon_filename = icon_name
        else:
            self._notif_icon.props.icon_name = 'image-missing'
        self._notif_icon.connect('button-release-event',
                                 self.__button_release_event_cb)

        palette = InvitePalette(activity_model)
        palette.props.invoker = WidgetInvoker(self._notif_icon)
        palette.set_group_id('frame')
        self._notif_icon.palette = palette

        view.frame.frame.get_instance().add_notification(self._notif_icon)

    def __button_release_event_cb(self, icon, event):
        self.emit('clicked')

    def __clicked_cb(self, button):
        if self._notif_icon is not None:
            frame = view.frame.frame.get_instance()
            frame.remove_notification(self._notif_icon)
            self._notif_icon = None

        shell = view.Shell.get_instance()
        shell.join_activity(self._activity_model.get_bundle_id(),
                            self._activity_model.get_id())

    def __destroy_cb(self, button):
        frame = view.frame.frame.get_instance()
        frame.remove_notification(self._notif_icon)
    
class InvitePalette(Palette):
    def __init__(self, activity_model):
        self._activity_model = activity_model

        Palette.__init__(self, '')

        registry = activity.get_registry()
        activity_info = registry.get_activity(activity_model.get_bundle_id())
        if activity_info:
            self.set_primary_text(activity_info.name)
        else:
            self.set_primary_text(activity_model.get_bundle_id())

        menu_item = MenuItem(_('Join'), icon_name='dialog-ok')
        menu_item.connect('activate', self.__join_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Decline'), icon_name='dialog-cancel')
        menu_item.connect('activate', self.__decline_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __join_activate_cb(self, menu_item):
        shell = view.Shell.get_instance()
        shell.join_activity(self._activity_model.get_bundle_id(),
                            self._activity_model.get_id())

    def __decline_activate_cb(self, menu_item):
        invites = shellmodel.get_instance().get_invites()
        for invite in invites:
            if invite.get_activity_id() == self._activity_model.get_id():
                invites.remove_invite(invite)
                return

class ActivitiesTray(HTray):
    def __init__(self):
        HTray.__init__(self)

        self._buttons = {}
        self._invite_to_item = {}

        self._home_model = shellmodel.get_instance().get_home()
        self._home_model.connect('activity-added', self.__activity_added_cb)
        self._home_model.connect('activity-removed', self.__activity_removed_cb)
        self._home_model.connect('pending-activity-changed',
                                 self.__activity_changed_cb)

        self._invites = shellmodel.get_instance().get_invites()
        for invite in self._invites:
            self._add_invite(invite)
        self._invites.connect('invite-added', self.__invite_added_cb)
        self._invites.connect('invite-removed', self.__invite_removed_cb)

    def __activity_added_cb(self, home_model, home_activity):
        logging.debug('__activity_added_cb: %r' % home_activity)
        if self.get_children():
            group = self.get_children()[0]
        else:
            group = None

        button = ActivityButton(home_activity, group)
        self.add_item(button)
        self._buttons[home_activity.get_activity_id()] = button
        button.connect('clicked', self.__activity_clicked_cb, home_activity)
        button.show()

    def __activity_removed_cb(self, home_model, home_activity):
        logging.debug('__activity_removed_cb: %r' % home_activity)
        button = self._buttons[home_activity.get_activity_id()]
        self.remove_item(button)
        del self._buttons[home_activity.get_activity_id()]

    def __activity_changed_cb(self, home_model, home_activity):
        logging.debug('__activity_changed_cb: %r' % home_activity)
        button = self._buttons[home_activity.get_activity_id()]
        button.props.active = True

    def __activity_clicked_cb(self, button, home_activity):
        if button.props.active:
            logging.debug('ActivitiesTray.__activity_clicked_cb')
            home_activity.get_window().activate(gtk.get_current_event_time())

    def __invite_clicked_cb(self, icon, invite):
        self._invites.remove_invite(invite)
    
    def __invite_added_cb(self, invites, invite):
        self._add_invite(invite)

    def __invite_removed_cb(self, invites, invite):
        self._remove_invite(invite)

    def _add_invite(self, invite):
        mesh = shellmodel.get_instance().get_mesh()
        activity_model = mesh.get_activity(invite.get_activity_id())
        if activity_model:
            item = InviteButton(activity_model)
            item.connect('clicked', self.__invite_clicked_cb, invite)
            self.add_item(item)
            item.show()

            self._invite_to_item[invite] = item

    def _remove_invite(self, invite):
        self.remove_item(self._invite_to_item[invite])
        self._invite_to_item[invite].destroy()
        del self._invite_to_item[invite]

