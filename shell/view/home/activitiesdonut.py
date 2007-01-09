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
import logging

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import style
from sugar.graphics import colors
from sugar.graphics import iconcolor
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
    _LEVEL_MAX = 1.6
    _LEVEL_MIN = 0.0
    _INTERVAL = 100

    def __init__(self, activity):
        icon_name = activity.get_icon_name()
        self._orig_color = profile.get_color()
        
        self._direction = 0
        self._level = self._LEVEL_MAX
        color = self._get_icon_color_for_level()

        CanvasIcon.__init__(self, icon_name=icon_name, color=color)
        style.apply_stylesheet(self, 'ring.ActivityIcon')

        self._activity = activity
        self._launched = False
        self._pulse_id = gobject.timeout_add(self._INTERVAL, self._pulse_cb)

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        logging.debug("removing source %s" % self._pulse_id)
        if self._pulse_id > 0:
            gobject.source_remove(self._pulse_id)
        self._pulse_id = 0

    def _get_icon_color_for_level(self):
        factor = math.sin(self._level)
        h, s, v = colorsys.rgb_to_hsv(*html_to_rgb(self._orig_color.get_fill_color()))
        new_fill = rgb_to_html(*colorsys.hsv_to_rgb(h, s * factor, v))
        h, s, v = colorsys.rgb_to_hsv(*html_to_rgb(self._orig_color.get_stroke_color()))
        new_stroke = rgb_to_html(*colorsys.hsv_to_rgb(h, s * factor, v))
        return iconcolor.IconColor("%s,%s" % (new_fill, new_stroke))

    def _pulse_cb(self):
        if self._direction == 1:
            self._level += 0.1
            if self._level >= self._LEVEL_MAX:
                self._direction = 0
                self._level = self._LEVEL_MAX
        elif self._direction == 0:
            self._level -= 0.1
            if self._level <= self._LEVEL_MIN:
                self._direction = 1
                self._level = self._LEVEL_MIN

        self.props.color = self._get_icon_color_for_level()
        self.emit_paint_needed(0, 0, -1, -1)
        return True

    def set_launched(self):
        if self._launched:
            return
        self._launched = True
        self.cleanup()
        self._level = 100.0
        self.props.color = self._orig_color
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

    def _activity_launched_cb(self, model, activity):
        self._add_activity(activity)

    def _activity_added_cb(self, model, activity):
        # Mark the activity as launched
        act_id = activity.get_id()
        if not self._activities.has_key(act_id):
            self._add_activity(activity)
        icon = self._activities[act_id]
        icon.set_launched()

    def _activity_removed_cb(self, model, activity):
        self._remove_activity(activity)
    
    def _remove_activity(self, activity):
        act_id = activity.get_id()
        if not self._activities.has_key(act_id):
            return
        icon = self._activities[act_id]
        self.remove(icon)
        act = self._activities[act_id]
        act.cleanup()
        del self._activities[act_id]

    def _add_activity(self, activity):
        icon = ActivityIcon(activity)
        icon.connect('activated', self._activity_icon_clicked_cb)
        self.append(icon, hippo.PACK_FIXED)

        self._activities[activity.get_id()] = icon

        self.emit_paint_needed(0, 0, -1, -1)

    def _activity_icon_clicked_cb(self, icon):
        activity = icon.get_activity()
        if not icon.get_launched():
            return

        activity_host = self._shell.get_activity(activity.get_id())
        if activity_host:
            activity_host.present()

    def _get_angles(self, index):
        angle = 2 * math.pi / 8
        return [index * angle, (index + 1) * angle]

    def _get_radius(self):
        [width, height] = self.get_allocation()
        return min(width, height) / 2

    def _get_inner_radius(self):
        return self._get_radius() * 0.5

    def do_paint_below_children(self, cr, damaged_box):
        [width, height] = self.get_allocation()

        cr.translate(width / 2, height / 2)

        radius = self._get_radius()

        cr.set_source_rgb(0xf1 / 255.0, 0xf1 / 255.0, 0xf1 / 255.0)
        cr.arc(0, 0, radius, 0, 2 * math.pi)
        cr.fill()

        angle_end = 0
        for i in range(0, len(self._activities)):
            [angle_start, angle_end] = self._get_angles(i)

            cr.new_path()
            cr.move_to(0, 0)
            cr.line_to(radius * math.cos(angle_start),
                       radius * math.sin(angle_start))
            cr.arc(0, 0, radius, angle_start, angle_end)
            cr.line_to(0, 0)

            cr.set_source_rgb(0xe2 / 255.0, 0xe2 / 255.0, 0xe2 / 255.0)
            cr.set_line_width(4)
            cr.stroke_preserve()

            cr.set_source_rgb(1, 1, 1)
            cr.fill()

        cr.set_source_rgb(0xe2 / 255.0, 0xe2 / 255.0, 0xe2 / 255.0)
        cr.arc(0, 0, self._get_inner_radius(), 0, 2 * math.pi)
        cr.fill()

    def do_allocate(self, width, height):
        hippo.CanvasBox.do_allocate(self, width, height)

        radius = (self._get_inner_radius() + self._get_radius()) / 2

        i = 0
        for icon in self._activities.values():
            [angle_start, angle_end] = self._get_angles(i)
            angle = angle_start + (angle_end - angle_start) / 2

            [icon_width, icon_height] = icon.get_allocation()

            x = int(radius * math.cos(angle)) - icon_width / 2
            y = int(radius * math.sin(angle)) - icon_height / 2
            self.move(icon, x + width / 2, y + height / 2)

            i += 1
