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
import math

import gobject
import gtk
import hippo

from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.icon import Icon, CanvasIcon
from sugar.graphics.menuitem import MenuItem
from sugar.profile import get_profile
from sugar import activity

import view.Shell
from view.palettes import JournalPalette
from view.palettes import CurrentActivityPalette, ActivityPalette
from view.home.MyIcon import MyIcon
from model import shellmodel
from model.shellmodel import ShellModel
from hardware import schoolserver
from controlpanel.gui import ControlPanel
from session import get_session_manager

_logger = logging.getLogger('ActivitiesRing')

_ICON_DND_TARGET = ('activity-icon', gtk.TARGET_SAME_WIDGET, 0)

class ActivitiesRing(hippo.Canvas):
    __gtype_name__ = 'SugarActivitiesRing'

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, **kwargs)

        self._box = hippo.CanvasBox()
        self._box.props.background_color = style.COLOR_WHITE.get_int()
        self.set_root(self._box)

        shell_model = shellmodel.get_instance()
        shell_model.connect('notify::state', self._shell_state_changed_cb)

        self._my_icon = _MyIcon(style.XLARGE_ICON_SIZE)
        self._box.append(self._my_icon, hippo.PACK_FIXED)

        self._current_activity = CurrentActivityIcon()
        self._box.append(self._current_activity, hippo.PACK_FIXED)

        self._layout = RingLayout()
        self._box.set_layout(self._layout)

        registry = activity.get_registry()
        registry.get_activities_async(reply_handler=self._get_activities_cb)
        registry.connect('activity-added', self.__activity_added_cb)
        registry.connect('activity-removed', self.__activity_removed_cb)
        registry.connect('activity-changed', self.__activity_changed_cb)

        # DND stuff
        self._pressed_button = None
        self._press_start_x = None
        self._press_start_y = None
        self._last_clicked_icon = None

        self.drag_source_set(0, [], 0)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK |
                        gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.connect('motion-notify-event', self.__motion_notify_event_cb)
        self.connect('button-press-event', self.__button_press_event_cb)
        self.connect('drag-begin', self.__drag_begin_cb)

        self.drag_dest_set(0, [], 0)
        self.connect('drag-motion', self.__drag_motion_cb)
        self.connect('drag-drop', self.__drag_drop_cb)
        self.connect('drag-data-received', self.__drag_data_received_cb)

    def _add_activity(self, activity_info):
        icon = ActivityIcon(activity_info)
        self._layout.append(icon)

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
        if activity_info.bundle_id == "org.laptop.JournalActivity":
            return
        icon = self._find_activity_icon(activity_info.bundle_id,
                activity_info.version)
        if icon is not None and not activity_info.favorite:
            self._box.remove(icon)
        elif icon is None and activity_info.favorite:
            self._add_activity(activity_info)

    def _shell_state_changed_cb(self, model, pspec):
        # FIXME implement this
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            pass

    def do_size_allocate(self, allocation):
        hippo.Canvas.do_size_allocate(self, allocation)
        
        width = allocation.width        
        height = allocation.height

        [my_icon_width, my_icon_height] = self._my_icon.get_allocation()
        x = (width - my_icon_width) / 2
        y = (height - my_icon_height - style.GRID_CELL_SIZE) / 2
        self._box.set_position(self._my_icon, x, y)

        [icon_width, icon_height] = self._current_activity.get_allocation()
        x = (width - icon_width) / 2
        y = (height + my_icon_height + style.DEFAULT_PADDING \
                 - style.GRID_CELL_SIZE) / 2
        self._box.set_position(self._current_activity, x, y)

    def enable_xo_palette(self):
        self._my_icon.enable_palette()

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

class ActivityIcon(CanvasIcon):
    def __init__(self, activity_info):
        CanvasIcon.__init__(self, cache=True, file_name=activity_info.icon)
        self._activity_info = activity_info
        self.connect('hovering-changed', self.__hovering_changed_event_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

    def create_palette(self):
        return ActivityPalette(self._activity_info)

    def __hovering_changed_event_cb(self, icon, event):
        if event:
            self.props.xo_color = get_profile().color
        else:
            self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

    def __button_release_event_cb(self, icon, event):
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
        _logger.debug('CurrentActivityIcon._update')
        self.props.file_name = home_activity.get_icon_path()
        self.props.xo_color = home_activity.get_icon_color()
        self.props.size = style.STANDARD_ICON_SIZE

        if home_activity.get_type() == "org.laptop.JournalActivity":
            palette = JournalPalette(home_activity)
        else:
            palette = CurrentActivityPalette(home_activity)
        self.set_palette(palette)

    def __active_activity_changed_cb(self, home_model, home_activity):
        self._update(home_activity)

_MINIMUM_RADIUS = style.XLARGE_ICON_SIZE / 2 + style.DEFAULT_SPACING + \
        style.STANDARD_ICON_SIZE * 2
_MAXIMUM_RADIUS = (gtk.gdk.screen_height() - style.GRID_CELL_SIZE) / 2 - \
        style.STANDARD_ICON_SIZE - style.DEFAULT_SPACING

class RingLayout(gobject.GObject, hippo.CanvasLayout):
    __gtype_name__ = 'SugarRingLayout'

    def __init__(self):
        gobject.GObject.__init__(self)
        self._box = None
        self._fixed_positions = {}

    def do_set_box(self, box):
        self._box = box

    def do_get_height_request(self, for_width):
        return 0, gtk.gdk.screen_height() - style.GRID_CELL_SIZE

    def do_get_width_request(self):
        return 0, gtk.gdk.screen_width()

    def _calculate_radius_and_icon_size(self, children_count):
        angle = 2 * math.pi / children_count

        # what's the radius required without downscaling?
        distance = style.STANDARD_ICON_SIZE + style.DEFAULT_SPACING
        icon_size = style.STANDARD_ICON_SIZE
        
        if children_count == 1:
            radius = 0
        else:
            radius = math.sqrt(distance ** 2 /
                    (math.sin(angle) ** 2 + (math.cos(angle) - 1) ** 2))
        
        if radius < _MINIMUM_RADIUS:
            # we can upscale, if we want
            icon_size += style.STANDARD_ICON_SIZE * \
                    (0.5 * (_MINIMUM_RADIUS - radius) / _MINIMUM_RADIUS)
            radius = _MINIMUM_RADIUS
        elif radius > _MAXIMUM_RADIUS:
            radius = _MAXIMUM_RADIUS
            # need to downscale. what's the icon size required?
            distance = math.sqrt((radius * math.sin(angle)) ** 2 + \
                    (radius * (math.cos(angle) - 1)) ** 2)
            icon_size = distance - style.DEFAULT_SPACING
        
        return radius, icon_size

    def _calculate_position(self, radius, icon_size, index, children_count):
        width, height = self._box.get_allocation()
        angle = index * (2 * math.pi / children_count) - math.pi / 2
        x = radius * math.cos(angle) + (width - icon_size) / 2
        y = radius * math.sin(angle) + (height - icon_size -
                                        style.GRID_CELL_SIZE) / 2
        return x, y

    def _get_children_in_ring(self):
        children = self._box.get_layout_children()
        width, height = self._box.get_allocation()
        children_in_ring = []
        for child in children:
            if child.item in self._fixed_positions:
                x, y = self._fixed_positions[child.item]
                distance_to_center = math.hypot(x - width / 2, y - height / 2)
                # TODO at what distance should we consider a child inside the ring?
            else:
                children_in_ring.append(child)

        return children_in_ring

    def _update_icon_sizes(self):
        children_in_ring = self._get_children_in_ring()
        if children_in_ring:
            radius_, icon_size = \
                    self._calculate_radius_and_icon_size(len(children_in_ring))

            for n in range(len(children_in_ring)):
                child = children_in_ring[n]
                child.item.props.size = icon_size

        for child in self._box.get_layout_children():
            if child not in children_in_ring:
                child.item.props.size = style.STANDARD_ICON_SIZE

    def _compare_activities(self, icon_a, icon_b):
        if hasattr(icon_a, 'installation_time') and \
                hasattr(icon_b, 'installation_time'):
            return icon_b.installation_time - icon_a.installation_time
        else:
            return 0

    def append(self, icon):
        self._box.insert_sorted(icon, 0, self._compare_activities)
        relative_x, relative_y = icon.fixed_position
        if relative_x >= 0 and relative_y >= 0:
            width = gtk.gdk.screen_width()
            height = gtk.gdk.screen_height() - style.GRID_CELL_SIZE
            self._fixed_positions[icon] = (relative_x * 1000 / width,
                                           relative_y * 1000 / height)
        self._update_icon_sizes()

    def remove(self, icon):
        del self._fixed_positions[icon]
        self._box.remove(icon)
        self._update_icon_sizes()

    def move_icon(self, icon, x, y):
        if icon not in self._box.get_children():
            raise ValueError('Child not in box.')

        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height() - style.GRID_CELL_SIZE
        registry = activity.get_registry()
        registry.set_activity_position(icon.get_bundle_id(), icon.get_version(),
                                       x * width / 1000, y * height / 1000)

        self._fixed_positions[icon] = (x, y)
        self._box.emit_request_changed()

    def do_allocate(self, x, y, width, height, req_width, req_height,
                    origin_changed):
        children_in_ring = self._get_children_in_ring()
        if children_in_ring:
            radius, icon_size = \
                    self._calculate_radius_and_icon_size(len(children_in_ring))

            for n in range(len(children_in_ring)):
                child = children_in_ring[n]

                x, y = self._calculate_position(radius, icon_size, n,
                                                len(children_in_ring))

                # We need to always get requests to not confuse hippo
                min_w_, child_width = child.get_width_request()
                min_h_, child_height = child.get_height_request(child_width)

                child.allocate(int(x), int(y), child_width, child_height,
                               origin_changed)

        for child in self._box.get_layout_children():
            if child in children_in_ring:
                continue

            # We need to always get requests to not confuse hippo
            min_w_, child_width = child.get_width_request()
            min_h_, child_height = child.get_height_request(child_width)

            x, y = self._fixed_positions[child.item]

            child.allocate(int(x), int(y), child_width, child_height,
                            origin_changed)

class _MyIcon(MyIcon):
    def __init__(self, scale):
        MyIcon.__init__(self, scale)

        self._power_manager = None
        self._profile = get_profile()

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
            item = MenuItem(_('Register'), 'media-record')
            item.connect('activate', self._register_activate_cb)
            palette.menu.append(item)
            item.show()
 
        self.set_palette(palette)

    def _reboot_activate_cb(self, menuitem):
        model = shellmodel.get_instance()
        model.props.state = ShellModel.STATE_SHUTDOWN

        session_manager = get_session_manager()
        session_manager.shutdown()

    def _shutdown_activate_cb(self, menuitem):
        model = shellmodel.get_instance()
        model.props.state = ShellModel.STATE_SHUTDOWN

        session_manager = get_session_manager()
        session_manager.shutdown()

    def _register_activate_cb(self, menuitem):
        schoolserver.register_laptop()
        if self._profile.is_registered():
            self.get_palette().menu.remove(menuitem)

    def get_toplevel(self):
        return hippo.get_canvas_for_item(self).get_toplevel()

    def __controlpanel_activate_cb(self, menuitem):
        panel = ControlPanel()
        panel.set_transient_for(self.get_toplevel())
        panel.show()

    def _response_cb(self, widget, response_id):
        if response_id == gtk.RESPONSE_OK:            
            widget.destroy()
