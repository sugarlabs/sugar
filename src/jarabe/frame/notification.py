# Copyright (C) 2008 One Laptop Per Child
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
import textwrap
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Graphene

from sugar4 import profile
from sugar4.graphics import style
from sugar4.graphics.xocolor import XoColor
from sugar4.graphics.icon import Icon
from sugar4.graphics.icon import get_surface
from sugar4.graphics.palette import Palette
from sugar4.graphics.palettemenu import PaletteMenuItem
from sugar4.graphics.palettemenu import PaletteMenuItemSeparator
from sugar4.graphics.toolbutton import ToolButton

from jarabe.model import notifications
from jarabe.view.pulsingicon import PulsingIcon
from jarabe.frame.frameinvoker import FrameWidgetInvoker


class NotificationBox(Gtk.Box):

    LINES = 3
    MAX_ENTRIES = 3
    ELLIPSIS_AND_BREAKS = 6

    def __init__(self, name):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._name = name

        self._notifications_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_child(self._notifications_box)
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)

        separator = PaletteMenuItemSeparator()

        clear_item = PaletteMenuItem(_('Clear notifications'), 'dialog-cancel')
        clear_item.connect('activate', self.__clear_cb)

        self.append(self._scrolled_window)
        self.append(separator)
        self.append(clear_item)

        self._service = notifications.get_service()
        entries = self._service.retrieve_by_name(self._name)

        if entries:
            for entry in entries:
                self._add(entry['summary'], entry['body'])
        else:
            self.set_visible(False)

        self._notify_handler = self._service.notification_received.connect(
            self.__notification_received_cb)

    def _get_entries(self):
        entries = []
        child = self._notifications_box.get_first_child()
        while child:
            entries.append(child)
            child = child.get_next_sibling()
        return entries

    def _update_scrolled_size(self):
        entries = self._get_entries()

        height = 0
        for entry in entries[:self.MAX_ENTRIES]:
            _min, nat_height, _min_b, _nat_b = entry.measure(
                Gtk.Orientation.VERTICAL, -1)
            height += nat_height

        self._scrolled_window.set_size_request(-1, height)

    def _add(self, summary, body):
        icon = Icon()
        icon.props.icon_name = 'emblem-notification'
        icon.props.pixel_size = style.SMALL_ICON_SIZE

        icon.props.xo_color = \
            XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                               style.COLOR_BLACK.get_svg()))

        summary_label = Gtk.Label()
        summary_label.set_max_width_chars(style.MENU_WIDTH_CHARS)
        summary_label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        summary_label.set_xalign(0.0)
        summary_label.set_yalign(0.5)
        summary_label.set_markup('<b>%s</b>' % summary)

        body_label = Gtk.Label()
        body_label.set_xalign(0.0)
        body_label.set_yalign(0.5)

        if hasattr(body_label, 'set_lines'):
            body_label.set_max_width_chars(style.MENU_WIDTH_CHARS)
            body_label.set_wrap(True)
            body_label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
            body_label.set_lines(self.LINES)
            body_label.set_justify(Gtk.Justification.FILL)
        else:
            # FIXME: fallback for Gtk < 3.10
            body_width = self.LINES * style.MENU_WIDTH_CHARS
            body_width -= self.ELLIPSIS_AND_BREAKS
            body = body.replace('\n', ' ')
            if len(body) > body_width:
                body = ' '.join(body[:body_width].split(' ')[:-1]) + '...'
            body = textwrap.fill(body, width=style.MENU_WIDTH_CHARS)

        body_label.set_text(body)

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        grid.set_row_spacing(0)
        grid.set_margin_top(style.DEFAULT_SPACING)
        grid.set_margin_bottom(style.DEFAULT_SPACING)
        grid.set_margin_start(style.DEFAULT_SPACING)
        grid.set_margin_end(style.DEFAULT_SPACING)
        grid.attach(icon, 0, 0, 1, 2)
        grid.attach(summary_label, 1, 0, 1, 1)
        grid.attach(body_label, 1, 1, 1, 1)

        self._notifications_box.append(grid)
        self._update_scrolled_size()

    def __clear_cb(self, clear_item):
        logging.debug('NotificationBox.__clear_cb')
        child = self._notifications_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            if child.get_parent() == self._notifications_box:
                child.unparent()
            child = next_child
        self._service.clear_by_name(self._name)
        self.set_visible(False)

    def __notification_received_cb(self, **kwargs):
        logging.debug('NotificationBox.__notification_received_cb')
        if kwargs.get('app_name', '') == self._name:
            self._add(kwargs.get('summary', ''), kwargs.get('body', ''))

    def do_unroot(self):
        logging.debug('NotificationBox.do_unroot')
        service = notifications.get_service()
        if hasattr(self, '_notify_handler') and self._notify_handler:
            service.notification_received.disconnect(self._notify_handler)
            self._notify_handler = 0


class NotificationButton(ToolButton):

    def __init__(self, name):
        ToolButton.__init__(self)
        self._name = name
        self._icon = None
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.cache_palette = False
        self.connect('clicked', self.__clicked_cb)

    def remove_notification(self, icon):
        # no-op: notifications are managed by the frame view
        logging.debug('NotificationButton.remove_notification called')

    def set_icon(self, icon):
        self._icon = icon
        self.set_icon_widget(self._icon)

    def show_badge(self):
        if self._icon:
            self._icon.show_badge()

    def hide_badge(self):
        if self._icon:
            self._icon.hide_badge()

    def create_palette(self):
        notification_box = NotificationBox(self._name)
        palette = Palette(self._name)
        palette.set_group_id('frame')
        palette.set_content(notification_box)
        self.set_palette(palette)

    def __clicked_cb(self, button):
        self.create_palette()
        self.palette.popup(immediate=True)


class NotificationPulsingIcon(PulsingIcon):

    def __init__(self, filename=None, name=None, colors=None):
        PulsingIcon.__init__(self, pixel_size=style.STANDARD_ICON_SIZE)
        self._badge = None

        if filename:
            self.props.file = filename
        elif name:
            self.props.icon_name = name
        else:
            self.props.icon_name = 'application-octet-stream'

        if not colors:
            colors = profile.get_color()
        self.props.base_color = colors
        self.props.pulse_color = \
            XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                               style.COLOR_TOOLBAR_GREY.get_svg()))

    def show_badge(self):
        self._badge = get_surface(icon_name='emblem-notification',
                                  stroke_color=style.COLOR_WHITE.get_svg(),
                                  fill_color=style.COLOR_BLACK.get_svg(),
                                  width=self.get_badge_size(),
                                  height=self.get_badge_size())

    def hide_badge(self):
        self._badge = None

    def do_snapshot(self, snapshot):
        PulsingIcon.do_snapshot(self, snapshot)
        if self._badge:
            width = self.get_width()
            height = self.get_height()

            offset = int(self.props.pixel_size / 2) - self.get_badge_size()
            x = int(width / 2) + offset
            y = int(height / 2) + offset

            badge_size = self.get_badge_size()
            rect = Graphene.Rect()
            rect.init(x, y, badge_size, badge_size)
            cr = snapshot.append_cairo(rect)
            cr.set_source_surface(self._badge, 0, 0)
            cr.paint()


class NotificationIcon(Gtk.Box):
    __gtype_name__ = 'SugarNotificationIcon'

    __gproperties__ = {
        'xo-color': (object, None, None, GObject.ParamFlags.READWRITE),
        'icon-name': (str, None, None, None, GObject.ParamFlags.READWRITE),
        'icon-filename': (str, None, None, None, GObject.ParamFlags.READWRITE),
    }

    _PULSE_TIMEOUT = 3

    def __init__(self, **kwargs):
        self._icon = NotificationPulsingIcon()
        self._icon.props.pixel_size = style.STANDARD_ICON_SIZE

        super().__init__(**kwargs)

        self._icon.props.pulse_color = \
            XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                               style.COLOR_TRANSPARENT.get_svg()))
        self._icon.props.pulsing = True
        self.append(self._icon)

        GLib.timeout_add_seconds(self._PULSE_TIMEOUT,
                                 self.__stop_pulsing_cb)

        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

    def __stop_pulsing_cb(self):
        self._icon.props.pulsing = False
        return False

    def do_set_property(self, pspec, value):
        if pspec.name == 'xo-color':
            if self._icon.props.base_color != value:
                self._icon.props.base_color = value
        elif pspec.name == 'icon-name':
            if self._icon.props.icon_name != value:
                self._icon.props.icon_name = value
        elif pspec.name == 'icon-filename':
            if self._icon.props.file != value:
                self._icon.props.file = value

    def do_get_property(self, pspec):
        if pspec.name == 'xo-color':
            return self._icon.props.base_color
        if pspec.name == 'icon-name':
            return self._icon.props.icon_name
        if pspec.name == 'icon-filename':
            return self._icon.props.file

    def _set_palette(self, palette):
        self._icon.palette = palette

    def _get_palette(self):
        return self._icon.palette

    palette = property(_get_palette, _set_palette)

    def show_badge(self):
        self._icon.show_badge()

    def hide_badge(self):
        self._icon.hide_badge()


class NotificationWindow(Gtk.Box):
    __gtype_name__ = 'SugarNotificationWindow'

    def __init__(self, **kwargs):
        # strip Gtk.Window-specific kwargs not valid on Gtk.Box
        box_kwargs = {k: v for k, v in kwargs.items()
                      if k not in ('decorated', 'resizable', 'focusable')}
        super().__init__(**box_kwargs)

        self.add_css_class('notification-window')
        self.add_css_class('frame-notification')
        self.set_valign(Gtk.Align.START)
        self.set_halign(Gtk.Align.START)
