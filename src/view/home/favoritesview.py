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

import gobject
import gtk
import hippo

from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.icon import Icon, CanvasIcon
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.alert import Alert
from sugar.profile import get_profile
from sugar import activity

import view.Shell
from view.palettes import JournalPalette
from view.palettes import CurrentActivityPalette, ActivityPalette
from view.home.MyIcon import MyIcon
from view.home import favoriteslayout
from model import shellmodel
from model.shellmodel import ShellModel
from hardware import schoolserver
from hardware.schoolserver import RegisterError
from controlpanel.gui import ControlPanel
from session import get_session_manager

_logger = logging.getLogger('FavoritesView')

_ICON_DND_TARGET = ('activity-icon', gtk.TARGET_SAME_WIDGET, 0)

RING_LAYOUT = 0
RANDOM_LAYOUT = 1

_LAYOUT_MAP = {RING_LAYOUT: favoriteslayout.RingLayout,
               RANDOM_LAYOUT: favoriteslayout.RandomLayout}

class FavoritesView(hippo.Canvas):
    __gtype_name__ = 'SugarFavoritesView'

    __gsignals__ = {
        'erase-activated' : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([str])),
    }

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, **kwargs)

        # DND stuff
        self._pressed_button = None
        self._press_start_x = None
        self._press_start_y = None
        self._last_clicked_icon = None

        self._box = hippo.CanvasBox()
        self._box.props.background_color = style.COLOR_WHITE.get_int()
        self.set_root(self._box)

        self._my_icon = None
        self._current_activity = None
        self._layout = None
        self._alert = None

        registry = activity.get_registry()
        registry.connect('activity-added', self.__activity_added_cb)
        registry.connect('activity-removed', self.__activity_removed_cb)
        registry.connect('activity-changed', self.__activity_changed_cb)

        # More DND stuff
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK |
                        gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.connect('motion-notify-event', self.__motion_notify_event_cb)
        self.connect('button-press-event', self.__button_press_event_cb)
        self.connect('drag-begin', self.__drag_begin_cb)
        self.connect('drag-motion', self.__drag_motion_cb)
        self.connect('drag-drop', self.__drag_drop_cb)
        self.connect('drag-data-received', self.__drag_data_received_cb)

    def _add_activity(self, activity_info):
        icon = ActivityIcon(activity_info)
        icon.connect('erase-activated', self.__erase_activated_cb)
        icon.props.size = style.STANDARD_ICON_SIZE
        self._layout.append(icon)

    def __erase_activated_cb(self, activity_icon, bundle_id):
        self.emit('erase-activated', bundle_id)

    def _get_activities_cb(self, activity_list):
        for info in activity_list:
            if info.favorite and info.bundle_id != "org.laptop.JournalActivity":
                self._add_activity(info)

    def __activity_added_cb(self, activity_registry, activity_info):
        if activity_info.favorite and \
                activity_info.bundle_id != "org.laptop.JournalActivity":
            self._add_activity(activity_info)

    def _find_activity_icon(self, bundle_id, version):
        for icon in self._box.get_children():
            if isinstance(icon, ActivityIcon) and \
                    icon.bundle_id == bundle_id and icon.version == version:
                return icon
        return None

    def __activity_removed_cb(self, activity_registry, activity_info):
        icon = self._find_activity_icon(activity_info.bundle_id,
                activity_info.version)
        if icon is not None:
            self._layout.remove(icon)

    def __activity_changed_cb(self, activity_registry, activity_info):
        if activity_info.bundle_id == 'org.laptop.JournalActivity':
            return
        icon = self._find_activity_icon(activity_info.bundle_id,
                activity_info.version)
        if icon is not None:
            self._box.remove(icon)
        if activity_info.favorite:
            self._add_activity(activity_info)

    def do_size_allocate(self, allocation):
        width = allocation.width        
        height = allocation.height

        min_w_, my_icon_width = self._my_icon.get_width_request()
        min_h_, my_icon_height = self._my_icon.get_height_request(my_icon_width)
        x = (width - my_icon_width) / 2
        y = (height - my_icon_height - style.GRID_CELL_SIZE) / 2
        self._layout.move_icon(self._my_icon, x, y, locked=True)

        min_w_, icon_width = self._current_activity.get_width_request()
        min_h_, icon_height = \
                self._current_activity.get_height_request(icon_width)
        x = (width - icon_width) / 2
        y = (height - my_icon_height - style.GRID_CELL_SIZE) / 2 + \
                my_icon_height + style.DEFAULT_PADDING
        self._layout.move_icon(self._current_activity, x, y, locked=True)

        hippo.Canvas.do_size_allocate(self, allocation)

    def enable_xo_palette(self):
        self._my_icon.enable_palette()
        if self._my_icon.register_menu is not None:
            self._my_icon.register_menu.connect('activate', 
                                                self.__register_activate_cb)

    # TODO: Dnd methods. This should be merged somehow inside hippo-canvas.
    def __button_press_event_cb(self, widget, event):
        if event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
            self._last_clicked_icon = self._get_icon_at_coords(event.x, event.y)
            if self._last_clicked_icon is not None:
                self._pressed_button = event.button
                self._press_start_x = event.x
                self._press_start_y = event.y

        return False

    def _get_icon_at_coords(self, x, y):
        for icon in self._box.get_children():
            icon_x, icon_y = icon.get_context().translate_to_widget(icon)
            icon_width, icon_height = icon.get_allocation()

            if (x >= icon_x ) and (x <= icon_x + icon_width) and \
                    (y >= icon_y ) and (y <= icon_y + icon_height) and \
                    isinstance(icon, ActivityIcon):
                return icon
        return None

    def __motion_notify_event_cb(self, widget, event):
        if not self._pressed_button:
            return False
        
        # if the mouse button is not pressed, no drag should occurr
        if not event.state & gtk.gdk.BUTTON1_MASK:
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
            context_ = widget.drag_begin([_ICON_DND_TARGET],
                                         gtk.gdk.ACTION_MOVE,
                                         1,
                                         event)
        return False

    def __drag_begin_cb(self, widget, context):
        icon_file_name = self._last_clicked_icon.props.file_name
        # TODO: we should get the pixbuf from the widget, so it has colors, etc
        pixbuf = gtk.gdk.pixbuf_new_from_file(icon_file_name)
        
        hot_spot = style.zoom(10)
        context.set_icon_pixbuf(pixbuf, hot_spot, hot_spot)

    def __drag_motion_cb(self, widget, context, x, y, time):
        if self._last_clicked_icon is not None:
            context.drag_status(context.suggested_action, time)
            return True
        else:
            return False

    def __drag_drop_cb(self, widget, context, x, y, time):
        if self._last_clicked_icon is not None:
            self.drag_get_data(context, _ICON_DND_TARGET[0])

            self._layout.move_icon(self._last_clicked_icon, x, y)

            self._pressed_button = None
            self._press_start_x = None
            self._press_start_y = None
            self._last_clicked_icon = None

            return True
        else:
            return False

    def __drag_data_received_cb(self, widget, context, x, y, selection_data,
                                info, time):
        context.drop_finish(success=True, time=time)

    def _set_layout(self, layout):
        if layout not in _LAYOUT_MAP:
            raise ValueError('Unknown favorites layout: %r' % layout)
        if type(self._layout) != _LAYOUT_MAP[layout]:
            self._box.clear()
            self._layout = _LAYOUT_MAP[layout]()
            self._box.set_layout(self._layout)

            self._my_icon = _MyIcon(style.XLARGE_ICON_SIZE)
            self._layout.append(self._my_icon, locked=True)

            self._current_activity = CurrentActivityIcon()
            self._layout.append(self._current_activity, locked=True)

            registry = activity.get_registry()
            registry.get_activities_async(reply_handler=self._get_activities_cb)

            if self._layout.allow_dnd():
                self.drag_source_set(0, [], 0)
                self.drag_dest_set(0, [], 0)
            else:
                self.drag_source_unset()
                self.drag_dest_unset()

    layout = property(None, _set_layout)

    def add_alert(self, alert):
        if self._alert is not None:
            self.remove_alert()
        alert.set_size_request(gtk.gdk.screen_width(), -1)
        self._alert = hippo.CanvasWidget(widget=alert)
        self._box.append(self._alert, hippo.PACK_FIXED)

    def remove_alert(self):
        self._box.remove(self._alert)
        self._alert = None

    def __register_activate_cb(self, menuitem):
        alert = Alert()
        try:
            schoolserver.register_laptop()
        except RegisterError, e:
            alert.props.title = _('Registration Failed')
            alert.props.msg = _('%s') % e
        else:    
            alert.props.title = _('Registration Successful')
            alert.props.msg = _('You are now registered with your school server.') 
            palette = self._my_icon.get_palette()
            palette.menu.remove(menuitem)

        ok_icon = Icon(icon_name='dialog-ok')
        alert.add_button(gtk.RESPONSE_OK, _('Ok'), ok_icon)

        self.add_alert(alert)
        alert.connect('response', self.__register_alert_response_cb)            
            
    def __register_alert_response_cb(self, alert, response_id):
        self.remove_alert()

class ActivityIcon(CanvasIcon):
    __gtype_name__ = 'SugarFavoriteActivityIcon'

    __gsignals__ = {
        'erase-activated' : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([str])),
    }

    def __init__(self, activity_info):
        CanvasIcon.__init__(self, cache=True, file_name=activity_info.icon)
        self._activity_info = activity_info
        self._uncolor()
        self.connect('hovering-changed', self.__hovering_changed_event_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

    def create_palette(self):
        palette = ActivityPalette(self._activity_info)
        palette.connect('erase-activated', self.__erase_activated_cb)
        return palette

    def __erase_activated_cb(self, palette):
        self.emit('erase-activated', self._activity_info.bundle_id)

    def _color(self):
        self.props.xo_color = get_profile().color

    def _uncolor(self):
        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

    def __hovering_changed_event_cb(self, icon, hovering):
        if hovering:
            self._color()
        else:
            self._uncolor()

    def __button_release_event_cb(self, icon, event):
        self.palette.popdown(immediate=True)
        self._uncolor()
        view.Shell.get_instance().start_activity(self._activity_info.bundle_id)

    def get_bundle_id(self):
        return self._activity_info.bundle_id
    bundle_id = property(get_bundle_id, None)

    def get_version(self):
        return self._activity_info.version
    version = property(get_version, None)

    def _get_installation_time(self):
        return self._activity_info.installation_time
    installation_time = property(_get_installation_time, None)

    def _get_fixed_position(self):
        return self._activity_info.position
    fixed_position = property(_get_fixed_position, None)

class CurrentActivityIcon(CanvasIcon, hippo.CanvasItem):
    def __init__(self):
        CanvasIcon.__init__(self, cache=True)
        self._home_model = shellmodel.get_instance().get_home()

        if self._home_model.get_active_activity() is not None:
            self._update(self._home_model.get_active_activity())

        self._home_model.connect('active-activity-changed',
                                 self.__active_activity_changed_cb)

        self.connect('button-release-event', self.__button_release_event_cb)

    def __button_release_event_cb(self, icon, event):
        self._home_model.get_active_activity().get_window().activate(1)

    def _update(self, home_activity):
        self.props.file_name = home_activity.get_icon_path()
        self.props.xo_color = home_activity.get_icon_color()
        self.props.size = style.STANDARD_ICON_SIZE

        if self.palette is not None:
            self.palette.destroy()
            self.palette = None

        if home_activity.is_journal():
            palette = JournalPalette(home_activity)
        else:
            palette = CurrentActivityPalette(home_activity)
        self.set_palette(palette)

    def __active_activity_changed_cb(self, home_model, home_activity):
        self._update(home_activity)

class _MyIcon(MyIcon):
    def __init__(self, scale):
        MyIcon.__init__(self, scale)

        self._power_manager = None
        self._profile = get_profile()
        self.register_menu = None

    def enable_palette(self):
        palette_icon = Icon(icon_name='computer-xo', 
                            icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR,
                            xo_color=self._profile.color)
        palette = Palette(self._profile.nick_name,
                          #secondary_text='Sample secondary label',
                          icon=palette_icon)

        item = MenuItem(_('Control Panel'))

        icon = Icon(icon_name='computer-xo', icon_size=gtk.ICON_SIZE_MENU,
                xo_color=self._profile.color)
        item.set_image(icon)
        icon.show()

        item.connect('activate', self.__controlpanel_activate_cb)
        palette.menu.append(item)
        item.show()

        item = MenuItem(_('Restart'), 'system-restart')
        item.connect('activate', self._reboot_activate_cb)
        palette.menu.append(item)
        item.show()

        item = MenuItem(_('Shutdown'), 'system-shutdown')
        item.connect('activate', self._shutdown_activate_cb)
        palette.menu.append(item)
        item.show()

        if not self._profile.is_registered():
            self.register_menu = MenuItem(_('Register'), 'media-record')
            palette.menu.append(self.register_menu)
            self.register_menu.show()
 
        self.set_palette(palette)

    def _reboot_activate_cb(self, menuitem):
        session_manager = get_session_manager()
        session_manager.reboot()

    def _shutdown_activate_cb(self, menuitem):
        session_manager = get_session_manager()
        session_manager.shutdown()
        
    def get_toplevel(self):
        return hippo.get_canvas_for_item(self).get_toplevel()

    def __controlpanel_activate_cb(self, menuitem):
        panel = ControlPanel()
        panel.set_transient_for(self.get_toplevel())
        panel.show()
