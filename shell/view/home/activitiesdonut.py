# Copyright (C) 2006, Red Hat, Inc.
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

import hippo
import math
import gobject
import colorsys

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import units
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

    def __init__(self, activity):
        icon_name = activity.get_icon_name()
        self._orig_color = profile.get_color()
        self._icon_colors = self._compute_icon_colors()

        self._direction = 0
        self._level_max = len(self._icon_colors) - 1
        self._level = self._level_max
        color = self._icon_colors[self._level]

        CanvasIcon.__init__(self, icon_name=icon_name, xo_color=color,
                            scale=units.MEDIUM_ICON_SCALE, cache=True)

        self._activity = activity
        self._launched = False
        self._pulse_id = gobject.timeout_add(self._INTERVAL, self._pulse_cb)

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        if self._pulse_id > 0:
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

    def set_launched(self):
        if self._launched:
            return
        self._launched = True
        self.cleanup()
        self._level = 100.0
        self.props.xo_color = self._orig_color
        self.emit_paint_needed(0, 0, -1, -1)

    def get_launched(self):
        return self._launched

    def get_activity(self):
        return self._activity

class ActivitiesDonut(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarActivitiesDonut'
    def __init__(self, shell, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)

        self._activities = {}
        self._shell = shell

        self._model = shell.get_model().get_home()
        self._model.connect('activity-launched', self._activity_launched_cb)
        self._model.connect('activity-added', self._activity_added_cb)
        self._model.connect('activity-removed', self._activity_removed_cb)
        self._model.connect('active-activity-changed', self._activity_changed_cb)

    def _activity_launched_cb(self, model, activity):
        self._add_activity(activity)

    def _activity_added_cb(self, model, activity):
        # Mark the activity as launched
        act_id = activity.get_activity_id()
        if not self._activities.has_key(act_id):
            self._add_activity(activity)
        icon = self._activities[act_id]
        icon.set_launched()

    def _activity_removed_cb(self, model, activity):
        self._remove_activity(activity)
    
    def _activity_changed_cb(self, model, activity):
        self.emit_paint_needed(0, 0, -1, -1)

    def _remove_activity(self, activity):
        act_id = activity.get_activity_id()
        if not self._activities.has_key(act_id):
            return
        icon = self._activities[act_id]
        self.remove(icon)
        icon.cleanup()
        del self._activities[act_id]

    def _add_activity(self, activity):
        icon = ActivityIcon(activity)
        icon.connect('activated', self._activity_icon_clicked_cb)
        self.append(icon, hippo.PACK_FIXED)

        self._activities[activity.get_activity_id()] = icon

        self.emit_paint_needed(0, 0, -1, -1)

    def _activity_icon_clicked_cb(self, icon):
        activity = icon.get_activity()
        if not icon.get_launched():
            return

        activity_host = self._shell.get_activity(activity.get_activity_id())
        if activity_host:
            activity_host.present()

    def _get_angles(self, index):
        angle = 2 * math.pi / 8
        bottom_align = (math.pi - angle) / 2
        return [index * angle + bottom_align, 
                (index + 1) * angle + bottom_align]

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

        i = 0
        for h_activity in self._model:
            icon = self._activities[h_activity.get_activity_id()]
            [angle_start, angle_end] = self._get_angles(i)
            angle = angle_start + (angle_end - angle_start) / 2

            [icon_width, icon_height] = icon.get_allocation()

            x = int(radius * math.cos(angle)) - icon_width / 2
            y = int(radius * math.sin(angle)) - icon_height / 2
            self.set_position(icon, x + width / 2, y + height / 2)

            i += 1
