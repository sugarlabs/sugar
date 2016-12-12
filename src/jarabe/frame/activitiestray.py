# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2008 One Laptop Per Child
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

import logging
from gettext import gettext as _
import tempfile
import os

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.tray import HTray
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.icon import Icon, get_icon_file_name
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator
from sugar3.datastore import datastore
from sugar3 import mime
from sugar3 import env
from sugar3 import profile

from jarabe.model import shell
from jarabe.model import invites
from jarabe.model import bundleregistry
from jarabe.model import filetransfer
from jarabe.model import notifications
from jarabe.view.palettes import JournalPalette, CurrentActivityPalette
from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.frame.notification import NotificationIcon
from jarabe.frame.notification import NotificationButton
from jarabe.frame.notification import NotificationPulsingIcon
import jarabe.frame


class ActivityButton(RadioToolButton):

    def __init__(self, home_activity, group):
        RadioToolButton.__init__(self, group=group)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.cache_palette = False

        self._home_activity = home_activity
        self._notify_launch_hid = None

        self._icon = NotificationPulsingIcon()
        self._icon.props.base_color = home_activity.get_icon_color()
        self._icon.props.pulse_color = \
            XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                               style.COLOR_TOOLBAR_GREY.get_svg()))
        if home_activity.get_icon_path():
            self._icon.props.file = home_activity.get_icon_path()
        else:
            # Let's see if the X11 window can give us an icon.
            window = home_activity.get_window()

            if not window.get_icon_is_fallback():
                pixbuf = window.get_icon()
                self._icon.pixbuf = pixbuf
            else:
                self._icon.props.icon_name = 'image-missing'

        self.set_icon_widget(self._icon)
        self._icon.show()

        if home_activity.props.launch_status == shell.Activity.LAUNCHING:
            self._icon.props.pulsing = True
            self._notify_launch_hid = home_activity.connect(
                'notify::launch-status', self.__notify_launch_status_cb)
        elif home_activity.props.launch_status == shell.Activity.LAUNCH_FAILED:
            self._on_failed_launch()

    def create_palette(self):
        if self._home_activity.is_journal():
            palette = JournalPalette(self._home_activity)
        else:
            palette = CurrentActivityPalette(self._home_activity)
            palette.connect('done', self.__palette_item_selected_cb)
        palette.set_group_id('frame')
        self.set_palette(palette)

    def __palette_item_selected_cb(self, widget):
        frame = jarabe.frame.get_view()
        frame.hide()

    def _on_failed_launch(self):
        # TODO http://bugs.sugarlabs.org/ticket/2007
        pass

    def __notify_launch_status_cb(self, home_activity, pspec):
        home_activity.disconnect(self._notify_launch_hid)
        self._notify_launch_hid = None
        if home_activity.props.launch_status == shell.Activity.LAUNCH_FAILED:
            self._on_failed_launch()
        else:
            self._icon.props.pulsing = False

    def show_badge(self):
        self._icon.show_badge()

    def hide_badge(self):
        self._icon.hide_badge()


class InviteButton(ToolButton):
    """Invite to shared activity"""

    __gsignals__ = {
        'remove-invite': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, invite):
        ToolButton.__init__(self)

        self._invite = invite

        self.connect('clicked', self.__clicked_cb)
        self.connect('destroy', self.__destroy_cb)

        bundle_registry = bundleregistry.get_registry()
        bundle = bundle_registry.get_bundle(invite.get_bundle_id())

        self._icon = Icon()
        self._icon.props.xo_color = invite.get_color()
        if bundle is not None:
            self._icon.props.file = bundle.get_icon()
        else:
            self._icon.props.icon_name = 'image-missing'
        self.set_icon_widget(self._icon)
        self._icon.show()

        palette = InvitePalette(invite)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        palette.connect('remove-invite', self.__remove_invite_cb)
        self.set_palette(palette)

        self._notif_icon = NotificationIcon()
        self._notif_icon.connect('button-release-event',
                                 self.__button_release_event_cb)

        self._notif_icon.props.xo_color = invite.get_color()
        if bundle is not None:
            self._notif_icon.props.icon_filename = bundle.get_icon()
        else:
            self._notif_icon.props.icon_name = 'image-missing'

        frame = jarabe.frame.get_view()
        frame.add_notification(self._notif_icon, Gtk.CornerType.TOP_LEFT)

    def __button_release_event_cb(self, icon, event):
        if self._notif_icon is not None:
            frame = jarabe.frame.get_view()
            frame.remove_notification(self._notif_icon)
            self._notif_icon = None
            self._invite.join()
            self.emit('remove-invite')

    def __clicked_cb(self, button):
        self.palette.popup(immediate=True)

    def __remove_invite_cb(self, palette):
        self.emit('remove-invite')

    def __destroy_cb(self, button):
        if self._notif_icon is not None:
            frame = jarabe.frame.get_view()
            frame.remove_notification(self._notif_icon)
            self._notif_icon = None


class InvitePalette(Palette):
    """Palette for frame or notification icon for invites."""

    __gsignals__ = {
        'remove-invite': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, invite):
        Palette.__init__(self, '')

        self._invite = invite

        self.menu_box = PaletteMenuBox()
        self.set_content(self.menu_box)
        self.menu_box.show()

        menu_item = PaletteMenuItem(_('Join'), icon_name='dialog-ok')
        menu_item.connect('activate', self.__join_activate_cb)
        self.menu_box.append_item(menu_item)
        menu_item.show()

        menu_item = PaletteMenuItem(_('Decline'), icon_name='dialog-cancel')
        menu_item.connect('activate', self.__decline_activate_cb)
        self.menu_box.append_item(menu_item)
        menu_item.show()

        bundle_id = invite.get_bundle_id()

        registry = bundleregistry.get_registry()
        self._bundle = registry.get_bundle(bundle_id)
        if self._bundle:
            activity_name = self._bundle.get_name()
        else:
            activity_name = bundle_id
        self.set_primary_text(activity_name)

        title = self._invite.get_activity_title()
        if title is not None:
            self.set_secondary_text(title)

    def __join_activate_cb(self, menu_item):
        self._invite.join()
        self.emit('remove-invite')

    def __decline_activate_cb(self, menu_item):
        self.emit('remove-invite')


class ActivitiesTray(HTray):

    def __init__(self):
        HTray.__init__(self)

        self._buttons = {}
        self._buttons_by_name = {}
        self._invite_to_item = {}
        self._freeze_button_clicks = False

        self._home_model = shell.get_model()
        self._home_model.connect('activity-added', self.__activity_added_cb)
        self._home_model.connect('activity-removed',
                                 self.__activity_removed_cb)
        self._home_model.connect('active-activity-changed',
                                 self.__activity_changed_cb)
        self._home_model.connect('tabbing-activity-changed',
                                 self.__tabbing_activity_changed_cb)

        self._invites = invites.get_instance()
        for invite in self._invites:
            self._add_invite(invite)
        self._invites.connect('invite-added', self.__invite_added_cb)
        self._invites.connect('invite-removed', self.__invite_removed_cb)

        filetransfer.new_file_transfer.connect(self.__new_file_transfer_cb)

        service = notifications.get_service()
        service.notification_received.connect(self.__notification_received_cb)
        service.buffer_cleared.connect(self.__buffer_cleared_cb)

    def __notification_received_cb(self, **kwargs):
        logging.debug('ActivitiesTray.__notification_received_cb')

        name = kwargs.get('app_name')

        button = self._buttons_by_name.get(name, None)
        if button is None:
            hints = kwargs.get('hints')
            icon = NotificationPulsingIcon(
                hints.get('x-sugar-icon-file-name', ''),
                hints.get('x-sugar-icon-name', ''),
                hints.get('x-sugar-icon-colors', ''))

            button = NotificationButton(name)
            button.set_icon(icon)
            button.show()

            self.add_item(button)
            self._buttons_by_name[name] = button

        if hasattr(button, 'show_badge'):
            button.show_badge()

    def __buffer_cleared_cb(self, **kwargs):
        logging.debug('ActivitiesTray.__buffer_cleared_cb')

        name = kwargs.get('app_name', None)

        button = self._buttons_by_name.get(name, None)
        if isinstance(button, NotificationButton):
            self.remove_item(button)
            del self._buttons_by_name[name]
            return

        if hasattr(button, 'hide_badge'):
            button.hide_badge()

    def __activity_added_cb(self, home_model, home_activity):
        logging.debug('__activity_added_cb: %r', home_activity)
        if self.get_children():
            group = self.get_children()[0]
        else:
            group = None

        button = ActivityButton(home_activity, group)
        self.add_item(button)
        self._buttons[home_activity] = button
        self._buttons_by_name[home_activity.get_activity_id()] = button
        button.connect('clicked', self.__activity_clicked_cb, home_activity)
        button.show()

    def __activity_removed_cb(self, home_model, home_activity):
        logging.debug('__activity_removed_cb: %r', home_activity)
        button = self._buttons[home_activity]
        self.remove_item(button)
        del self._buttons[home_activity]
        del self._buttons_by_name[home_activity.get_activity_id()]

    def _activate_activity(self, home_activity):
        button = self._buttons[home_activity]
        self._freeze_button_clicks = True
        button.props.active = True
        self._freeze_button_clicks = False

        self.scroll_to_item(button)
        # Redraw immediately.
        # The widget may not be realized yet, and then there is no window.
        x11_window = self.get_window()
        if x11_window:
            x11_window.process_updates(True)

    def __activity_changed_cb(self, home_model, home_activity):
        logging.debug('__activity_changed_cb: %r', home_activity)

        if home_activity is None:
            return

        # Only select the new activity, if there is no tabbing activity.
        if home_model.get_tabbing_activity() is None:
            self._activate_activity(home_activity)

    def __tabbing_activity_changed_cb(self, home_model, home_activity):
        logging.debug('__tabbing_activity_changed_cb: %r', home_activity)
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
                window.activate(Gtk.get_current_event_time())
                frame = jarabe.frame.get_view()
                frame.hide()

    def __remove_invite_cb(self, icon, invite):
        self._invites.remove_invite(invite)

    def __invite_added_cb(self, invites_model, invite):
        self._add_invite(invite)

    def __invite_removed_cb(self, invites_model, invite):
        self._remove_invite(invite)

    def _add_invite(self, invite):
        """Add an invite"""
        item = InviteButton(invite)
        item.connect('remove-invite', self.__remove_invite_cb, invite)
        self.add_item(item)
        item.show()
        self._invite_to_item[invite] = item

    def _remove_invite(self, invite):
        self.remove_item(self._invite_to_item[invite])
        self._invite_to_item[invite].destroy()
        del self._invite_to_item[invite]

    def __new_file_transfer_cb(self, **kwargs):
        file_transfer = kwargs['file_transfer']
        logging.debug('__new_file_transfer_cb %r', file_transfer)

        if isinstance(file_transfer, filetransfer.IncomingFileTransfer):
            button = IncomingTransferButton(file_transfer)
        elif isinstance(file_transfer, filetransfer.OutgoingFileTransfer):
            button = OutgoingTransferButton(file_transfer)

        self.add_item(button)
        button.show()


class BaseTransferButton(ToolButton):
    """Button with a notification attached
    """

    def __init__(self, file_transfer):
        ToolButton.__init__(self)

        self.file_transfer = file_transfer
        file_transfer.connect('notify::state', self.__notify_state_cb)

        icon = Icon()
        self.props.icon_widget = icon
        icon.show()

        self.notif_icon = NotificationIcon()
        self.notif_icon.connect('button-release-event',
                                self.__button_release_event_cb)

        self.connect('clicked', self.__button_clicked_cb)

    def __button_release_event_cb(self, icon, event):
        if self.notif_icon is not None:
            frame = jarabe.frame.get_view()
            frame.remove_notification(self.notif_icon)
            self.notif_icon = None

    def __button_clicked_cb(self, button):
        self.palette.popup(immediate=True)

    def remove(self):
        frame = jarabe.frame.get_view()
        frame.remove_notification(self.notif_icon)
        self.props.parent.remove(self)

    def __notify_state_cb(self, file_transfer, pspec):
        logging.debug('_update state: %r %r', file_transfer.props.state,
                      file_transfer.reason_last_change)
        if file_transfer.props.state == filetransfer.FT_STATE_CANCELLED:
            if file_transfer.reason_last_change == \
               filetransfer.FT_REASON_LOCAL_STOPPED:
                self.remove()


class IncomingTransferButton(BaseTransferButton):
    """UI element representing an ongoing incoming file transfer
    """

    def __init__(self, file_transfer):
        BaseTransferButton.__init__(self, file_transfer)

        self._ds_object = datastore.create()

        file_transfer.connect('notify::state', self.__notify_state_cb)
        file_transfer.connect('notify::transferred-bytes',
                              self.__notify_transferred_bytes_cb)

        icons = Gio.content_type_get_icon(file_transfer.mime_type).props.names
        icons.append('application-octet-stream')
        for icon_name in icons:
            icon_name = 'transfer-from-%s' % icon_name
            file_name = get_icon_file_name(icon_name)
            if file_name is not None:
                self.props.icon_widget.props.icon_name = icon_name
                self.notif_icon.props.icon_name = icon_name
                break

        icon_color = file_transfer.buddy.props.color
        self.props.icon_widget.props.xo_color = icon_color
        self.notif_icon.props.xo_color = icon_color

        frame = jarabe.frame.get_view()
        frame.add_notification(self.notif_icon,
                               Gtk.CornerType.TOP_LEFT)

    def create_palette(self):
        palette = IncomingTransferPalette(self.file_transfer)
        palette.connect('dismiss-clicked', self.__dismiss_clicked_cb)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        return palette

    def __notify_state_cb(self, file_transfer, pspec):
        if file_transfer.props.state == filetransfer.FT_STATE_OPEN:
            logging.debug('__notify_state_cb OPEN')
            self._ds_object.metadata['title'] = file_transfer.title
            self._ds_object.metadata['description'] = file_transfer.description
            self._ds_object.metadata['progress'] = '0'
            self._ds_object.metadata['keep'] = '0'
            self._ds_object.metadata['buddies'] = ''
            self._ds_object.metadata['preview'] = ''
            self._ds_object.metadata['icon-color'] = \
                file_transfer.buddy.props.color.to_string()
            self._ds_object.metadata['mime_type'] = file_transfer.mime_type
        elif file_transfer.props.state == filetransfer.FT_STATE_COMPLETED:
            logging.debug('__notify_state_cb COMPLETED')
            self._ds_object.metadata['progress'] = '100'
            self._ds_object.file_path = file_transfer.destination_path
            datastore.write(self._ds_object, transfer_ownership=True,
                            reply_handler=self.__reply_handler_cb,
                            error_handler=self.__error_handler_cb)
        elif file_transfer.props.state == filetransfer.FT_STATE_CANCELLED:
            logging.debug('__notify_state_cb CANCELLED')
            object_id = self._ds_object.object_id
            if object_id is not None:
                self._ds_object.destroy()
                datastore.delete(object_id)
                self._ds_object = None

    def __notify_transferred_bytes_cb(self, file_transfer, pspec):
        progress = file_transfer.props.transferred_bytes /      \
            file_transfer.file_size
        self._ds_object.metadata['progress'] = str(progress * 100)
        datastore.write(self._ds_object, update_mtime=False)

    def __reply_handler_cb(self):
        logging.debug('__reply_handler_cb %r', self._ds_object.object_id)

    def __error_handler_cb(self, error):
        logging.debug('__error_handler_cb %r %s', self._ds_object.object_id,
                      error)

    def __dismiss_clicked_cb(self, palette):
        self.remove()


class OutgoingTransferButton(BaseTransferButton):
    """UI element representing an ongoing outgoing file transfer
    """

    def __init__(self, file_transfer):
        BaseTransferButton.__init__(self, file_transfer)

        icons = Gio.content_type_get_icon(file_transfer.mime_type).props.names
        icons.append('application-octet-stream')
        for icon_name in icons:
            icon_name = 'transfer-to-%s' % icon_name
            file_name = get_icon_file_name(icon_name)
            if file_name is not None:
                self.props.icon_widget.props.icon_name = icon_name
                self.notif_icon.props.icon_name = icon_name
                break

        icon_color = profile.get_color()
        self.props.icon_widget.props.xo_color = icon_color
        self.notif_icon.props.xo_color = icon_color

        frame = jarabe.frame.get_view()
        frame.add_notification(self.notif_icon,
                               Gtk.CornerType.TOP_LEFT)

    def create_palette(self):
        palette = OutgoingTransferPalette(self.file_transfer)
        palette.connect('dismiss-clicked', self.__dismiss_clicked_cb)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        return palette

    def __dismiss_clicked_cb(self, palette):
        self.remove()


class BaseTransferPalette(Palette):
    """Base palette class for frame or notification icon for file transfers
    """
    __gtype_name__ = 'SugarBaseTransferPalette'

    __gsignals__ = {
        'dismiss-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, file_transfer):
        Palette.__init__(self, file_transfer.title)

        self.file_transfer = file_transfer

        self.progress_bar = None
        self.progress_label = None
        self._notify_transferred_bytes_handler = None

        self.connect('popup', self.__popup_cb)
        self.connect('popdown', self.__popdown_cb)

    def __popup_cb(self, palette):
        self.update_progress()
        self._notify_transferred_bytes_handler = \
            self.file_transfer.connect('notify::transferred_bytes',
                                       self.__notify_transferred_bytes_cb)

    def __popdown_cb(self, palette):
        if self._notify_transferred_bytes_handler is not None:
            self.file_transfer.disconnect(
                self._notify_transferred_bytes_handler)
            self._notify_transferred_bytes_handler = None

    def __notify_transferred_bytes_cb(self, file_transfer, pspec):
        self.update_progress()

    def _format_size(self, size):
        if size < 1024:
            return _('%d B') % size
        elif size < 1048576:
            return _('%d KiB') % (size / 1024)
        else:
            return _('%d MiB') % (size / 1048576)

    def update_progress(self):
        logging.debug('update_progress: %r',
                      self.file_transfer.props.transferred_bytes)

        if self.progress_bar is None:
            return

        self.progress_bar.props.fraction = \
            self.file_transfer.props.transferred_bytes / \
            float(self.file_transfer.file_size)
        logging.debug('update_progress: %r', self.progress_bar.props.fraction)

        transferred = self._format_size(
            self.file_transfer.props.transferred_bytes)
        total = self._format_size(self.file_transfer.file_size)
        # TRANS: file transfer, bytes transferred, e.g. 128 of 1024
        self.progress_label.props.label = _('%s of %s') % (transferred, total)


class IncomingTransferPalette(BaseTransferPalette):
    """Palette for frame or notification icon for incoming file transfers
    """
    __gtype_name__ = 'SugarIncomingTransferPalette'

    def __init__(self, file_transfer):
        BaseTransferPalette.__init__(self, file_transfer)

        self.file_transfer.connect('notify::state', self.__notify_state_cb)

        nick = str(self.file_transfer.buddy.props.nick)
        self.props.secondary_text = _('Transfer from %s') % (nick,)

        self._update()

    def __notify_state_cb(self, file_transfer, pspec):
        self._update()

    def _update(self):
        box = PaletteMenuBox()
        self.set_content(box)
        box.show()

        logging.debug('_update state: %r', self.file_transfer.props.state)
        if self.file_transfer.props.state == filetransfer.FT_STATE_PENDING:
            menu_item = PaletteMenuItem(_('Accept'))
            icon = Icon(icon_name='dialog-ok',
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            icon.show()
            menu_item.connect('activate', self.__accept_activate_cb)
            box.append_item(menu_item)
            menu_item.show()

            menu_item = PaletteMenuItem(_('Decline'))
            icon = Icon(icon_name='dialog-cancel',
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            icon.show()
            menu_item.connect('activate', self.__decline_activate_cb)
            box.append_item(menu_item)
            menu_item.show()

            separator = PaletteMenuItemSeparator()
            box.append_item(separator)
            separator.show()

            inner_box = Gtk.VBox()
            inner_box.set_spacing(style.DEFAULT_PADDING)
            box.append_item(inner_box, vertical_padding=0)
            inner_box.show()

            if self.file_transfer.description:
                text = self.file_transfer.description.replace('\n', ' ')
                label = Gtk.Label(label=text)
                label.set_max_width_chars(style.MENU_WIDTH_CHARS)
                label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
                inner_box.add(label)
                label.show()

            mime_type = self.file_transfer.mime_type
            type_description = mime.get_mime_description(mime_type)

            size = self._format_size(self.file_transfer.file_size)
            label = Gtk.Label(label='%s (%s)' % (size, type_description))
            inner_box.add(label)
            label.show()

        elif self.file_transfer.props.state in \
                [filetransfer.FT_STATE_ACCEPTED, filetransfer.FT_STATE_OPEN]:
            menu_item = PaletteMenuItem(_('Cancel'))
            icon = Icon(icon_name='dialog-cancel',
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            icon.show()
            menu_item.connect('activate', self.__cancel_activate_cb)
            box.append_item(menu_item)
            menu_item.show()

            separator = PaletteMenuItemSeparator()
            box.append_item(separator)
            separator.show()

            inner_box = Gtk.VBox()
            inner_box.set_spacing(style.DEFAULT_PADDING)
            box.append_item(inner_box, vertical_padding=0)
            inner_box.show()

            self.progress_bar = Gtk.ProgressBar()
            inner_box.add(self.progress_bar)
            self.progress_bar.show()

            self.progress_label = Gtk.Label(label='')
            inner_box.add(self.progress_label)
            self.progress_label.show()

            self.update_progress()

        elif self.file_transfer.props.state == filetransfer.FT_STATE_COMPLETED:
            menu_item = PaletteMenuItem(_('Dismiss'))
            icon = Icon(icon_name='dialog-cancel',
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            icon.show()
            menu_item.connect('activate', self.__dismiss_activate_cb)
            box.append_item(menu_item)
            menu_item.show()

            self.update_progress()

        elif self.file_transfer.props.state == filetransfer.FT_STATE_CANCELLED:
            if self.file_transfer.reason_last_change == \
                    filetransfer.FT_REASON_REMOTE_STOPPED:
                menu_item = PaletteMenuItem(_('Dismiss'))
                icon = Icon(icon_name='dialog-cancel',
                            pixel_size=style.SMALL_ICON_SIZE)
                menu_item.set_image(icon)
                icon.show()
                menu_item.connect('activate', self.__dismiss_activate_cb)
                box.append_item(menu_item)
                menu_item.show()

                inner_box = Gtk.VBox()
                inner_box.set_spacing(style.DEFAULT_PADDING)
                box.append_item(inner_box, vertical_padding=0)
                inner_box.show()

                text = _('The other participant canceled the file transfer')
                label = Gtk.Label(label=text)
                inner_box.add(label)
                label.show()

    def __accept_activate_cb(self, menu_item):
        # TODO: figure out the best place to get rid of that temp file
        extension = mime.get_primary_extension(self.file_transfer.mime_type)
        if extension is None:
            extension = '.bin'
        fd, file_path = tempfile.mkstemp(suffix=extension,
                                         prefix=self._sanitize(
                                             self.file_transfer.title),
                                         dir=os.path.join(
                                             env.get_profile_path(), 'data'))
        os.close(fd)
        os.unlink(file_path)

        self.file_transfer.accept(file_path)

    def _sanitize(self, file_name):
        file_name = file_name.replace('/', '_')
        file_name = file_name.replace('.', '_')
        file_name = file_name.replace('?', '_')
        return file_name

    def __decline_activate_cb(self, menu_item):
        self.file_transfer.cancel()

    def __cancel_activate_cb(self, menu_item):
        self.file_transfer.cancel()

    def __dismiss_activate_cb(self, menu_item):
        self.emit('dismiss-clicked')


class OutgoingTransferPalette(BaseTransferPalette):
    """Palette for frame or notification icon for outgoing file transfers
    """
    __gtype_name__ = 'SugarOutgoingTransferPalette'

    def __init__(self, file_transfer):
        BaseTransferPalette.__init__(self, file_transfer)

        self.progress_bar = None
        self.progress_label = None

        self.file_transfer.connect('notify::state', self.__notify_state_cb)

        nick = str(file_transfer.buddy.props.nick)
        self.props.secondary_text = _('Transfer to %s') % (nick,)

        self._update()

    def __notify_state_cb(self, file_transfer, pspec):
        self._update()

    def _update(self):
        new_state = self.file_transfer.props.state
        logging.debug('_update state: %r', new_state)

        box = PaletteMenuBox()
        self.set_content(box)
        box.show()
        if new_state == filetransfer.FT_STATE_PENDING:
            menu_item = PaletteMenuItem(_('Cancel'))
            icon = Icon(icon_name='dialog-cancel',
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            icon.show()
            menu_item.connect('activate', self.__cancel_activate_cb)
            box.append_item(menu_item)
            menu_item.show()

            separator = PaletteMenuItemSeparator()
            box.append_item(separator)
            separator.show()

            inner_box = Gtk.VBox()
            inner_box.set_spacing(style.DEFAULT_PADDING)
            box.append_item(inner_box, vertical_padding=0)
            inner_box.show()

            if self.file_transfer.description:
                label = Gtk.Label(label=self.file_transfer.description)
                inner_box.add(label)
                label.show()

            mime_type = self.file_transfer.mime_type
            type_description = mime.get_mime_description(mime_type)

            size = self._format_size(self.file_transfer.file_size)
            label = Gtk.Label(label='%s (%s)' % (size, type_description))
            inner_box.add(label)
            label.show()

        elif new_state in [filetransfer.FT_STATE_ACCEPTED,
                           filetransfer.FT_STATE_OPEN]:
            menu_item = PaletteMenuItem(_('Cancel'))
            icon = Icon(icon_name='dialog-cancel',
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            icon.show()
            menu_item.connect('activate', self.__cancel_activate_cb)
            box.append_item(menu_item)
            menu_item.show()

            separator = PaletteMenuItemSeparator()
            box.append_item(separator)
            separator.show()

            inner_box = Gtk.VBox()
            inner_box.set_spacing(style.DEFAULT_PADDING)
            box.append_item(inner_box, vertical_padding=0)
            inner_box.show()

            self.progress_bar = Gtk.ProgressBar()
            inner_box.add(self.progress_bar)
            self.progress_bar.show()

            self.progress_label = Gtk.Label(label='')
            inner_box.add(self.progress_label)
            self.progress_label.show()

            self.update_progress()

        elif new_state in [filetransfer.FT_STATE_COMPLETED,
                           filetransfer.FT_STATE_CANCELLED]:
            menu_item = PaletteMenuItem(_('Dismiss'))
            icon = Icon(icon_name='dialog-cancel',
                        pixel_size=style.SMALL_ICON_SIZE)
            menu_item.set_image(icon)
            icon.show()
            menu_item.connect('activate', self.__dismiss_activate_cb)
            box.append_item(menu_item)
            menu_item.show()

            self.update_progress()

    def __cancel_activate_cb(self, menu_item):
        self.file_transfer.cancel()

    def __dismiss_activate_cb(self, menu_item):
        self.emit('dismiss-clicked')
