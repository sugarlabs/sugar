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

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.icon import CanvasIcon
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator
from sugar3.graphics.alert import Alert, ErrorAlert
from sugar3.graphics.xocolor import XoColor
from sugar3.activity import activityfactory
from sugar3 import dispatch
from sugar3.datastore import datastore

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

_ICON_DND_TARGET = ('activity-icon', Gtk.TargetFlags.SAME_WIDGET, 0)

LAYOUT_MAP = {favoriteslayout.RingLayout.key: favoriteslayout.RingLayout,
              # favoriteslayout.BoxLayout.key: favoriteslayout.BoxLayout,
              # favoriteslayout.TriangleLayout.key:
              # favoriteslayout.TriangleLayout,
              # favoriteslayout.SunflowerLayout.key:
              # favoriteslayout.SunflowerLayout,
              favoriteslayout.RandomLayout.key: favoriteslayout.RandomLayout}
"""Map numeric layout identifiers to uninstantiated subclasses of
`FavoritesLayout` which implement the layouts.  Additional information
about the layout can be accessed with fields of the class."""

_favorites_settings = None


class FavoritesBox(Gtk.VBox):
    __gtype_name__ = 'SugarFavoritesBox'

    def __init__(self, favorite_view):
        Gtk.VBox.__init__(self)

        self.favorite_view = favorite_view
        self._view = FavoritesView(self)
        self.pack_start(self._view, True, True, 0)
        self._view.show()

        self._alert = None

    def set_filter(self, query):
        self._view.set_filter(query)

    def set_resume_mode(self, resume_mode):
        self._view.set_resume_mode(resume_mode)

    def grab_focus(self):
        # overwrite grab focus in order to grab focus from the parent
        self._view.grab_focus()

    def add_alert(self, alert):
        if self._alert is not None:
            self.remove_alert()
        self._alert = alert
        self.pack_start(alert, False, True, 0)
        self.reorder_child(alert, 0)

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

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.drag_dest_set(0, [], 0)

        # Drag and drop is set only for the Random layout.  This is
        # the flag that enables or disables it.
        self._dragging_mode = False

        self._drag_motion_hid = None
        self._drag_drop_hid = None
        self._drag_data_received_hid = None

        self._dragging = False
        self._pressed_button = None
        self._press_start_x = 0
        self._press_start_y = 0
        self._hot_x = None
        self._hot_y = None
        self._last_clicked_icon = None

        self._alert = None
        self._resume_mode = Gio.Settings(
            'org.sugarlabs.user').get_boolean('resume-activity')

        GLib.idle_add(self.__connect_to_bundle_registry_cb)

        favorites_settings = get_settings(self._box.favorite_view)
        favorites_settings.changed.connect(self.__settings_changed_cb)
        self._set_layout(favorites_settings.layout)

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
            logging.warn('Unknown favorites layout: %r', layout)
            layout = favoriteslayout.RingLayout.key
            assert layout in LAYOUT_MAP

        if isinstance(self._layout, LAYOUT_MAP[layout]):
            return False

        if self._layout is not None and self._dragging_mode:
            self.disconnect(self._drag_motion_hid)
            self.disconnect(self._drag_drop_hid)
            self.disconnect(self._drag_data_received_hid)

        if layout == favoriteslayout.RandomLayout.key:
            self._dragging_mode = True
            self._drag_motion_hid = self.connect(
                'drag-motion', self.__drag_motion_cb)
            self._drag_drop_hid = self.connect(
                'drag-drop', self.__drag_drop_cb)
            self._drag_data_received_hid = self.connect(
                'drag-data-received', self.__drag_data_received_cb)
        else:
            self._dragging_mode = False

        self._layout = LAYOUT_MAP[layout]()
        return True

    layout = property(None, _set_layout)

    def do_add(self, child):
        if child != self._owner_icon and child != self._activity_icon:
            self._children.append(child)
            child.connect('button-press-event', self.__button_press_cb)
            child.connect('button-release-event', self.__button_release_cb)
            child.connect('motion-notify-event', self.__motion_notify_event_cb)
            child.connect('drag-begin', self.__drag_begin_cb)
        if child.get_realized():
            child.set_parent_window(self.get_parent_window())
        child.set_parent(self)

    def __button_release_cb(self, widget, event):
        if self._dragging:
            return True
        else:
            return False

    def __button_press_cb(self, widget, event):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self._last_clicked_icon = widget
            self._pressed_button = event.button
            self._press_start_x = event.x
            self._press_start_y = event.y
        return False

    def __motion_notify_event_cb(self, widget, event):
        if not self._dragging_mode:
            return False

        # if the mouse button is not pressed, no drag should occurr
        if not event.get_state() & Gdk.ModifierType.BUTTON1_MASK:
            self._pressed_button = None
            return False

        if event.is_hint:
            x, y, state_ = event.window.get_pointer()
        else:
            x = event.x
            y = event.y

        if widget.drag_check_threshold(int(self._press_start_x),
                                       int(self._press_start_y),
                                       int(x),
                                       int(y)):
            self._dragging = True
            target_entry = Gtk.TargetEntry.new(*_ICON_DND_TARGET)
            target_list = Gtk.TargetList.new([target_entry])
            widget.drag_begin(target_list,
                              Gdk.DragAction.MOVE,
                              1,
                              event)
        return False

    def __drag_begin_cb(self, widget, context):
        if not self._dragging_mode:
            return False

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(widget.props.file_name)

        self._hot_x = pixbuf.props.width / 2
        self._hot_y = pixbuf.props.height / 2
        Gtk.drag_set_icon_pixbuf(context, pixbuf, self._hot_x, self._hot_y)

    def __drag_motion_cb(self, widget, context, x, y, time):
        if self._last_clicked_icon is not None:
            Gdk.drag_status(context, context.get_suggested_action(), time)
            return True
        else:
            return False

    def __drag_drop_cb(self, widget, context, x, y, time):
        if self._last_clicked_icon is not None:
            target = Gdk.Atom.intern_static_string(_ICON_DND_TARGET[0])
            self.drag_get_data(context, target, time)
            self._layout.move_icon(self._last_clicked_icon,
                                   x - self._hot_x, y - self._hot_y,
                                   self.get_allocation())

            self._pressed_button = None
            self._press_start_x = None
            self._press_start_y = None
            self._hot_x = None
            self._hot_y = None
            self._last_clicked_icon = None
            self._dragging = False

            return True
        else:
            return False

    def __drag_data_received_cb(self, widget, context, x, y, selection_data,
                                info, time):
        Gdk.drop_finish(context, success=True, time_=time)

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
        icon = ActivityIcon(activity_info)
        icon.props.pixel_size = style.STANDARD_ICON_SIZE
        # icon.set_resume_mode(self._resume_mode)
        self.add(icon)
        icon.show()

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
                activity_name = icon.get_activity_name().decode('utf-8')
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
                activity_name = icon.get_activity_name().decode('utf-8')
                normalized_name = normalize_string(activity_name)
                if normalized_name.find(query) > -1:
                    selected.append(icon)
        return selected

    def __register_activate_cb(self, icon):
        alert = Alert()
        alert.props.title = _('Registration')
        alert.props.msg = _('Please wait, searching for your school server.')
        self._box.add_alert(alert)
        GObject.idle_add(self.__register)

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
        self._resume_mode = Gio.Settings(
            'org.sugarlabs.user').get_boolean('resume-activity')

        self.connect_after('activate', self.__button_activate_cb)

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

    def do_get_preferred_width(self):
        width = CanvasIcon.do_get_preferred_width(self)[0]
        width += ActivityIcon._BORDER_WIDTH * 2
        return (width, width)

    def do_get_preferred_height(self):
        height = CanvasIcon.do_get_preferred_height(self)[0]
        height += ActivityIcon._BORDER_WIDTH * 2
        return (height, height)

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
                menu_item.show()

            if journal_entries:
                separator = PaletteMenuItemSeparator()
                menu_items.append(separator)
                separator.show()

            for i in range(0, len(menu_items)):
                self.menu_box.pack_start(menu_items[i], True, True, 0)

    def __resume_entry_cb(self, menu_item, entry):
        if entry is not None:
            self.emit('entry-activate', entry)


class CurrentActivityIcon(CanvasIcon):

    def __init__(self):
        CanvasIcon.__init__(self, icon_name='activity-journal',
                            pixel_size=style.STANDARD_ICON_SIZE, cache=True)
        self._home_model = shell.get_model()
        self._home_activity = self._home_model.get_active_activity()

        if self._home_activity is not None:
            self._update()

        self._home_model.connect('active-activity-changed',
                                 self.__active_activity_changed_cb)

        self.connect_after('activate', self.__activate_cb)

    def __activate_cb(self, icon):
        window = self._home_model.get_active_activity().get_window()
        window.activate(Gtk.get_current_event_time())

    def _update(self):
        if self._home_activity is not None:
            self.props.file_name = self._home_activity.get_icon_path()
            self.props.xo_color = self._home_activity.get_icon_color()

            if self._home_activity.is_journal():
                if self._unbusy():
                    GLib.timeout_add(100, self._unbusy)

        self.props.pixel_size = style.STANDARD_ICON_SIZE

        if self.palette is not None:
            self.palette.destroy()
            self.palette = None

    def _unbusy(self):
        if self.get_window():
            import jarabe.desktop.homewindow
            jarabe.desktop.homewindow.get_instance().unbusy()
            return False
        return True

    def create_palette(self):
        if self._home_activity is not None:
            if self._home_activity.is_journal():
                palette = JournalPalette(self._home_activity)
            else:
                palette = CurrentActivityPalette(self._home_activity)
            self.connect_to_palette_pop_events(palette)
        else:
            palette = None
        return palette

    def __active_activity_changed_cb(self, home_model, home_activity):
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

        # This is a workaround to skip the callback for
        # enter-notify-event in the parent class the first time.
        def __enter_notify_event_cb(icon, event):
            self.unset_state_flags(Gtk.StateFlags.PRELIGHT)
            self.disconnect(self._enter_notify_hid)

        self._enter_notify_hid = self.connect('enter-notify-event',
                                              __enter_notify_event_cb)

    def create_palette(self):
        palette = BuddyMenu(get_owner_instance())

        settings = Gio.Settings('org.sugarlabs')
        if settings.get_boolean('show-register'):
            backup_url = settings.get_string('backup-url')

            if not backup_url:
                text = _('Register')
            else:
                text = _('Register again')

            register_menu = PaletteMenuItem(text, 'media-record')
            register_menu.connect('activate', self.__register_activate_cb)
            palette.menu_box.pack_end(register_menu, True, True, 0)
            register_menu.show()

        self.connect_to_palette_pop_events(palette)

        return palette

    def __register_activate_cb(self, menuitem):
        self.emit('register-activate')


class FavoritesSetting(object):

    _DESKTOP_DIR = 'org.sugarlabs.desktop'
    _HOMEVIEWS_KEY = 'homeviews'

    def __init__(self, favorite_view):
        self._favorite_view = int(favorite_view)

        settings = Gio.Settings(self._DESKTOP_DIR)
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

            settings = Gio.Settings(self._DESKTOP_DIR)
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
