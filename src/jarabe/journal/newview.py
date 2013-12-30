# Copyright (C) 2014 Sam Parkinson
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
import cairo
import json

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository.GdkPixbuf import Pixbuf

from sugar3.graphics.icon import Icon, EventIcon, _IconBuffer
from sugar3.graphics import style
from sugar3 import util
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.objectchooser import get_preview_pixbuf
from sugar3.graphics.palettewindow import CursorInvoker

from jarabe.model import bundleregistry

from jarabe.journal import model
from jarabe.journal import misc
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import journalwindow

UPDATE_SIZE = 30


class ExpandedView(Gtk.IconView):

    def __init__(self, children_str, ja):
        self._ja = ja
        Gtk.IconView.__init__(self)

        self.rebuild(children_str)
        self.set_model(self._store)
        self.set_pixbuf_column(1)

        pr = Gtk.CellRendererPixbuf()
        pr.set_alignment(0.5, 0.5)
        self.pack_start(pr, True)
        self.set_cell_data_func(pr, self._img_data_func, None)

        tr = Gtk.CellRendererText()
        tr.set_alignment(0.5, 0.5)
        self.pack_start(tr, True)
        self.set_cell_data_func(tr, self._title_data_func, None)

        self._invoker = CursorInvoker(self)

        self.connect('item-activated', self._launch_cb)

    def _launch_cb(self, self_again, path):
        misc.resume(model.get(self._store[path][0]),
                    alert_window=journalwindow.get_journal_window())

    def rebuild(self, children_str):
        self._store = Gtk.ListStore(str, Pixbuf, str)
        for uid in children_str.split('|'):
            if not uid:
                continue

            metadata = model.get(uid)
            title = metadata.get('title', 'No Title')
            pb = get_preview_pixbuf(metadata.get('preview', ''))

            if not pb:
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 216, 162)
                cr = cairo.Context(surface)
                cr.set_source_rgba(1, 1, 1, 1)
                cr.set_operator(cairo.OPERATOR_SOURCE)
                cr.paint()
                pb = Gdk.pixbuf_get_from_surface(surface, 0, 0, 216, 162)

            self._store.append([uid, pb, title])
        self.set_model(self._store)

    def create_palette(self):
        tree_model = self.get_model()
        display = Gdk.Display.get_default()
        manager = display.get_device_manager()
        pointer_device = manager.get_client_pointer()
        screen, x, y = pointer_device.get_position()

        path = self.get_path_at_pos(x, y)
        if not path:
            y -= 15
            path = self.get_path_at_pos(x, y)
        metadata = model.get(tree_model[path][0])

        palette = ObjectPalette(self._ja, metadata, detail=False)
        return palette

    def _title_data_func(self, view, cell, store, i, data):
        title = store.get_value(i, 2)
        cell.props.markup = title

    def _img_data_func(self, view, cell, store, i, data):
        img = store.get_value(i, 1)
        cell.props.pixbuf = img


class BuddyIcon(EventIcon):
    __gtype_name__ = 'JournalIconBuddy'

    def __init__(self, buddy):
        EventIcon.__init__(self)
        self.set_buddy(buddy)

    def set_buddy(self, buddy):
        if buddy is None:
            self.props.icon_name = None
        else:
            nick_, xo_color = buddy
            self.props.icon_name = 'computer-xo'
            self.props.xo_color = xo_color
            self.props.palette = BuddyPalette((nick_, xo_color.to_string()))

    buddy = GObject.property(type=object, setter=set_buddy)


class _ItemView(Gtk.Box):

    __gsignals__ = {
        'drag-changed': (GObject.SIGNAL_RUN_FIRST, None, (bool,))
    }

    def __init__(self, ja, metadata):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self._uid = metadata['uid']
        self._children = metadata.get('children')
        self._expanded_view = None
        self._is_expanded = False
        self._ja = ja

        self._top_box = Gtk.Box()
        self._top_box.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new('journal-object-id', 0, 0)],
            Gdk.DragAction.COPY)
        self._top_box.connect('drag-begin', self._drag_begin)
        self._top_box.connect('drag-end', self._drag_end)
        self._top_box.connect('drag-data-get', self.do_drag_data_get)
        self.pack_start(self._top_box, False, False, 4)
        self._top_box.show()

        self._expand_box = Gtk.EventBox()
        self._expand = Icon(icon_name='go-down',
                            icon_size=Gtk.IconSize.MENU,
                            fill_color=style.COLOR_TOOLBAR_GREY.get_svg())
        self._expand_box.connect('button-press-event', self._expand_cb)
        self._expand_box.add(self._expand)
        self._top_box.pack_start(self._expand_box, False, False, 4)
        self._expand_box.show()

        bundle_id = metadata.get('activity', '')
        if not bundle_id:
            bundle_id = metadata.get('bundle_id', '')
        if bundle_id:
            activity_info = bundleregistry.get_registry().get_bundle(bundle_id)
            if activity_info:
                action = activity_info.get_action_text().strip()
            else:
                action = 'Did a'
        else:
            action = 'Did a'

        self._action_lab = Gtk.Label()
        self._action_lab.set_markup(action)
        self._top_box.pack_start(self._action_lab, False, False, 4)
        self._action_lab.show()

        self._icon_name = misc.get_icon_name(metadata)
        self._a_icon = EventIcon(file_name=self._icon_name)
        palette = ObjectPalette(ja, model.get(self._uid))
        self._a_icon.set_palette(palette)
        self._top_box.pack_start(self._a_icon, False, False, 0)
        self._a_icon.show()

        self._title_lab = Gtk.Label()
        self._top_box.pack_start(self._title_lab, False, False, 4)
        self._title_lab.show()

        self._resume_box = Gtk.EventBox()
        self._resume = Icon(icon_name='go-next',
                            icon_size=Gtk.IconSize.MENU,
                            fill_color=style.COLOR_TOOLBAR_GREY.get_svg())
        self._resume_box.connect('button-press-event', self._resume_cb)
        self._resume_box.add(self._resume)
        self._top_box.pack_start(self._resume_box, False, False, 4)
        self._resume_box.show()
        self._resume.show()

        self._with = Gtk.Label('with')
        self._top_box.pack_start(self._with, False, False, 4)

        self._buddies_box = Gtk.Box()
        self._top_box.pack_start(self._buddies_box, False, False, 0)
        self._buddies_box.show()

        self._buddy_btns = {}

        self._date_lab = Gtk.Label()
        self._top_box.pack_start(self._date_lab, False, False, 4)
        self._date_lab.show()

        self.update(metadata)

    def _drag_begin(self, widget, drag_context):
        self._is_dragging = True
        self.emit('drag-changed', True)

        ib = _IconBuffer()
        ib.xocolor = self._xocolor
        ib.file_name = self._icon_name
        Gtk.drag_set_icon_surface(drag_context, ib.get_surface())

    def do_drag_data_get(self, target, context, selection, x, y):
        uid = self._uid
        target_atom = selection.get_target()
        target_name = target_atom.name()
        if target_name == 'text/uri-list':
            # Get hold of a reference so the temp file doesn't get deleted
            self._temp_drag_file_path = model.get_file(uid)
            logging.debug('putting %r in selection', self._temp_drag_file_path)
            selection.set(target_atom, 8, self._temp_drag_file_path)
            return True
        elif target_name == 'journal-object-id':
            # uid is unicode but Gtk.SelectionData.set() needs str
            selection.set(target_atom, 8, str(uid))
            return True
        logging.error('Unknowen drag dest:'+target_name)
        return False

    def _drag_end(self, widget, drag_context):
        self._is_dragging = False
        self.emit('drag-changed', False)

    def _resume_cb(self, arg1, arg2=None):
        misc.resume(model.get(self._uid),
                    alert_window=journalwindow.get_journal_window())

    def _expand_cb(self, arg1, arg2=None):
        if not self._is_expanded:
            self._expand.props.icon_name = 'go-next'
            self._is_expanded = True
            if self._expanded_view and self._children:
                self._expanded_view.rebuild(self._children)
                self._expanded_view.show()
            elif self._children:
                self._expanded_view = ExpandedView(self._children, self._ja)
                self.pack_end(self._expanded_view, False, False, 4)
                self._expanded_view.show()
            else:
                pass
        else:
            self._is_expanded = False
            self._expand.props.icon_name = 'go-down'
            if self._children:
                self._expanded_view.hide()

    def update(self, metadata):
        if misc.is_activity_bundle(metadata):
            self._xocolor = XoColor(
                '%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                           style.COLOR_TRANSPARENT.get_svg()))
        else:
            self._xocolor = misc.get_icon_color(metadata)
        self._a_icon.set_xo_color(self._xocolor)

        try:
            timestamp = float(metadata.get('timestamp', 0))
        except (TypeError, ValueError):
            timestamp_content = 'Unknown'
        else:
            timestamp_content = util.timestamp_to_elapsed_string(timestamp)
        self._date_lab.set_markup(timestamp_content)

        self._title_lab.set_markup('<b>{}</b>'.format(metadata.get(
                                   'title', 'No Title')))

        self._childern = metadata.get('children', '')
        if self._children:
            self._expand.show()
        else:
            self._expand.hide()

        if metadata.get('buddies'):
            buddies = []
            try:
                buddies = json.loads(metadata['buddies']).values()
            except json.decoder.JSONDecodeError, exception:
                logging.warning('Cannot decode buddies for %r: %s',
                                metadata['uid'], exception)
            self._with.show()

            for i in buddies:
                try:
                    nick, color = i
                except (AttributeError, ValueError), exception:
                    logging.warning('Malformed buddies for %r: %s',
                                    metadata['uid'], exception)
                else:
                    if not nick + color in self._buddy_btns:
                        b = BuddyIcon((nick, XoColor(color)))
                        self._buddies_box.pack_start(b, False, False, 0)
                        b.show()
                        self._buddy_btns[nick + color] = b
                        continue


class NewView(Gtk.EventBox):

    def __init__(self, ja):
        Gtk.EventBox.__init__(self)
        self._sw = Gtk.ScrolledWindow()
        self.add(self._sw)
        self._sw.show()

        self._main_box = None
        self._label_box = None
        self.ja = ja
        self._kids = []
        self._view_dict = {}
        self._is_dragging = False

        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA())

        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._sw.add(self._main_box)
        self._main_box.show()

        self._spinner = Gtk.Spinner()
        self._main_box.pack_end(self._spinner, True, True, 0)

    def _show_message(self, text):
        for i in self._kids:
            i.hide()
            self._main_box.remove(i)
        if self._label_box:
            self._label_box.hide()
            self._main_box.remove(self._label_box)
        self._label_box = Gtk.Alignment.new(0.5, 0.5, 0.1, 0.1)
        self._main_box.pack_start(self._label_box, True, True, 0)
        self._label_box.show()

        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._label_box.add(b)
        b.show()
        l = Gtk.Label(text)
        b.pack_start(l, True, True, 0)
        l.show()

    def _is_query_empty(self, query):
        # FIXME: This is a hack, we shouldn't have to update this every time
        # a new search term is added.
        return not (query.get('query') or query.get('mime_type') or
                    query.get('keep') or query.get('mtime') or
                    query.get('activity'))

    def _show_none_found(self, query):
        if self._is_query_empty(query):
            documents_path = model.get_documents_path()
            if query['mountpoints'] == ['/']:
                self._show_message('Your Journal is empty')
            elif documents_path and query['mountpoints'] == [documents_path]:
                self._show_message('Your documents folder is empty')
            else:
                self._show_message('This device is empty')
        else:
            self._show_message('No matching entries')

    def _re_add_view(self, metadata):
        self._main_box.pack_start(self._view_dict[metadata['uid']],
                                  True, True, 0)
        self._view_dict[metadata['uid']].show()
        self._view_dict[metadata['uid']].update(metadata)

    def _create_add_view(self, metadata):
        v = _ItemView(self.ja, metadata)
        v.connect('drag-changed', self._drag_changed)
        self._main_box.pack_start(v, True, True, 0)
        v.show()
        self._kids.append(v)
        if metadata['uid']:
            self._view_dict[metadata['uid']] = v

    def update_with_query(self, query):
        self._spinner.show()
        self._spinner.start()

        for i in self._kids:
            i.hide()
            self._main_box.remove(i)

        if self._label_box:
            self._label_box.hide()

        self._result_set = model.find(query, UPDATE_SIZE)
        self._result_set.setup()

        if self._result_set.get_length() == 0:
            GObject.idle_add(self._show_none_found, query)
        else:
            do_range = self._result_set.get_length()
            for i in range(do_range):
                self._result_set.seek(i)
                metadata = self._result_set.read()
                if not metadata.get('is_child', False):
                    if metadata['uid'] in self._view_dict:
                        GObject.idle_add(self._re_add_view, metadata)
                    else:
                        GObject.idle_add(self._create_add_view, metadata)

        self._spinner.stop()
        self._spinner.hide()

    def _drag_changed(self, widget, value):
        self._is_dragging = value

    def is_dragging(self):
        return self._is_dragging
