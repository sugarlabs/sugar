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
from sugar import profile

from jarabe.model import shellmodel
from jarabe.view.palettes import JournalPalette, CurrentActivityPalette
from jarabe.view.pulsingicon import PulsingIcon
from jarabe.view.frame.frameinvoker import FrameWidgetInvoker
from jarabe.view.frame.notification import NotificationIcon
import jarabe.view.frame.frame

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

        if home_activity.props.launching:
            self._icon.props.pulsing = True
            self._notify_launching_hid = home_activity.connect( \
                    'notify::launching', self.__notify_launching_cb)
        else:
            self._notify_launching_hid = None
            self._notif_icon = None

    def create_palette(self):
        if self._home_activity.is_journal():
            palette = JournalPalette(self._home_activity)
        else:
            palette = CurrentActivityPalette(self._home_activity)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        self.set_palette(palette)

    def __notify_launching_cb(self, home_activity, pspec):
        if not home_activity.props.launching:
            self._icon.props.pulsing = False
            home_activity.disconnect(self._notify_launching_hid)


class BaseInviteButton(ToolButton):
    def __init__(self, invite):
        ToolButton.__init__(self)
        self._invite = invite
        self._icon = Icon()
        self.connect('clicked', self.__clicked_cb)
        self.connect('destroy', self.__destroy_cb)
        self._notif_icon = NotificationIcon()
        self._notif_icon.connect('button-release-event',
                                 self.__button_release_event_cb)

    def __button_release_event_cb(self, icon, event):
        self.emit('clicked')

    def __clicked_cb(self, button):
        if self._notif_icon is not None:
            frame = jarabe.view.frame.frame.get_instance()
            frame.remove_notification(self._notif_icon)
            self._notif_icon = None
            self._launch()

    def _launch(self):
        """Launch the target of the invite"""
        raise NotImplementedError

    def __destroy_cb(self, button):
        frame = jarabe.view.frame.frame.get_instance()
        frame.remove_notification(self._notif_icon)

class ActivityInviteButton(BaseInviteButton):
    """Invite to shared activity"""
    def __init__(self, invite):
        BaseInviteButton.__init__(self, invite)
        mesh = shellmodel.get_instance().get_mesh()
        activity_model = mesh.get_activity(invite.get_activity_id())
        self._activity_model = activity_model
        self._bundle_id = activity_model.get_bundle_id()

        self._icon.props.xo_color = activity_model.get_color()
        if activity_model.get_icon_name():
            self._icon.props.file = activity_model.get_icon_name()
        else:
            self._icon.props.icon_name = 'image-missing'
        self.set_icon_widget(self._icon)
        self._icon.show()

        palette = ActivityInvitePalette(invite)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        self.set_palette(palette)

        self._notif_icon.props.xo_color = activity_model.get_color()
        if activity_model.get_icon_name():
            icon_name = activity_model.get_icon_name()
            self._notif_icon.props.icon_filename = icon_name
        else:
            self._notif_icon.props.icon_name = 'image-missing'

        palette = ActivityInvitePalette(invite)
        palette.props.invoker = WidgetInvoker(self._notif_icon)
        palette.set_group_id('frame')
        self._notif_icon.palette = palette

        frame = jarabe.view.frame.frame.get_instance()
        frame.add_notification(self._notif_icon,
                               jarabe.view.frame.frame.TOP_LEFT)

    def _launch(self):
        """Join the activity in the invite."""
        shell = Shell.get_instance()
        shell.join_activity(self._activity_model.get_bundle_id(),
                            self._activity_model.get_id())


class PrivateInviteButton(BaseInviteButton):
    """Invite to a private one to one channel"""
    def __init__(self, invite):
        BaseInviteButton.__init__(self, invite)
        self._private_channel = invite.get_private_channel()
        self._bundle_id = invite.get_bundle_id()

        self._icon.props.xo_color = profile.get_color()
        registry = activity.get_registry()
        activity_info = registry.get_activity(self._bundle_id)
        if activity_info:
            self._icon.props.file = activity_info.icon
        else:
            self._icon.props.icon_name = 'image-missing'
        self.set_icon_widget(self._icon)
        self._icon.show()

        palette = PrivateInvitePalette(invite)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        self.set_palette(palette)

        self._notif_icon.props.xo_color = profile.get_color()
        registry = activity.get_registry()
        activity_info = registry.get_activity(self._bundle_id)
        if activity_info:
            self._notif_icon.props.icon_filename = activity_info.icon
        else:
            self._notif_icon.props.icon_name = 'image-missing'

        palette = PrivateInvitePalette(invite)
        palette.props.invoker = WidgetInvoker(self._notif_icon)
        palette.set_group_id('frame')
        self._notif_icon.palette = palette

        frame = jarabe.view.frame.frame.get_instance()
        frame.add_notification(self._notif_icon,
                               jarabe.view.frame.frame.TOP_LEFT)

    def _launch(self):
        """Start the activity with private channel."""
        shell = Shell.get_instance()
        shell.start_activity_with_uri(self._bundle_id,
                                      self._private_channel)


class BaseInvitePalette(Palette):
    """Palette for frame or notification icon for invites."""
    def __init__(self):
        Palette.__init__(self, '')

        menu_item = MenuItem(_('Join'), icon_name='dialog-ok')
        menu_item.connect('activate', self.__join_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Decline'), icon_name='dialog-cancel')
        menu_item.connect('activate', self.__decline_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __join_activate_cb(self, menu_item):
        self._join()

    def __decline_activate_cb(self, menu_item):
        self._decline()

    def _join(self):
        raise NotImplementedError

    def _decline(self):
        raise NotImplementedError


class ActivityInvitePalette(BaseInvitePalette):
    """Palette for shared activity invites."""

    def __init__(self, invite):
        BaseInvitePalette.__init__(self)

        mesh = shellmodel.get_instance().get_mesh()
        activity_model = mesh.get_activity(invite.get_activity_id())
        self._activity_model = activity_model
        self._bundle_id = activity_model.get_bundle_id()

        registry = activity.get_registry()
        activity_info = registry.get_activity(self._bundle_id)
        if activity_info:
            self.set_primary_text(activity_info.name)
        else:
            self.set_primary_text(self._bundle_id)

    def _join(self):
        shell = Shell.get_instance()
        shell.join_activity(self._activity_model.get_bundle_id(),
                            self._activity_model.get_id())

    def _decline(self):
        invites = shellmodel.get_instance().get_invites()
        activity_id = self._activity_model.get_id()
        invites.remove_activity(activity_id)


class PrivateInvitePalette(BaseInvitePalette):
    """Palette for private channel invites."""

    def __init__(self, invite):
        BaseInvitePalette.__init__(self)

        self._private_channel = invite.get_private_channel()
        self._bundle_id = invite.get_bundle_id()

        registry = activity.get_registry()
        activity_info = registry.get_activity(self._bundle_id)
        if activity_info:
            self.set_primary_text(activity_info.name)
        else:
            self.set_primary_text(self._bundle_id)

    def _join(self):
        shell = Shell.get_instance()
        shell.start_activity_with_uri(self._bundle_id,
                                      self._private_channel)
        invites = shellmodel.get_instance().get_invites()
        invites.remove_private_channel(self._private_channel)

    def _decline(self):
        invites = shellmodel.get_instance().get_invites()
        invites.remove_private_channel(self._private_channel)


class ActivitiesTray(HTray):
    def __init__(self):
        HTray.__init__(self)

        self._buttons = {}
        self._invite_to_item = {}
        self._freeze_button_clicks = False

        self._home_model = shellmodel.get_instance().get_home()
        self._home_model.connect('activity-added', self.__activity_added_cb)
        self._home_model.connect('activity-removed', self.__activity_removed_cb)
        self._home_model.connect('active-activity-changed',
                                 self.__activity_changed_cb)
        self._home_model.connect('tabbing-activity-changed',
                                 self.__tabbing_activity_changed_cb)

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

    def _activate_activity(self, home_activity):
        button = self._buttons[home_activity.get_activity_id()]
        self._freeze_button_clicks = True
        button.props.active = True
        self._freeze_button_clicks = False

        self.scroll_to_item(button)
        # Redraw immediately.
        # The widget may not be realized yet, and then there is no window.
        if self.window:
            self.window.process_updates(True)

    def __activity_changed_cb(self, home_model, home_activity):
        logging.debug('__activity_changed_cb: %r' % home_activity)

        # Only select the new activity, if there is no tabbing activity.
        if home_model.get_tabbing_activity() is None:
            self._activate_activity(home_activity)

    def __tabbing_activity_changed_cb(self, home_model, home_activity):
        logging.debug('__tabbing_activity_changed_cb: %r' % home_activity)
        # If the tabbing_activity is set to None just do nothing.
        # The active activity will be updated a bit later (and it will
        # be set to the activity that is currently selected).
        if home_activity is None:
            return

        self._activate_activity(home_activity)

    def __activity_clicked_cb(self, button, home_activity):
        if not self._freeze_button_clicks and button.props.active:
            logging.debug('ActivitiesTray.__activity_clicked_cb')
            window = home_activity.get_window()
            if window:
                window.activate(gtk.get_current_event_time())

    def __invite_clicked_cb(self, icon, invite):
        if hasattr(invite, 'get_activity_id'):
            self._invites.remove_invite(invite)
        else:
            self._invites.remove_private_invite(invite)
    
    def __invite_added_cb(self, invites, invite):
        self._add_invite(invite)

    def __invite_removed_cb(self, invites, invite):
        self._remove_invite(invite)

    def _add_invite(self, invite):
        """Add an invite (SugarInvite or PrivateInvite)"""
        item = None
        if hasattr(invite, 'get_activity_id'):
            mesh = shellmodel.get_instance().get_mesh()
            activity_model = mesh.get_activity(invite.get_activity_id())
            if activity_model is not None:
                item = ActivityInviteButton(invite)
        else:
            item = PrivateInviteButton(invite)
        if item is not None:
            item.connect('clicked', self.__invite_clicked_cb, invite)
            self.add_item(item)
            item.show()
            self._invite_to_item[invite] = item

    def _remove_invite(self, invite):
        self.remove_item(self._invite_to_item[invite])
        self._invite_to_item[invite].destroy()
        del self._invite_to_item[invite]

