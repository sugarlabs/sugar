# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2008-2013, Sugar Labs
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
import time
import os

from gi.repository import GObject
from gi.repository import Gtk
import json

from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.icon import CanvasIcon, get_icon_file_name
from sugar3.graphics.icon import Icon, CellRendererIcon
from sugar3.graphics.alert import Alert
from sugar3.util import format_size
from sugar3.graphics.objectchooser import get_preview_pixbuf
from sugar3.activity.activity import PREVIEW_SIZE

from jarabe.journal.keepicon import KeepIcon
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import misc
from jarabe.journal import model
from jarabe.journal import journalwindow


class Separator(Gtk.VBox):

    def __init__(self, orientation):
        Gtk.VBox.__init__(
            self, background_color=style.COLOR_PANEL_GREY.get_gdk_color())


class BuddyList(Gtk.Alignment):

    def __init__(self, buddies):
        Gtk.Alignment.__init__(self)
        self.set(0, 0, 0, 0)

        hbox = Gtk.HBox()
        for buddy in buddies:
            nick_, color = buddy
            icon = CanvasIcon(icon_name='computer-xo',
                              xo_color=XoColor(color),
                              pixel_size=style.STANDARD_ICON_SIZE)
            icon.set_palette(BuddyPalette(buddy))
            hbox.pack_start(icon, True, True, 0)
        self.add(hbox)


class TextView(Gtk.TextView):

    def __init__(self):
        Gtk.TextView.__init__(self)
        text_buffer = Gtk.TextBuffer()
        self.set_buffer(text_buffer)
        self.set_left_margin(style.DEFAULT_PADDING)
        self.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)


class CommentsView(Gtk.TreeView):
    __gsignals__ = {
        'comments-changed': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
        'clicked': (GObject.SignalFlags.RUN_FIRST, None, [object]),
    }

    FROM = 'from'
    MESSAGE = 'message'
    ICON = 'icon'
    ICON_COLOR = 'icon-color'
    COMMENT_ICON = 0
    COMMENT_ICON_COLOR = 1
    COMMENT_FROM = 2
    COMMENT_MESSAGE = 3
    COMMENT_ERASE_ICON = 4
    COMMENT_ERASE_ICON_COLOR = 5

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.set_headers_visible(False)
        self._store = Gtk.ListStore(str, object, str, str, str, object)
        self._comments = []
        self._init_model()

    def update_comments(self, comments):
        self._store.clear()

        if comments:
            self._comments = json.loads(comments)
            for comment in self._comments:
                self._add_row(comment.get(self.FROM, ''),
                              comment.get(self.MESSAGE, ''),
                              comment.get(self.ICON, 'computer-xo'),
                              comment.get(self.ICON_COLOR, '#FFFFFF,#000000'))

    def _get_selected_row(self):
        selection = self.get_selection()
        return selection.get_selected()

    def _add_row(self, sender, message, icon_name, icon_color):
        self._store.append((get_icon_file_name(icon_name),
                            XoColor(icon_color),
                            sender,
                            message,
                            get_icon_file_name('list-remove'),
                            XoColor('#FFFFFF,#000000')))

    def _init_model(self):
        self.set_model(self._store)
        col = Gtk.TreeViewColumn()

        who_icon = CellRendererCommentIcon()
        col.pack_start(who_icon, False)
        col.add_attribute(who_icon, 'file-name', self.COMMENT_ICON)
        col.add_attribute(who_icon, 'xo-color', self.COMMENT_ICON_COLOR)

        who_text = Gtk.CellRendererText()
        col.pack_start(who_text, True)
        col.add_attribute(who_text, 'text', self.COMMENT_FROM)

        comment_text = Gtk.CellRendererText()
        col.pack_start(comment_text, True)
        col.add_attribute(comment_text, 'text', self.COMMENT_MESSAGE)

        erase_icon = CellRendererCommentIcon()
        erase_icon.connect('clicked', self._erase_comment_cb)
        col.pack_start(erase_icon, False)
        col.add_attribute(erase_icon, 'file-name', self.COMMENT_ERASE_ICON)
        col.add_attribute(
            erase_icon, 'xo-color', self.COMMENT_ERASE_ICON_COLOR)

        self.append_column(col)

    def _erase_comment_cb(self, widget, event):
        alert = Alert()

        entry = self.get_selection().get_selected()[1]
        erase_string = _('Erase')
        alert.props.title = erase_string
        alert.props.msg = _('Do you want to permanently erase \"%s\"?') \
            % self._store[entry][self.COMMENT_MESSAGE]

        icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), icon)
        icon.show()

        ok_icon = Icon(icon_name='dialog-ok')
        alert.add_button(Gtk.ResponseType.OK, erase_string, ok_icon)
        ok_icon.show()

        alert.connect('response', self._erase_alert_response_cb, entry)

        journalwindow.get_journal_window().add_alert(alert)
        alert.show()

    def _erase_alert_response_cb(self, alert, response_id, entry):
        journalwindow.get_journal_window().remove_alert(alert)

        if response_id is Gtk.ResponseType.OK:
            self._store.remove(entry)

            # Regenerate comments from current contents of store
            self._comments = []
            for entry in self._store:
                self._comments.append({
                    self.FROM: entry[self.COMMENT_FROM],
                    self.MESSAGE: entry[self.COMMENT_MESSAGE],
                    self.ICON: entry[self.COMMENT_ICON],
                    self.ICON_COLOR: '[%s]' % (
                        entry[self.COMMENT_ICON_COLOR].to_string()),
                })

            self.emit('comments-changed', json.dumps(self._comments))


class CellRendererCommentIcon(CellRendererIcon):

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.SMALL_ICON_SIZE
        self.props.height = style.SMALL_ICON_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_BLACK.get_svg()
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE


class BaseExpandedEntry(GObject.GObject):

    def __init__(self):
        # Create a header
        self._keep_icon = None
        self._keep_sid = None
        self._icon = None
        self._icon_box = None
        self._title = None
        self._date = None

    def create_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self._keep_icon = self._create_keep_icon()
        header.pack_start(self._keep_icon, False, False, style.DEFAULT_SPACING)

        self._icon_box = Gtk.HBox()
        header.pack_start(self._icon_box, False, False, style.DEFAULT_SPACING)

        self._title = self._create_title()
        header.pack_start(self._title, True, True, 0)

        # TODO: create a version list popup instead of a date label
        self._date = self._create_date()
        header.pack_start(self._date, False, False, style.DEFAULT_SPACING)

        return header

    def _create_keep_icon(self):
        keep_icon = KeepIcon()
        return keep_icon

    def _create_title(self):
        entry = Gtk.Entry()
        return entry

    def _create_date(self):
        date = Gtk.Label()
        return date


class ExpandedEntry(Gtk.EventBox, BaseExpandedEntry):

    def __init__(self, journalactivity):
        BaseExpandedEntry.__init__(self)
        self._journalactivity = journalactivity
        Gtk.EventBox.__init__(self)
        self._vbox = Gtk.VBox()
        self.add(self._vbox)

        self._metadata = None
        self._update_title_sid = None

        self.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        self._header = self.create_header()
        self._vbox.pack_start(self._header, False, False,
                              style.DEFAULT_SPACING * 2)
        self._keep_sid = self._keep_icon.connect(
            'toggled', self._keep_icon_toggled_cb)
        self._title.connect(
            'focus-out-event', self._title_focus_out_event_cb)

        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            # Reverse header children.
            for child in self._header.get_children():
                self._header.reorder_child(child, 0)

        # Create a two-column body
        body_box = Gtk.EventBox()
        body_box.set_border_width(style.DEFAULT_SPACING)
        body_box.modify_bg(Gtk.StateType.NORMAL,
                           style.COLOR_WHITE.get_gdk_color())
        self._vbox.pack_start(body_box, True, True, 0)
        body = Gtk.HBox()
        body_box.add(body)

        first_column = Gtk.VBox()
        body.pack_start(first_column, False, False, style.DEFAULT_SPACING)

        second_column = Gtk.VBox()
        body.pack_start(second_column, True, True, 0)

        # First body column
        self._preview_box = Gtk.Frame()
        style_context = self._preview_box.get_style_context()
        style_context.add_class('journal-preview-box')
        first_column.pack_start(self._preview_box, False, True, 0)

        self._technical_box = Gtk.VBox()
        first_column.pack_start(self._technical_box, False, False, 0)

        # Second body column
        description_box, self._description = self._create_description()
        second_column.pack_start(description_box, True, True,
                                 style.DEFAULT_SPACING)

        tags_box, self._tags = self._create_tags()
        second_column.pack_start(tags_box, True, True,
                                 style.DEFAULT_SPACING)

        comments_box, self._comments = self._create_comments()
        second_column.pack_start(comments_box, True, True,
                                 style.DEFAULT_SPACING)

        self._buddy_list = Gtk.VBox()
        second_column.pack_start(self._buddy_list, True, False, 0)
        self.show_all()

    def set_metadata(self, metadata):
        if self._metadata == metadata:
            return
        self._metadata = metadata

        self._keep_icon.handler_block(self._keep_sid)
        self._keep_icon.set_active(int(metadata.get('keep', 0)) == 1)
        self._keep_icon.handler_unblock(self._keep_sid)

        self._icon = self._create_icon()
        for child in self._icon_box.get_children():
            self._icon_box.remove(child)
            # FIXME: self._icon_box.foreach(self._icon_box.remove)
        self._icon_box.pack_start(self._icon, False, False, 0)

        self._date.set_text(misc.get_date(metadata))

        self._title.set_text(metadata.get('title', _('Untitled')))

        if self._preview_box.get_child():
            self._preview_box.remove(self._preview_box.get_child())
        self._preview_box.add(self._create_preview())

        for child in self._technical_box.get_children():
            self._technical_box.remove(child)
            # FIXME: self._technical_box.foreach(self._technical_box.remove)
        self._technical_box.pack_start(self._create_technical(),
                                       False, False, style.DEFAULT_SPACING)

        for child in self._buddy_list.get_children():
            self._buddy_list.remove(child)
            # FIXME: self._buddy_list.foreach(self._buddy_list.remove)
        self._buddy_list.pack_start(self._create_buddy_list(), False, False,
                                    style.DEFAULT_SPACING)

        description = metadata.get('description', '')
        self._description.get_buffer().set_text(description)
        tags = metadata.get('tags', '')
        self._tags.get_buffer().set_text(tags)
        comments = metadata.get('comments', '')
        self._comments.update_comments(comments)

    def _create_icon(self):
        icon = CanvasIcon(file_name=misc.get_icon_name(self._metadata))
        icon.connect_after('activate', self.__icon_activate_cb)

        if misc.is_activity_bundle(self._metadata):
            xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                          style.COLOR_TRANSPARENT.get_svg()))
        else:
            xo_color = misc.get_icon_color(self._metadata)
        icon.props.xo_color = xo_color

        icon.set_palette(ObjectPalette(self._journalactivity, self._metadata))

        return icon

    def _create_preview(self):

        box = Gtk.EventBox()
        box.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        metadata = self._metadata
        pixbuf = get_preview_pixbuf(metadata.get('preview', ''))
        has_preview = pixbuf is not None

        if has_preview:
            im = Gtk.Image()
            im.set_from_pixbuf(pixbuf)
            box.add(im)
            im.show()
        else:
            label = Gtk.Label()
            label.set_text(_('No preview'))
            width, height = PREVIEW_SIZE[0], PREVIEW_SIZE[1]
            label.set_size_request(width, height)
            box.add(label)
            label.show()

        box.connect_after('button-release-event',
                          self._preview_box_button_release_event_cb)
        return box

    def _create_technical(self):
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        if 'filesize' in self._metadata:
            filesize = self._metadata['filesize']
        else:
            filesize = model.get_file_size(self._metadata['uid'])

        lines = [
            _('Kind: %s') % (self._metadata.get('mime_type') or _('Unknown'),),
            _('Date: %s') % (self._format_date(),),
            _('Size: %s') % (format_size(int(filesize)))
        ]

        for line in lines:
            linebox = Gtk.HBox()
            vbox.pack_start(linebox, False, False, 0)

            text = Gtk.Label()
            text.set_markup('<span foreground="%s">%s</span>' % (
                style.COLOR_BUTTON_GREY.get_html(), line))
            linebox.pack_start(text, False, False, 0)

        return vbox

    def _format_date(self):
        if 'timestamp' in self._metadata:
            try:
                timestamp = float(self._metadata['timestamp'])
            except (ValueError, TypeError):
                logging.warning('Invalid timestamp for %r: %r',
                                self._metadata['uid'],
                                self._metadata['timestamp'])
            else:
                return time.strftime('%x', time.localtime(timestamp))
        return _('No date')

    def _create_buddy_list(self):

        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        text = Gtk.Label()
        text.set_markup('<span foreground="%s">%s</span>' % (
            style.COLOR_BUTTON_GREY.get_html(), _('Participants:')))
        halign = Gtk.Alignment.new(0, 0, 0, 0)
        halign.add(text)
        vbox.pack_start(halign, False, False, 0)

        if self._metadata.get('buddies'):
            buddies = json.loads(self._metadata['buddies']).values()
            vbox.pack_start(BuddyList(buddies), False, False, 0)
            return vbox
        else:
            return vbox

    def _create_scrollable(self, widget, label=None):
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        if label is not None:
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

    def _create_description(self):
        widget = TextView()
        widget.connect('focus-out-event',
                       self._description_tags_focus_out_event_cb)
        return self._create_scrollable(widget, label=_('Description:')), widget

    def _create_tags(self):
        widget = TextView()
        widget.connect('focus-out-event',
                       self._description_tags_focus_out_event_cb)
        return self._create_scrollable(widget, label=_('Tags:')), widget

    def _create_comments(self):
        widget = CommentsView()
        widget.connect('comments-changed', self._comments_changed_cb)
        return self._create_scrollable(widget, label=_('Comments:')), widget

    def _title_notify_text_cb(self, entry, pspec):
        if not self._update_title_sid:
            self._update_title_sid = \
                GObject.timeout_add_seconds(1,
                                            self._update_title_cb)

    def _title_focus_out_event_cb(self, entry, event):
        self._update_entry()

    def _description_tags_focus_out_event_cb(self, text_view, event):
        self._update_entry()

    def _comments_changed_cb(self, event, comments):
        self._metadata['comments'] = comments
        self._write_entry()

    def _update_entry(self, needs_update=False):
        if not model.is_editable(self._metadata):
            return

        old_title = self._metadata.get('title', None)
        new_title = self._title.get_text()
        if old_title != new_title:
            self._icon.palette.props.primary_text = new_title
            self._metadata['title'] = new_title
            self._metadata['title_set_by_user'] = '1'
            needs_update = True

        bounds = self._tags.get_buffer().get_bounds()
        old_tags = self._metadata.get('tags', None)
        new_tags = self._tags.get_buffer().get_text(bounds[0], bounds[1],
                                                    include_hidden_chars=False)

        if old_tags != new_tags:
            self._metadata['tags'] = new_tags
            needs_update = True

        bounds = self._description.get_buffer().get_bounds()
        old_description = self._metadata.get('description', None)
        new_description = self._description.get_buffer().get_text(
            bounds[0], bounds[1], include_hidden_chars=False)
        if old_description != new_description:
            self._metadata['description'] = new_description
            needs_update = True

        if needs_update:
            self._write_entry()

        self._update_title_sid = None

    def _write_entry(self):
        if self._metadata.get('mountpoint', '/') == '/':
            model.write(self._metadata, update_mtime=False)
        else:
            old_file_path = os.path.join(
                self._metadata['mountpoint'],
                model.get_file_name(self._metadata['title'],
                                    self._metadata['mime_type']))
            model.write(self._metadata, file_path=old_file_path,
                        update_mtime=False)

    def _keep_icon_toggled_cb(self, keep_icon):
        if keep_icon.get_active():
            self._metadata['keep'] = '1'
        else:
            self._metadata['keep'] = '0'
        self._update_entry(needs_update=True)

    def __icon_activate_cb(self, button):
        misc.resume(self._metadata,
                    alert_window=journalwindow.get_journal_window())
        return True

    def _preview_box_button_release_event_cb(self, button, event):
        logging.debug('_preview_box_button_release_event_cb')
        misc.resume(self._metadata,
                    alert_window=journalwindow.get_journal_window())
        return True
