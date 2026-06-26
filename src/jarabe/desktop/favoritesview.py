# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2008-2013 Sugar Labs
# Copyright (C) 2013 Daniel Francis
# Copyright (C) 2013 Walter Bender
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

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from sugar4.graphics import style
from sugar4.graphics.icon import Icon
from sugar4.graphics.icon import CanvasIcon
from sugar4.graphics.palettemenu import PaletteMenuItem
from sugar4.graphics.palettemenu import PaletteMenuItemSeparator
from sugar4.graphics.alert import Alert, ErrorAlert
from sugar4.graphics.xocolor import XoColor
from jarabe.util import activityfactory
from sugar4 import dispatch
from sugar4.datastore import datastore

from jarabe.view.palettes import JournalPalette
from jarabe.view.palettes import CurrentActivityPalette
from jarabe.view.palettes import ActivityPalette
from jarabe.view.buddyicon import BuddyIcon
from jarabe.view.buddymenu import BuddyMenu
from jarabe.model.buddy import get_owner_instance
from jarabe.model import shell
from jarabe.model import bundleregistry
from jarabe.model import desktop
from jarabe.journal import misc

from jarabe.desktop import schoolserver
from jarabe.desktop.schoolserver import RegisterError
from jarabe.desktop import favoriteslayout
from jarabe.desktop.viewcontainer import ViewContainer
from jarabe.util.normalize import normalize_string

_logger = logging.getLogger('FavoritesView')

LAYOUT_MAP = {favoriteslayout.RingLayout.key: favoriteslayout.RingLayout,
              favoriteslayout.BoxLayout.key: favoriteslayout.BoxLayout,
              favoriteslayout.TriangleLayout.key:
              favoriteslayout.TriangleLayout,
              favoriteslayout.SunflowerLayout.key:
              favoriteslayout.SunflowerLayout,
              favoriteslayout.RandomLayout.key: favoriteslayout.RandomLayout}
"""Map numeric layout identifiers to uninstantiated subclasses of
`FavoritesLayout` which implement the layouts.  Additional information
about the layout can be accessed with fields of the class."""

_favorites_settings = None


class FavoritesBox(Gtk.Box):
    __gtype_name__ = 'SugarFavoritesBox'

    def __init__(self, favorite_view):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.favorite_view = favorite_view
        self._view = FavoritesView(self)
        self.append(self._view)
        self._view.set_vexpand(True)
        self._view.set_hexpand(True)

        self._alert = None

    def set_filter(self, query):
        self._view.set_filter(query)

    def set_resume_mode(self, resume_mode):
        self._view.set_resume_mode(resume_mode)

    def grab_focus(self):
        # overwrite grab focus in order to grab focus from the parent
        return self._view.grab_focus()

    def add_alert(self, alert):
        if self._alert is not None:
            self.remove_alert()
        self._alert = alert
        self.prepend(alert)

    def remove_alert(self):
        self.remove(self._alert)
        self._alert = None

    def _get_selected(self, query):
        return self._view._get_selected(query)


class FavoritesView(ViewContainer):
    __gtype_name__ = 'SugarFavoritesView'

    def __init__(self, box):
        self._box = box
        self._layout = None

        owner_icon = OwnerIcon(style.XLARGE_ICON_SIZE)
        owner_icon.connect('register-activate', self.__register_activate_cb)

        current_activity = CurrentActivityIcon()

        ViewContainer.__init__(self, layout=self._layout,
                               owner_icon=owner_icon,
                               activity_icon=current_activity)
        self.set_can_focus(False)

        # Drag and drop is set only for the Random layout.
        self._dragging_mode = False
        self._drop_target = None

        self._hot_x = None
        self._hot_y = None
        self._last_clicked_icon = None

        self._alert = None
        self._resume_mode = Gio.Settings.new(
            'org.sugarlabs.user').get_boolean('resume-activity')

        GLib.idle_add(self.__connect_to_bundle_registry_cb)

        favorites_settings = get_settings(self._box.favorite_view)
        favorites_settings.changed.connect(self.__settings_changed_cb)
        layout_set = self._set_layout(favorites_settings.layout)
        if layout_set:
            self.set_layout(self._layout)

    def __settings_changed_cb(self, **kwargs):
        favorites_settings = get_settings(self._box.favorite_view)
        layout_set = self._set_layout(favorites_settings.layout)
        if layout_set:
            self.set_layout(self._layout)
            registry = bundleregistry.get_registry()
            for info in registry:
                if registry.is_bundle_favorite(info.get_bundle_id(),
                                               info.get_activity_version(),
                                               self._box.favorite_view):
                    self._add_activity(info)

    def _set_layout(self, layout):
        if layout not in LAYOUT_MAP:
            logging.warning('Unknown favorites layout: %r', layout)
            layout = favoriteslayout.RingLayout.key
            assert layout in LAYOUT_MAP

        if self._layout is not None and self._dragging_mode:
            if self._drop_target:
                self.remove_controller(self._drop_target)
                self._drop_target = None

        if layout == favoriteslayout.RandomLayout.key:
            self._dragging_mode = True
            self._drop_target = Gtk.DropTarget.new(type=GObject.TYPE_STRING, actions=Gdk.DragAction.MOVE)
            self._drop_target.connect('motion', self.__drag_motion_cb)
            self._drop_target.connect('drop', self.__drag_drop_cb)
            self.add_controller(self._drop_target)
        else:
            self._dragging_mode = False

        self._layout = LAYOUT_MAP[layout]()
        return True

    layout = property(None, _set_layout)

    def add(self, child):
        if child != self._owner_icon and child != self._activity_icon:
            self._children.append(child)
            
            drag_source = Gtk.DragSource.new()
            drag_source.set_actions(Gdk.DragAction.MOVE)
            drag_source.connect("prepare", self.__drag_prepare_cb, child)
            drag_source.connect("drag-begin", self.__drag_begin_cb, child)
            child.add_controller(drag_source)

        child.set_parent(self)

    def __drag_prepare_cb(self, source, x, y, child):
        if not self._dragging_mode:
            return None
        self._last_clicked_icon = child
        v = GObject.Value(GObject.TYPE_STRING, "activity-icon")
        return Gdk.ContentProvider.new_for_value(v)

    def __drag_begin_cb(self, source, drag, child):
        if not self._dragging_mode:
            return
        if not child.props.file_name:
            return
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(child.props.file_name)
            self._hot_x = pixbuf.get_width() / 2
            self._hot_y = pixbuf.get_height() / 2
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            source.set_icon(texture, self._hot_x, self._hot_y)
        except Exception as e:
            logging.error("Failed to create drag icon: %s", e)
            self._hot_x = 0
            self._hot_y = 0

    def __drag_motion_cb(self, target, x, y):
        if self._last_clicked_icon is not None:
            return Gdk.DragAction.MOVE
        return Gdk.DragAction(0)

    def __drag_drop_cb(self, target, value, x, y):
        if self._last_clicked_icon is not None:
            allocation = Gdk.Rectangle()
            allocation.x = 0
            allocation.y = 0
            allocation.width = self.get_width()
            allocation.height = self.get_height()
            self._layout.move_icon(self._last_clicked_icon,
                                   x - self._hot_x, y - self._hot_y, allocation)

            self._hot_x = None
            self._hot_y = None
            self._last_clicked_icon = None
            return True
        return False

    def __connect_to_bundle_registry_cb(self):
        registry = bundleregistry.get_registry()

        for info in registry:
            if registry.is_bundle_favorite(info.get_bundle_id(),
                                           info.get_activity_version(),
                                           self._box.favorite_view):
                self._add_activity(info)

        registry.connect('bundle-added', self.__activity_added_cb)
        registry.connect('bundle-removed', self.__activity_removed_cb)
        registry.connect('bundle-changed', self.__activity_changed_cb)

    def _add_activity(self, activity_info):
        if activity_info.get_bundle_id() == 'org.laptop.JournalActivity':
            return

        if not activity_info.get_show_launcher():
            return

        icon = ActivityIcon(activity_info)
        icon.props.pixel_size = style.STANDARD_ICON_SIZE
        # icon.set_resume_mode(self._resume_mode)
        self.add(icon)

    def __activity_added_cb(self, activity_registry, activity_info):
        registry = bundleregistry.get_registry()
        if registry.is_bundle_favorite(activity_info.get_bundle_id(),
                                       activity_info.get_activity_version(),
                                       self._box.favorite_view):
            self._add_activity(activity_info)

    def __activity_removed_cb(self, activity_registry, activity_info):
        icon = self._find_activity_icon(activity_info.get_bundle_id(),
                                        activity_info.get_activity_version())
        if icon is not None:
            self.remove(icon)

    def _find_activity_icon(self, bundle_id, version):
        for icon in self.get_children():
            if isinstance(icon, ActivityIcon) and \
                    icon.bundle_id == bundle_id and icon.version == version:
                return icon
        return None

    def __activity_changed_cb(self, activity_registry, activity_info):
        if activity_info.get_bundle_id() == 'org.laptop.JournalActivity':
            return
        icon = self._find_activity_icon(activity_info.get_bundle_id(),
                                        activity_info.get_activity_version())
        if icon is not None:
            self.remove(icon)

        registry = bundleregistry.get_registry()
        if registry.is_bundle_favorite(activity_info.get_bundle_id(),
                                       activity_info.get_activity_version(),
                                       self._box.favorite_view):
            self._add_activity(activity_info)

    def set_filter(self, query):
        query = query.strip()
        for icon in self.get_children():
            if icon not in [self._owner_icon, self._activity_icon]:
                activity_name = icon.get_activity_name()
                if isinstance(activity_name, bytes):
                    activity_name = activity_name.decode()
                normalized_name = normalize_string(activity_name)
                if normalized_name.find(query) > -1:
                    icon.alpha = 1.0
                else:
                    icon.alpha = 0.33

    def _get_selected(self, query):
        query = query.strip()
        selected = []
        for icon in self.get_children():
            if icon not in [self._owner_icon, self._activity_icon]:
                activity_name = icon.get_activity_name()
                if isinstance(activity_name, bytes):
                    activity_name = activity_name.decode()
                normalized_name = normalize_string(activity_name)
                if normalized_name.find(query) > -1:
                    selected.append(icon)
        return selected

    def __register_activate_cb(self, icon):
        alert = Alert()
        alert.props.title = _('Registration')
        alert.props.msg = _('Please wait, searching for your school server.')
        self._box.add_alert(alert)
        GLib.idle_add(self.__register)

    def __register(self):
        self._box.remove_alert()
        alert = ErrorAlert()
        try:
            schoolserver.register_laptop()
        except RegisterError as e:
            alert.props.title = _('Registration Failed')
            alert.props.msg = '%s' % e
        else:
            alert.props.title = _('Registration Successful')
            alert.props.msg = _('You are now registered '
                                'with your school server.')

        alert.connect('response', self.__register_alert_response_cb)
        self._box.add_alert(alert)
        return False

    def __register_alert_response_cb(self, alert, response_id):
        self._box.remove_alert()

    def set_resume_mode(self, resume_mode):
        self._resume_mode = resume_mode
        for icon in self.get_children():
            if hasattr(icon, 'set_resume_mode'):
                icon.set_resume_mode(self._resume_mode)


class ActivityIcon(CanvasIcon):
    __gtype_name__ = 'SugarFavoriteActivityIcon'

    _BORDER_WIDTH = style.zoom(9)
    _MAX_RESUME_ENTRIES = 5

    def __init__(self, activity_info):
        CanvasIcon.__init__(self, cache=True,
                            file_name=activity_info.get_icon())

        self._activity_info = activity_info
        self._journal_entries = []
        self._resume_mode = Gio.Settings.new(
            'org.sugarlabs.user').get_boolean('resume-activity')

        self.connect_after('activate', self.__button_activate_cb)

        datastore.created.connect(self.__datastore_listener_updated_cb)
        datastore.updated.connect(self.__datastore_listener_updated_cb)
        datastore.deleted.connect(self.__datastore_listener_deleted_cb)

        self._refresh()
        self._update()

    def _refresh(self):
        bundle_id = self._activity_info.get_bundle_id()
        properties = ['uid', 'title', 'icon-color', 'activity', 'activity_id',
                      'mime_type', 'mountpoint']
        self._get_last_activity_async(bundle_id, properties)

    def __datastore_listener_updated_cb(self, **kwargs):
        bundle_id = self._activity_info.get_bundle_id()
        if kwargs['metadata'].get('activity', '') == bundle_id:
            self._refresh()

    def __datastore_listener_deleted_cb(self, **kwargs):
        for entry in self._journal_entries:
            if entry['uid'] == kwargs['object_id']:
                self._refresh()
                break

    def _get_last_activity_async(self, bundle_id, properties):
        query = {'activity': bundle_id}
        datastore.find(query, sorting=['+timestamp'],
                       limit=self._MAX_RESUME_ENTRIES,
                       properties=properties,
                       reply_handler=self.__get_last_activity_reply_handler_cb,
                       error_handler=self.__get_last_activity_error_handler_cb)

    def __get_last_activity_reply_handler_cb(self, entries, total_count):
        # If there's a problem with the DS index, we may get entries not
        # related to this activity.
        checked_entries = []
        for entry in entries:
            if entry['activity'] == self.bundle_id:
                checked_entries.append(entry)

        self._journal_entries = checked_entries
        self._update()

    def __get_last_activity_error_handler_cb(self, error):
        logging.error('Error retrieving most recent activities: %r', error)

    def _update(self):
        self.palette = None
        if not self._resume_mode or not self._journal_entries:
            xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                          style.COLOR_WHITE.get_svg()))
        else:
            xo_color = misc.get_icon_color(self._journal_entries[0])
        self.props.xo_color = xo_color

    def create_palette(self):
        palette = FavoritePalette(self._activity_info, self._journal_entries)
        palette.connect('activate', self.__palette_activate_cb)
        palette.connect('entry-activate', self.__palette_entry_activate_cb)
        self.connect_to_palette_pop_events(palette)
        return palette

    def __palette_activate_cb(self, palette):
        self._activate()

    def __palette_entry_activate_cb(self, palette, metadata):
        self._resume(metadata)

    def do_measure(self, orientation, for_size):
        min_size, nat_size, min_base, nat_base = super().do_measure(orientation, for_size)
        min_size += ActivityIcon._BORDER_WIDTH * 2
        nat_size += ActivityIcon._BORDER_WIDTH * 2
        return (min_size, nat_size, min_base, nat_base)

    def __button_activate_cb(self, icon):
        self._activate()

    def _resume(self, journal_entry):
        if not journal_entry['activity_id']:
            journal_entry['activity_id'] = activityfactory.create_activity_id()
        misc.resume(journal_entry, self._activity_info.get_bundle_id())

    def _activate(self):
        if self.palette is not None:
            self.palette.popdown(immediate=True)

        if self._resume_mode and self._journal_entries:
            self._resume(self._journal_entries[0])
        else:
            misc.launch(self._activity_info)

    def run_activity(self):
        self._activate()

    def get_bundle_id(self):
        return self._activity_info.get_bundle_id()
    bundle_id = property(get_bundle_id, None)

    def get_version(self):
        return self._activity_info.get_activity_version()
    version = property(get_version, None)

    def get_activity_name(self):
        return self._activity_info.get_name()

    def _get_installation_time(self):
        return self._activity_info.get_installation_time()
    installation_time = property(_get_installation_time, None)

    def _get_fixed_position(self):
        registry = bundleregistry.get_registry()
        return registry.get_bundle_position(self.bundle_id, self.version)
    fixed_position = property(_get_fixed_position, None)

    def set_resume_mode(self, resume_mode):
        self._resume_mode = resume_mode
        self._update()


class FavoritePalette(ActivityPalette):
    __gtype_name__ = 'SugarFavoritePalette'

    __gsignals__ = {
        'entry-activate': (GObject.SignalFlags.RUN_FIRST,
                           None, ([object])),
    }

    def __init__(self, activity_info, journal_entries):
        ActivityPalette.__init__(self, activity_info)

        if not journal_entries:
            xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                          style.COLOR_WHITE.get_svg()))
        else:
            xo_color = misc.get_icon_color(journal_entries[0])

        self.props.icon = Icon(file=activity_info.get_icon(),
                               xo_color=xo_color,
                               pixel_size=style.STANDARD_ICON_SIZE)

        if journal_entries:
            self.props.secondary_text = journal_entries[0]['title']

            menu_items = []
            for entry in journal_entries:
                icon_file_name = misc.get_icon_name(entry)
                color = misc.get_icon_color(entry)

                menu_item = PaletteMenuItem(text_label=entry['title'],
                                            file_name=icon_file_name,
                                            xo_color=color)
                menu_item.connect('activate', self.__resume_entry_cb, entry)
                menu_items.append(menu_item)

            if journal_entries:
                separator = PaletteMenuItemSeparator()
                menu_items.append(separator)

            for i in range(0, len(menu_items)):
                menu_items[i].set_hexpand(True)
                menu_items[i].set_vexpand(True)
                menu_items[i].set_halign(Gtk.Align.FILL)
                menu_items[i].set_valign(Gtk.Align.FILL)
                self.menu_box.append(menu_items[i])

    def __resume_entry_cb(self, menu_item, entry):
        if entry is not None:
            self.emit('entry-activate', entry)


class CurrentActivityIcon(CanvasIcon):

    def __init__(self):
        CanvasIcon.__init__(self, icon_name='activity-journal',
                            pixel_size=style.STANDARD_ICON_SIZE, cache=True)
        self._home_model = shell.get_model()
        self._home_activity = self._home_model.get_active_activity()

        if self._home_activity is None:
            self._home_activity = self._get_journal_activity()

        self._update()

        self._home_model.connect('active-activity-changed',
                                 self.__active_activity_changed_cb)

        self.connect_after('activate', self.__activate_cb)

    def _get_journal_activity(self):
        for activity in self._home_model._activities:
            if activity.is_journal():
                return activity
        return None

    def __activate_cb(self, icon):
        active_activity = self._home_model.get_active_activity()
        if active_activity is None:
            # No activity open: reveal the Journal directly.
            from jarabe.journal import journalactivity
            journalactivity.get_journal().reveal()
        else:
            self._home_model.activate_activity(active_activity)

    def _update(self):
        if self._home_activity is not None:
            self.props.file_name = self._home_activity.get_icon_path()
            self.props.xo_color = self._home_activity.get_icon_color()

            if self._home_activity.is_journal():
                if self._unbusy():
                    GLib.timeout_add(100, self._unbusy)
        else:
            self.props.xo_color = get_owner_instance().props.color

        self.props.pixel_size = style.STANDARD_ICON_SIZE

        if self.palette is not None:
            if isinstance(self.palette, Gtk.Window):
                self.palette.destroy()
            self.palette = None

    def _unbusy(self):
        import jarabe.desktop.homewindow
        hw = jarabe.desktop.homewindow.get_instance()
        if hw and hw.get_root():
            hw.unbusy()
            return False
        return True

    def create_palette(self):
        if self._home_activity is None:
            # Journal may not be registered yet – initialize it now.
            from jarabe.journal import journalactivity as _ja
            _ja.get_journal()
            self._home_activity = self._get_journal_activity()

        if self._home_activity is not None:
            if self._home_activity.is_journal():
                palette = JournalPalette(self._home_activity)
            else:
                palette = CurrentActivityPalette(self._home_activity)
            self.connect_to_palette_pop_events(palette)
            return palette

        return None

    def __active_activity_changed_cb(self, home_model, home_activity):
        if home_activity is None:
            self._home_activity = self._get_journal_activity()
            if self._home_activity is None:
                # journal not yet registered – initialize it
                from jarabe.journal import journalactivity as _ja
                _ja.get_journal()
                self._home_activity = self._get_journal_activity()
        else:
            self._home_activity = home_activity
        self._update()


class OwnerIcon(BuddyIcon):
    __gtype_name__ = 'SugarFavoritesOwnerIcon'

    __gsignals__ = {
        'register-activate': (GObject.SignalFlags.RUN_FIRST, None,
                              ([])),
    }

    def __init__(self, size):
        BuddyIcon.__init__(self, buddy=get_owner_instance(), pixel_size=size)

        def __enter_notify_event_cb(controller, x, y):
            self.unset_state_flags(Gtk.StateFlags.PRELIGHT)
            GLib.idle_add(self.remove_controller, controller)

        controller = Gtk.EventControllerMotion()
        controller.connect('enter', __enter_notify_event_cb)
        self.add_controller(controller)
        
        # Ensure left-click toggles the palette
        if hasattr(self, 'palette_invoker') and self.palette_invoker:
            self.palette_invoker.props.toggle_palette = True

    def create_palette(self):
        palette = BuddyMenu(get_owner_instance())

        settings = Gio.Settings.new('org.sugarlabs')
        if settings.get_boolean('show-register'):
            backup_url = settings.get_string('backup-url')

            if not backup_url:
                text = _('Register')
            else:
                text = _('Register again')

            register_menu = PaletteMenuItem(text, 'media-record')
            register_menu.connect('item-activated', self.__register_activate_cb)
            register_menu.set_hexpand(True)
            register_menu.set_vexpand(True)
            register_menu.set_halign(Gtk.Align.FILL)
            register_menu.set_valign(Gtk.Align.FILL)
            palette.menu_box.append_item(register_menu)
            register_menu.set_visible(True)

        self.connect_to_palette_pop_events(palette)

        return palette

    def __register_activate_cb(self, menuitem):
        self.emit('register-activate')


class FavoritesSetting(object):

    _DESKTOP_DIR = 'org.sugarlabs.desktop'
    _HOMEVIEWS_KEY = 'homeviews'

    def __init__(self, favorite_view):
        self._favorite_view = int(favorite_view)

        settings = Gio.Settings.new(self._DESKTOP_DIR)
        homeviews = settings.get_value(self._HOMEVIEWS_KEY).unpack()

        self._layout = homeviews[self._favorite_view]['layout']

        logging.debug('FavoritesSetting layout %r', self._layout)

        self._mode = None

        self.changed = dispatch.Signal()

    def get_layout(self):
        return self._layout

    def set_layout(self, layout):
        logging.debug('set_layout %r %r', layout, self._layout)
        if layout != self._layout:
            self._layout = layout

            settings = Gio.Settings.new(self._DESKTOP_DIR)
            homeviews = settings.get_value(self._HOMEVIEWS_KEY).unpack()

            homeviews[self._favorite_view]['layout'] = layout

            variant = GLib.Variant('aa{ss}', homeviews)
            settings.set_value(self._HOMEVIEWS_KEY, variant)

            self.changed.send(self)

    layout = property(get_layout, set_layout)


def get_settings(favorite_view=0):
    global _favorites_settings

    number_of_views = desktop.get_number_of_views()
    if _favorites_settings is None:
        _favorites_settings = []
        for i in range(number_of_views):
            _favorites_settings.append(FavoritesSetting(i))
    elif len(_favorites_settings) < number_of_views:
        for i in range(number_of_views - len(_favorites_settings)):
            _favorites_settings.append(
                FavoritesSetting(len(_favorites_settings)))
    return _favorites_settings[favorite_view]
