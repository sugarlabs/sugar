# Copyright (C) 2006-2007 Red Hat, Inc.
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

import colorsys
from gettext import gettext as _
import math

import hippo
import gobject
import gtk

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.palette import Palette
from sugar.graphics import style
from sugar.graphics import xocolor
from sugar import profile

# TODO: rgb_to_html and html_to_rgb are useful elsewhere 
#       we should put this in a common module 
def rgb_to_html(r, g, b):
    """ (r, g, b) tuple (in float format) -> #RRGGBB """
    return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))

def html_to_rgb(html_color):
    """ #RRGGBB -> (r, g, b) tuple (in float format) """
    html_color = html_color.strip()
    if html_color[0] == '#':
        html_color = html_color[1:]
    if len(html_color) != 6:
        raise ValueError, "input #%s is not in #RRGGBB format" % html_color
    r, g, b = html_color[:2], html_color[2:4], html_color[4:]
    r, g, b = [int(n, 16) for n in (r, g, b)]
    r, g, b = (r / 255.0, g / 255.0, b / 255.0)
    return (r, g, b)

class ActivityIcon(CanvasIcon):
    _INTERVAL = 250

    __gsignals__ = {
        'resume': (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, ([])),
        'stop': (gobject.SIGNAL_RUN_FIRST,
                 gobject.TYPE_NONE, ([]))
    }

    def __init__(self, activity):
        icon_name = activity.get_icon_name()
        self._orig_color = activity.get_icon_color()
        self._icon_colors = self._compute_icon_colors()

        self._direction = 0
        self._level_max = len(self._icon_colors) - 1
        self._level = self._level_max
        color = self._icon_colors[self._level]

        CanvasIcon.__init__(self, icon_name=icon_name, xo_color=color,
                            size=style.MEDIUM_ICON_SIZE, cache=True)

        self._activity = activity
        self._pulse_id = 0

        palette = Palette(_('Starting...'))
        self.set_palette(palette)

        activity.connect('notify::launching', self._launching_changed_cb)
        if activity.props.launching:
            self._start_pulsing()
        else:
            self._setup_palette()

    def _setup_palette(self):
        palette = self.get_palette()

        palette.set_primary_text(self._activity.get_title())

        resume_menu_item = gtk.MenuItem(_('Resume'))
        resume_menu_item.connect('activate', self._resume_activate_cb)
        palette.menu.append(resume_menu_item)
        resume_menu_item.show()

        # FIXME: kludge
        if self._activity.get_type() != "org.laptop.JournalActivity":
            stop_menu_item = gtk.MenuItem(_('Stop'))
            stop_menu_item.connect('activate', self._stop_activate_cb)
            palette.menu.append(stop_menu_item)
            stop_menu_item.show()

    def _launching_changed_cb(self, activity, pspec):
        if activity.props.launching:
            self._start_pulsing()
        else:
            self._stop_pulsing()
        self._setup_palette()

    def __del__(self):
        self._cleanup()

    def _cleanup(self):
        if self._pulse_id:
            gobject.source_remove(self._pulse_id)
        self._pulse_id = 0
        # dispose of all rendered icons from launch feedback
        self._clear_buffers()

    def _compute_icon_colors(self):
        _LEVEL_MAX = 1.6
        _LEVEL_STEP = 0.16
        _LEVEL_MIN = 0.0
        icon_colors = {}
        level = _LEVEL_MIN
        for i in range(0, int(_LEVEL_MAX / _LEVEL_STEP)):
            icon_colors[i] = self._get_icon_color_for_level(level)
            level += _LEVEL_STEP
        return icon_colors

    def _get_icon_color_for_level(self, level):
        factor = math.sin(level)
        h, s, v = colorsys.rgb_to_hsv(*html_to_rgb(self._orig_color.get_fill_color()))
        new_fill = rgb_to_html(*colorsys.hsv_to_rgb(h, s * factor, v))
        h, s, v = colorsys.rgb_to_hsv(*html_to_rgb(self._orig_color.get_stroke_color()))
        new_stroke = rgb_to_html(*colorsys.hsv_to_rgb(h, s * factor, v))
        return xocolor.XoColor("%s,%s" % (new_stroke, new_fill))

    def _pulse_cb(self):
        if self._direction == 1:
            self._level += 1
            if self._level > self._level_max:
                self._direction = 0
                self._level = self._level_max
        elif self._direction == 0:
            self._level -= 1
            if self._level <= 0:
                self._direction = 1
                self._level = 0

        self.props.xo_color = self._icon_colors[self._level]
        self.emit_paint_needed(0, 0, -1, -1)
        return True

    def _start_pulsing(self):
        if self._pulse_id:
            return

        self._pulse_id = gobject.timeout_add(self._INTERVAL, self._pulse_cb)

    def _stop_pulsing(self):
        if not self._pulse_id:
            return

        self._cleanup()
        self._level = 100.0
        self.props.xo_color = self._orig_color

        # Force the donut to redraw now that we know how much memory
        # the activity is using.
        self.emit_request_changed()

    def _resume_activate_cb(self, menuitem):
        self.emit('resume')

    def _stop_activate_cb(self, menuitem):
        self.emit('stop')

    def get_activity(self):
        return self._activity

class ActivitiesDonut(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarActivitiesDonut'
    def __init__(self, shell, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)

        self._activities = []
        self._shell = shell
        self._angles = []

        self._model = shell.get_model().get_home()
        self._model.connect('activity-added', self._activity_added_cb)
        self._model.connect('activity-removed', self._activity_removed_cb)
        self._model.connect('active-activity-changed', self._activity_changed_cb)

        self.connect('button-release-event', self._button_release_event_cb)

    def _get_icon_from_activity(self, activity):
        for icon in self._activities:
            if icon.get_activity().equals(activity):
                return icon

    def _activity_added_cb(self, model, activity):
        self._add_activity(activity)

    def _activity_removed_cb(self, model, activity):
        self._remove_activity(activity)
    
    def _activity_changed_cb(self, model, activity):
        self.emit_paint_needed(0, 0, -1, -1)

    def _remove_activity(self, activity):
        icon = self._get_icon_from_activity(activity)
        if icon:
            self.remove(icon)
            icon._cleanup()
        self._activities.remove(icon)

    def _add_activity(self, activity):
        icon = ActivityIcon(activity)
        icon.connect('resume', self._activity_icon_resumed_cb)
        icon.connect('stop', self._activity_icon_stop_cb)
        self.append(icon, hippo.PACK_FIXED)

        self._activities.append(icon)

        self.emit_paint_needed(0, 0, -1, -1)

    def _activity_icon_resumed_cb(self, icon):
        activity = icon.get_activity()
        activity_host = self._shell.get_activity(activity.get_activity_id())
        if activity_host:
            activity_host.present()
        else:
            logging.error("Could not find ActivityHost for activity %s" %
                          activity.get_activity_id())

    def _activity_icon_stop_cb(self, icon):
        activity = icon.get_activity()
        activity_host = self._shell.get_activity(activity.get_activity_id())
        if activity_host:
            activity_host.close()
        else:
            logging.error("Could not find ActivityHost for activity %s" %
                          activity.get_activity_id())

    def _get_activity(self, x, y):
        # Compute the distance from the center.
        [width, height] = self.get_allocation()
        x -= width / 2
        y -= height / 2
        r = math.hypot(x, y)

        # Ignore the click if it's not inside the donut
        if r < self._get_inner_radius() or r > self._get_radius():
            return None

        # Now figure out where in the donut the click was.
        angle = math.atan2(-y, -x) + math.pi

        # Unfortunately, _get_angles() doesn't count from 0 to 2pi, it
        # counts from roughly pi/2 to roughly 5pi/2. So we have to
        # compare its return values against both angle and angle+2pi
        high_angle = angle + 2 * math.pi

        for index, activity in enumerate(self._model):
            [angle_start, angle_end] = self._get_angles(index)
            if angle_start < angle and angle_end > angle:
                return activity
            elif angle_start < high_angle and angle_end > high_angle:
                return activity

        return None

    def _button_release_event_cb(self, item, event):
        activity = self._get_activity(event.x, event.y)
        if activity is None:
            return False

        activity_host = self._shell.get_activity(activity.get_activity_id())
        if activity_host:
            activity_host.present()
        return True

    MAX_ACTIVITIES = 10
    MIN_ACTIVITY_WEDGE_SIZE = 1.0 / MAX_ACTIVITIES

    def _get_activity_sizes(self):
        # First get the size of each process that hosts an activity,
        # and the number of activities it hosts.
        process_size = {}
        num_activities = {}
        total_activity_size = 0
        for activity in self._model:
            pid = activity.get_pid()
            if not pid:
                # Still starting up, hasn't opened a window yet
                continue

            if process_size.has_key(pid):
                num_activities[pid] += 1
                continue

            try:
                statm = open('/proc/%s/statm' % pid)
                # We use "RSS" (the second field in /proc/PID/statm)
                # for the activity size because that's what ps and top
                # use for calculating "%MEM". We multiply by 4 to
                # convert from pages to kb.
                process_size[pid] = int(statm.readline().split()[1]) * 4
                total_activity_size += process_size[pid]
                num_activities[pid] = 1
                statm.close()
            except IOError:
                logging.warn('ActivitiesDonut: could not read /proc/%s/statm' %
                             pid)
            except (IndexError, ValueError):
                logging.warn('ActivitiesDonut: /proc/%s/statm was not in ' +
                             'expected format' % pid)

        # Next, see how much free memory is left.
        try:
            meminfo = open('/proc/meminfo')
            meminfo.readline()
            free_memory = int(meminfo.readline()[9:-3])
            meminfo.close()
        except IOError:
            logging.warn('ActivitiesDonut: could not read /proc/meminfo')
        except (IndexError, ValueError):
            logging.warn('ActivitiesDonut: /proc/meminfo was not in ' +
                         'expected format')

        # Each activity starts with MIN_ACTIVITY_WEDGE_SIZE. The
        # remaining space in the donut is allocated proportionately
        # among the activities-of-known-size and the free space
        used_space = ActivitiesDonut.MIN_ACTIVITY_WEDGE_SIZE * len(self._model)
        remaining_space = max(0.0, 1.0 - used_space)

        total_memory = total_activity_size + free_memory

        activity_sizes = []
        for activity in self._model:
            percent = ActivitiesDonut.MIN_ACTIVITY_WEDGE_SIZE
            pid = activity.get_pid()
            if process_size.has_key(pid):
                size = process_size[pid] / num_activities[pid]
                percent += remaining_space * size / total_memory
            activity_sizes.append(percent)

        return activity_sizes

    def _compute_angles(self):
        percentages = self._get_activity_sizes()
        self._angles = []
        if len(percentages) == 0:
            return

        # The first wedge (Journal) should be centered at 6 o'clock
        size = percentages[0] * 2 * math.pi
        angle = (math.pi - size) / 2
        self._angles.append(angle)

        for size in percentages:
            self._angles.append(self._angles[-1] + size * 2 * math.pi)

    def _get_angles(self, index):
        return [self._angles[index],
                self._angles[(index + 1) % len(self._angles)]]

    def _get_radius(self):
        [width, height] = self.get_allocation()
        return min(width, height) / 2

    def _get_inner_radius(self):
        return self._get_radius() * 0.5

    def do_paint_below_children(self, cr, damaged_box):
        [width, height] = self.get_allocation()

        cr.translate(width / 2, height / 2)

        radius = self._get_radius()

        # Outer Ring
        cr.set_source_rgb(0xf1 / 255.0, 0xf1 / 255.0, 0xf1 / 255.0)
        cr.arc(0, 0, radius, 0, 2 * math.pi)
        cr.fill()

        # Selected Wedge
        current_activity = self._model.get_current_activity()
        if current_activity is not None:
            selected_index = self._model.index(current_activity)    
            [angle_start, angle_end] = self._get_angles(selected_index)
        
            cr.new_path()   
            cr.move_to(0, 0)
            cr.line_to(radius * math.cos(angle_start),
                       radius * math.sin(angle_start))
            cr.arc(0, 0, radius, angle_start, angle_end)
            cr.line_to(0, 0)
            cr.set_source_rgb(1, 1, 1)
            cr.fill()        

        # Edges
        if len(self._model):   
            n_edges = len(self._model) + 1
        else:
            n_edges = 0
            
        for i in range(0, n_edges):
            cr.new_path()
            cr.move_to(0, 0)
            [angle, unused_angle] = self._get_angles(i)
            cr.line_to(radius * math.cos(angle),
                        radius * math.sin(angle))
            
            cr.set_source_rgb(0xe2 / 255.0, 0xe2 / 255.0, 0xe2 / 255.0)
            cr.set_line_width(4)
            cr.stroke_preserve()
             
        # Inner Ring    
        cr.new_path()
        cr.arc(0, 0, self._get_inner_radius(), 0, 2 * math.pi)
        cr.set_source_rgb(0xe2 / 255.0, 0xe2 / 255.0, 0xe2 / 255.0)
        cr.fill()

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        radius = (self._get_inner_radius() + self._get_radius()) / 2

        self._compute_angles()
        for i, icon in enumerate(self._activities):
            [angle_start, angle_end] = self._get_angles(i)
            angle = angle_start + (angle_end - angle_start) / 2

            [icon_width, icon_height] = icon.get_allocation()

            x = int(radius * math.cos(angle)) - icon_width / 2
            y = int(radius * math.sin(angle)) - icon_height / 2
            self.set_position(icon, x + width / 2, y + height / 2)
