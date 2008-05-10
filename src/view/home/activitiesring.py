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

import os
import logging
import signal
from gettext import gettext as _
import re
import math

import gobject
import gtk
import hippo
import dbus

from hardware import hardwaremanager
from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.icon import Icon, CanvasIcon
from sugar.graphics.menuitem import MenuItem
from sugar.profile import get_profile
from sugar import env
from sugar import activity

import view.Shell
from view.palettes import JournalPalette
from view.palettes import CurrentActivityPalette, ActivityPalette
from view.home.MyIcon import MyIcon
from model import shellmodel
from model.shellmodel import ShellModel
from hardware import schoolserver
from controlpanel.gui import ControlPanel

_logger = logging.getLogger('ActivitiesRing')

class ActivitiesRing(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarActivitiesRing'

    def __init__(self):
        hippo.CanvasBox.__init__(self, 
                                 background_color=style.COLOR_WHITE.get_int())

        shell_model = shellmodel.get_instance()
        shell_model.connect('notify::state', self._shell_state_changed_cb)

        self._my_icon = _MyIcon(style.XLARGE_ICON_SIZE)
        self.append(self._my_icon, hippo.PACK_FIXED)

        self._current_activity = CurrentActivityIcon()
        self.append(self._current_activity, hippo.PACK_FIXED)

        self.set_layout(RingLayout())

        registry = activity.get_registry()
        registry.get_activities_async(reply_handler=self._get_activities_cb)
        registry.connect('activity-added', self.__activity_added_cb)
        registry.connect('activity-removed', self.__activity_removed_cb)
        registry.connect('activity-changed', self.__activity_changed_cb)

    def _get_activities_cb(self, activity_list):
        for info in activity_list:
            if info.favorite and info.bundle_id != "org.laptop.JournalActivity":
                self.append(ActivityIcon(info))

    def __activity_added_cb(self, activity_registry, activity_info):
        if activity_info.favorite and \
                activity_info.bundle_id != "org.laptop.JournalActivity":
            self.append(ActivityIcon(activity_info))

    def _find_activity_icon(self, bundle_id, version):
        for icon in self.get_children():
            if isinstance(icon, ActivityIcon) and \
                    icon.bundle_id == bundle_id and icon.version == version:
                return icon
        return None

    def __activity_removed_cb(self, activity_registry, activity_info):
        icon = self._find_activity_icon(activity_info.bundle_id,
                activity_info.version)
        if icon is not None:
            self.remove(icon)

    def __activity_changed_cb(self, activity_registry, activity_info):
        if activity_info.bundle_id == "org.laptop.JournalActivity":
            return
        icon = self._find_activity_icon(activity_info.bundle_id,
                activity_info.version)
        if icon is not None and not activity_info.favorite:
            self.remove(icon)
        elif icon is None and activity_info.favorite:
            self.append(ActivityIcon(activity_info))

    def _shell_state_changed_cb(self, model, pspec):
        # FIXME implement this
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            pass

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        [my_icon_width, my_icon_height] = self._my_icon.get_allocation()
        x = (width - my_icon_width) / 2
        y = (height - my_icon_height - style.GRID_CELL_SIZE) / 2
        self.set_position(self._my_icon, x, y)

        [icon_width, icon_height] = self._current_activity.get_allocation()
        x = (width - icon_width) / 2
        y = (height + my_icon_height + style.DEFAULT_PADDING \
                 - style.GRID_CELL_SIZE) / 2
        self.set_position(self._current_activity, x, y)

    def enable_xo_palette(self):
        self._my_icon.enable_palette()

class ActivityIcon(CanvasIcon):
    def __init__(self, activity_info):
        CanvasIcon.__init__(self, cache=True, file_name=activity_info.icon)
        self._activity_info = activity_info
        self.set_palette(ActivityPalette(activity_info))
        self.connect('hovering-changed', self.__hovering_changed_event_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

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


class CurrentActivityIcon(CanvasIcon, hippo.CanvasItem):
    def __init__(self):
        CanvasIcon.__init__(self, cache=True)
        self._home_model = shellmodel.get_instance().get_home()

        if self._home_model.get_pending_activity() is not None:
            self._update(self._home_model.get_pending_activity())

        self._home_model.connect('pending-activity-changed',
                self.__pending_activity_changed_cb)

        self.connect('button-release-event', self.__button_release_event_cb)

    def __button_release_event_cb(self, icon, event):
        self._home_model.get_pending_activity().get_window().activate(1)

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

    def __pending_activity_changed_cb(self, home_model, home_activity):
        self._update(home_activity)

class RingLayout(gobject.GObject, hippo.CanvasLayout):
    __gtype_name__ = 'SugarRingLayout'
    def __init__(self):
        gobject.GObject.__init__(self)
        self._box = None

    def do_set_box(self, box):
        self._box = box

    def do_get_height_request(self, for_width):
        return 0, gtk.gdk.screen_height() - style.GRID_CELL_SIZE

    def do_get_width_request(self):
        return 0, gtk.gdk.screen_width()

    def _calculate_radius_and_icon_size(self, children_count):
        minimum_radius = style.XLARGE_ICON_SIZE / 2 + style.DEFAULT_SPACING + \
                style.STANDARD_ICON_SIZE * 2
        maximum_radius = (gtk.gdk.screen_height() - style.GRID_CELL_SIZE) \
                / 2 - style.STANDARD_ICON_SIZE - style.DEFAULT_SPACING
        angle = 2 * math.pi / children_count

        _logger.debug('minimum_radius %r maximum_radius %r angle %r' % \
                (minimum_radius, maximum_radius, angle))

        # what's the radius required without downscaling?
        distance = style.STANDARD_ICON_SIZE + style.DEFAULT_SPACING
        icon_size = style.STANDARD_ICON_SIZE
        
        if children_count == 1:
            radius = 0
        else:
            radius = math.sqrt(distance ** 2 /
                    (math.sin(angle) ** 2 + (math.cos(angle) - 1) ** 2))

        _logger.debug('radius 1 %r' % radius)
        
        if radius < minimum_radius:
            # we can upscale, if we want
            icon_size += style.STANDARD_ICON_SIZE * \
                    (0.5 * (minimum_radius - radius)/minimum_radius)
            radius = minimum_radius
        elif radius > maximum_radius:
            radius = maximum_radius
            # need to downscale. what's the icon size required?
            distance = math.sqrt((radius * math.sin(angle)) ** 2 + \
                    (radius * (math.cos(angle) - 1)) ** 2)
            icon_size = distance - style.DEFAULT_SPACING

        _logger.debug('radius 2 %r icon_size %r' % (radius, icon_size))
        
        return radius, icon_size

    def _calculate_position(self, radius, icon_size, index, children_count):
        width, height = self._box.get_allocation()
        angle = index * (2 * math.pi / children_count) - math.pi/2
        x = radius * math.cos(angle) + (width - icon_size) / 2
        y = radius * math.sin(angle) + (height - icon_size -
                                        style.GRID_CELL_SIZE) / 2
        return x, y

    def do_allocate(self, x, y, width, height, req_width, req_height,
                    origin_changed):
        _logger.debug('RingLayout.do_allocate: %r %r %r %r %r %r %r' % (x, y,
                width, height, req_width, req_height, origin_changed))

        children = self._box.get_layout_children()
        if not children:
            return

        radius, icon_size = self._calculate_radius_and_icon_size(len(children))

        for n in range(len(children)):
            child = children[n]
            # TODO: We get here a glib warning and I don't know why.
            child.item.props.size = icon_size

            x, y = self._calculate_position(radius, icon_size, n, len(children))

            # We need to always get requests to not confuse hippo
            min_w, child_width = child.get_width_request()
            min_h, child_height = child.get_height_request(child_width)

            child.allocate(int(x),
                           int(y),
                           child_width,
                           child_height,
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

        pm = self._get_power_manager()

        hw_manager = hardwaremanager.get_manager()
        hw_manager.shutdown()

        if env.is_emulator():
            self._close_emulator()
        else:
            pm.Reboot()

    def _shutdown_activate_cb(self, menuitem):
        model = shellmodel.get_instance()
        model.props.state = ShellModel.STATE_SHUTDOWN

        pm = self._get_power_manager()

        hw_manager = hardwaremanager.get_manager()
        hw_manager.shutdown()

        if env.is_emulator():
            self._close_emulator()
        else:
            pm.Shutdown()

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

    def _close_emulator(self):
        if os.environ.has_key('SUGAR_EMULATOR_PID'):
            pid = int(os.environ['SUGAR_EMULATOR_PID'])
            os.kill(pid, signal.SIGTERM)

    def _get_power_manager(self):
        if self._power_manager is None:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.Hal', 
                                '/org/freedesktop/Hal/devices/computer')
            self._power_manager = dbus.Interface(proxy, \
                            'org.freedesktop.Hal.Device.SystemPowerManagement') 

        return self._power_manager

