# Copyright(c) 2007-2010 by Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#
# This file is part of PyCha.
#
# PyCha is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyCha is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyCha.  If not, see <http://www.gnu.org/licenses/>.

import math

import cairo

from jarabe.util.sugarpycha.chart import Chart, Option, Layout, Area, get_text_extents
from jarabe.util.sugarpycha.color import hex2rgb


class PieChart(Chart):

    def __init__(self, surface=None, options={}, debug=False):
        super(PieChart, self).__init__(surface, options, debug)
        self.slices = []
        self.centerx = 0
        self.centery = 0
        self.layout = PieLayout(self.slices)

        self.colors = [[0, 255, 0],
                       [0, 200, 204],
                       [120, 203, 0],
                       [107, 0, 202],
                       [194, 0, 0],
                       ]

    def _updateChart(self):
        """Evaluates measures for pie charts"""
        slices = [dict(name=key,
                       value=(i, value[0][1]))
                  for i, (key, value) in enumerate(self.datasets)]

        s = float(sum([slice['value'][1] for slice in slices]))

        fraction = angle = 0.0

        del self.slices[:]
        for slice in slices:
            if slice['value'][1] > 0:
                angle += fraction
                fraction = slice['value'][1] / s
                self.slices.append(Slice(slice['name'], fraction,
                                         slice['value'][0], slice['value'][1],
                                         angle))

    def _updateTicks(self):
        """Evaluates pie ticks"""
        self.xticks = []
        if self.options.axis.x.ticks:
            lookup = dict([(_slice.xval, _slice) for _slice in self.slices])
            for tick in self.options.axis.x.ticks:
                if not isinstance(tick, Option):
                    tick = Option(tick)
                _slice = lookup.get(tick.v, None)
                label = tick.label or str(tick.v)
                if _slice is not None:
                    label += ' (%.0f%%)' % (_slice.fraction * 100)
                    self.xticks.append((tick.v, label))
        else:
            for _slice in self.slices:
                label = '%s (%.1f%%)' % (_slice.name, _slice.fraction * 100)
                self.xticks.append((_slice.xval, label))

    def _renderLines(self, cx):
        """Aux function for _renderBackground"""
        # there are no lines in a Pie Chart

    def _renderChart(self, cx):
        """Renders a pie chart"""
        self.centerx = self.layout.chart.x + self.layout.chart.w * 0.5
        self.centery = self.layout.chart.y + self.layout.chart.h * 0.5

        cx.set_line_join(cairo.LINE_JOIN_ROUND)

        if self.options.stroke.shadow and False:
            cx.save()
            cx.set_source_rgba(0, 0, 0, 0.15)

            cx.new_path()
            cx.move_to(self.centerx, self.centery)
            cx.arc(self.centerx + 1, self.centery + 2,
                   self.layout.radius + 1, 0, math.pi * 2)
            cx.line_to(self.centerx, self.centery)
            cx.close_path()
            cx.fill()
            cx.restore()

        cx.save()

        ctr = 0
        color_len = len(self.colors)

        for slice in self.slices:
            if slice.isBigEnough():
                if ctr == color_len - 1:
                    ctr = 0
                else:
                    ctr = ctr + 1
                cx.set_source_rgb(*self.colors[ctr])

                if self.options.shouldFill:
                    slice.draw(cx, self.centerx, self.centery,
                               self.layout.radius)
                    cx.fill()

                if not self.options.stroke.hide:
                    slice.draw(cx, self.centerx, self.centery,
                               self.layout.radius)
                    cx.set_line_width(self.options.stroke.width)
                    cx.set_source_rgb(*hex2rgb(self.options.stroke.color))
                    #cx.stroke()

        cx.restore()

        if self.debug:
            cx.set_source_rgba(1, 0, 0, 0.5)
            px = max(cx.device_to_user_distance(1, 1))
            for x, y in self.layout._lines:
                cx.arc(x, y, 5 * px, 0, 2 * math.pi)
                cx.fill()
                cx.new_path()
                cx.move_to(self.centerx, self.centery)
                cx.line_to(x, y)
                cx.stroke()

    def _renderAxis(self, cx):
        """Renders the axis for pie charts"""
        if self.options.axis.x.hide or not self.xticks:
            return

        self.xlabels = []

        if self.debug:
            px = max(cx.device_to_user_distance(1, 1))
            cx.set_source_rgba(0, 0, 1, 0.5)
            for x, y, w, h in self.layout.ticks:
                cx.rectangle(x, y, w, h)
                cx.stroke()
                cx.arc(x + w / 2.0, y + h / 2.0, 5 * px, 0, 2 * math.pi)
                cx.fill()
                cx.arc(x, y, 2 * px, 0, 2 * math.pi)
                cx.fill()

        cx.select_font_face(self.options.axis.tickFont,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cx.set_font_size(10)

        cx.set_source_rgb(*hex2rgb(self.options.axis.labelColor))

        for i, tick in enumerate(self.xticks):
            label = tick[1]
            x, y, w, h = self.layout.ticks[i]

            xb, yb, width, height, xa, ya = cx.text_extents(label)

            # draw label with text tick[1]
            cx.move_to(x - xb, y - yb)
            cx.show_text(label)
            self.xlabels.append(label)


class Slice(object):

    def __init__(self, name, fraction, xval, yval, angle):
        self.name = name
        self.fraction = fraction
        self.xval = xval
        self.yval = yval
        self.startAngle = 2 * angle * math.pi
        self.endAngle = 2 * (angle + fraction) * math.pi

    def __str__(self):
        return ("<pycha.pie.Slice from %.2f to %.2f (%.2f%%)>" %
                (self.startAngle, self.endAngle, self.fraction))

    def isBigEnough(self):
        return abs(self.startAngle - self.endAngle) > 0.001

    def draw(self, cx, centerx, centery, radius):
        cx.new_path()
        cx.move_to(centerx, centery)
        cx.arc(centerx, centery, radius - 10, -self.endAngle, -self.startAngle)
        cx.close_path()

    def getNormalisedAngle(self):
        normalisedAngle = (self.startAngle + self.endAngle) / 2

        if normalisedAngle > math.pi * 2:
            normalisedAngle -= math.pi * 2
        elif normalisedAngle < 0:
            normalisedAngle += math.pi * 2

        return normalisedAngle


class PieLayout(Layout):
    """Set of chart areas for pie charts"""

    def __init__(self, slices):
        self.slices = slices

        self.title = Area()
        self.chart = Area()

        self.ticks = []
        self.radius = 0

        self._areas = (
            (self.title, (1, 126 / 255.0, 0)),  # orange
            (self.chart, (75 / 255.0, 75 / 255.0, 1.0)),  # blue
            )

        self._lines = []

    def update(self, cx, options, width, height, xticks, yticks):
        self.title.x = options.padding.left
        self.title.y = options.padding.top
        self.title.w = width - (options.padding.left + options.padding.right)
        self.title.h = get_text_extents(cx,
                                        options.title,
                                        options.titleFont,
                                        options.titleFontSize,
                                        options.encoding)[1]

        lookup = dict([(slice.xval, slice) for slice in self.slices])

        self.chart.x = self.title.x
        self.chart.y = self.title.y + self.title.h
        self.chart.w = self.title.w
        self.chart.h = height - self.title.h - (options.padding.top
                                                + options.padding.bottom)

        centerx = self.chart.x + self.chart.w * 0.5
        centery = self.chart.y + self.chart.h * 0.5

        self.radius = min(self.chart.w / 2.0, self.chart.h / 2.0)
        for tick in xticks:
            _slice = lookup.get(tick[0], None)
            width, height = get_text_extents(cx, tick[1],
                                             options.axis.tickFont,
                                             options.axis.tickFontSize,
                                             options.encoding)
            angle = _slice.getNormalisedAngle()
            radius = self._get_min_radius(angle, centerx, centery,
                                          width, height)
            self.radius = min(self.radius, radius)

        # Now that we now the radius we move the ticks as close as we can
        # to the circle
        for i, tick in enumerate(xticks):
            _slice = lookup.get(tick[0], None)
            angle = _slice.getNormalisedAngle()
            self.ticks[i] = self._get_tick_position(self.radius, angle,
                                                    self.ticks[i],
                                                    centerx, centery)

    def _get_min_radius(self, angle, centerx, centery, width, height):
        min_radius = None

        # precompute some common values
        tan = math.tan(angle)
        half_width = width / 2.0
        half_height = height / 2.0
        offset_x = half_width * tan
        offset_y = half_height / tan

        def intersect_horizontal_line(y):
            return centerx + (centery - y) / tan

        def intersect_vertical_line(x):
            return centery - tan * (x - centerx)

        # computes the intersection between the rect that has
        # that angle with the X axis and the bounding chart box
        if 0.25 * math.pi <= angle < 0.75 * math.pi:
            # intersects with the top rect
            y = self.chart.y
            x = intersect_horizontal_line(y)
            self._lines.append((x, y))

            x1 = x - half_width - offset_y
            self.ticks.append((x1, self.chart.y, width, height))

            min_radius = abs((y + height) - centery)
        elif 0.75 * math.pi <= angle < 1.25 * math.pi:
            # intersects with the left rect
            x = self.chart.x
            y = intersect_vertical_line(x)
            self._lines.append((x, y))

            y1 = y - half_height - offset_x
            self.ticks.append((x, y1, width, height))

            min_radius = abs(centerx - (x + width))
        elif 1.25 * math.pi <= angle < 1.75 * math.pi:
            # intersects with the bottom rect
            y = self.chart.y + self.chart.h
            x = intersect_horizontal_line(y)
            self._lines.append((x, y))

            x1 = x - half_width + offset_y
            self.ticks.append((x1, y - height, width, height))

            min_radius = abs((y - height) - centery)
        else:
            # intersects with the right rect
            x = self.chart.x + self.chart.w
            y = intersect_vertical_line(x)
            self._lines.append((x, y))

            y1 = y - half_height + offset_x
            self.ticks.append((x - width, y1, width, height))

            min_radius = abs((x - width) - centerx)

        return min_radius

    def _get_tick_position(self, radius, angle, tick, centerx, centery):
        text_width, text_height = tick[2:4]
        half_width = text_width / 2.0
        half_height = text_height / 2.0

        if 0 <= angle < 0.5 * math.pi:
            # first quadrant
            k1 = j1 = k2 = 1
            j2 = -1
        elif 0.5 * math.pi <= angle < math.pi:
            # second quadrant
            k1 = k2 = -1
            j1 = j2 = 1
        elif math.pi <= angle < 1.5 * math.pi:
            # third quadrant
            k1 = j1 = k2 = -1
            j2 = 1
        elif 1.5 * math.pi <= angle < 2 * math.pi:
            # fourth quadrant
            k1 = k2 = 1
            j1 = j2 = -1

        cx = radius * math.cos(angle) + k1 * half_width
        cy = radius * math.sin(angle) + j1 * half_height

        radius2 = math.sqrt(cx * cx + cy * cy)

        tan = math.tan(angle)
        x = math.sqrt((radius2 * radius2) / (1 + tan * tan))
        y = tan * x

        x = centerx + k2 * x
        y = centery + j2 * y

        return x - half_width, y - half_height, text_width, text_height
