# Copyright(c) 2011 by Roberto Garcia Carvajal <roberpot@gmail.com>
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

from jarabe.util.sugarpycha.chart import Chart
from jarabe.util.sugarpycha.line import Point
from jarabe.util.sugarpycha.color import hex2rgb
from jarabe.util.sugarpycha.utils import safe_unicode


class PolygonalChart(Chart):

    def __init__(self, surface=None, options={}):
        super(PolygonalChart, self).__init__(surface, options)
        self.points = []

    def _updateChart(self):
        """Evaluates measures for polygonal charts"""
        self.points = []

        for i, (name, store) in enumerate(self.datasets):
            for item in store:
                xval, yval = item
                x = (xval - self.minxval) * self.xscale
                y = 1.0 - (yval - self.minyval) * self.yscale
                point = Point(x, y, xval, yval, name)

                if 0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0:
                    self.points.append(point)

    def _renderBackground(self, cx):
        """Renders the background area of the chart"""
        if self.options.background.hide:
            return

        cx.save()

        if self.options.background.baseColor:
            cx.set_source_rgb(*hex2rgb(self.options.background.baseColor))
            cx.paint()

        if self.options.background.chartColor:
            cx.set_source_rgb(*hex2rgb(self.options.background.chartColor))
            cx.set_line_width(10.0)
            cx.new_path()
            init = None
            count = len(self.xticks)
            for index, tick in enumerate(self.xticks):
                ang = math.pi / 2 - index * 2 * math.pi / count
                x = (self.layout.chart.x + self.layout.chart.w / 2
                     - math.cos(ang)
                     * min(self.layout.chart.w / 2, self.layout.chart.h / 2))
                y = (self.layout.chart.y + self.layout.chart.h / 2
                     - math.sin(ang)
                     * min(self.layout.chart.w / 2, self.layout.chart.h / 2))
                if init is None:
                    cx.move_to(x, y)
                    init = (x, y)
                else:
                    cx.line_to(x, y)
            cx.line_to(init[0], init[1])
            cx.close_path()
            cx.fill()

        if self.options.background.lineColor:
            cx.set_source_rgb(*hex2rgb(self.options.background.lineColor))
            cx.set_line_width(self.options.axis.lineWidth)
            self._renderLines(cx)

        cx.restore()

    def _renderLine(self, cx, tick, horiz):
        """Aux function for _renderLines"""

        rad = (self.layout.chart.h / 2) * (1 - tick[0])
        cx.new_path()
        init = None
        count = len(self.xticks)
        for index, tick in enumerate(self.xticks):
            ang = math.pi / 2 - index * 2 * math.pi / count
            x = (self.layout.chart.x + self.layout.chart.w / 2
                 - math.cos(ang) * rad)
            y = (self.layout.chart.y + self.layout.chart.h / 2
                 - math.sin(ang) * rad)
            if init is None:
                cx.move_to(x, y)
                init = (x, y)
            else:
                cx.line_to(x, y)
        cx.line_to(init[0], init[1])
        cx.close_path()
        cx.stroke()

    def _renderXAxis(self, cx):
        """Draws the horizontal line representing the X axis"""

        count = len(self.xticks)

        centerx = self.layout.chart.x + self.layout.chart.w / 2
        centery = self.layout.chart.y + self.layout.chart.h / 2

        for i in range(0, count):
            offset1 = i * 2 * math.pi / count
            offset = math.pi / 2 - offset1

            rad = self.layout.chart.h / 2
            (r1, r2) = (0, rad + 5)

            x1 = centerx - math.cos(offset) * r1
            x2 = centerx - math.cos(offset) * r2
            y1 = centery - math.sin(offset) * r1
            y2 = centery - math.sin(offset) * r2

            cx.new_path()
            cx.move_to(x1, y1)
            cx.line_to(x2, y2)
            cx.close_path()
            cx.stroke()

    def _renderYTick(self, cx, tick, center):
        """Aux method for _renderAxis"""

        i = tick
        tick = self.yticks[i]

        count = len(self.yticks)

        if callable(tick):
            return

        x = center[0]
        y = center[1] - i * (self.layout.chart.h / 2) / count

        cx.new_path()
        cx.move_to(x, y)
        cx.line_to(x - self.options.axis.tickSize, y)
        cx.close_path()
        cx.stroke()

        cx.select_font_face(self.options.axis.tickFont,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cx.set_font_size(self.options.axis.tickFontSize)

        label = safe_unicode(tick[1], self.options.encoding)
        extents = cx.text_extents(label)
        labelWidth = extents[2]
        labelHeight = extents[3]

        if self.options.axis.y.rotate:
            radians = math.radians(self.options.axis.y.rotate)
            cx.move_to(x - self.options.axis.tickSize
                       - (labelWidth * math.cos(radians))
                       - 4,
                       y + (labelWidth * math.sin(radians))
                       + labelHeight / (2.0 / math.cos(radians)))
            cx.rotate(-radians)
            cx.show_text(label)
            cx.rotate(radians)  # this is probably faster than a save/restore
        else:
            cx.move_to(x - self.options.axis.tickSize - labelWidth - 4,
                       y + labelHeight / 2.0)
            cx.rel_move_to(0.0, -labelHeight / 2.0)
            cx.show_text(label)

        return label

    def _renderYAxis(self, cx):
        """Draws the vertical line for the Y axis"""

        centerx = self.layout.chart.x + self.layout.chart.w / 2
        centery = self.layout.chart.y + self.layout.chart.h / 2

        offset = math.pi / 2

        r1 = self.layout.chart.h / 2

        x1 = centerx - math.cos(offset) * r1
        y1 = centery - math.sin(offset) * r1

        cx.new_path()
        cx.move_to(centerx, centery)
        cx.line_to(x1, y1)
        cx.close_path()
        cx.stroke()

    def _renderAxis(self, cx):
        """Renders axis"""
        if self.options.axis.x.hide and self.options.axis.y.hide:
            return

        cx.save()
        cx.set_source_rgb(*hex2rgb(self.options.axis.lineColor))
        cx.set_line_width(self.options.axis.lineWidth)

        centerx = self.layout.chart.x + self.layout.chart.w / 2
        centery = self.layout.chart.y + self.layout.chart.h / 2

        if not self.options.axis.y.hide:
            if self.yticks:

                count = len(self.yticks)

                for i in range(0, count):
                    self._renderYTick(cx, i, (centerx, centery))

            if self.options.axis.y.label:
                self._renderYAxisLabel(cx, self.options.axis.y.label)

            self._renderYAxis(cx)

        if not self.options.axis.x.hide:
            fontAscent = cx.font_extents()[0]
            if self.xticks:

                count = len(self.xticks)

                for i in range(0, count):
                    self._renderXTick(cx, i, fontAscent, (centerx, centery))

            if self.options.axis.x.label:
                self._renderXAxisLabel(cx, self.options.axis.x.label)

            self._renderXAxis(cx)

        cx.restore()

    def _renderXTick(self, cx, i, fontAscent, center):
        tick = self.xticks[i]
        if callable(tick):
            return

        count = len(self.xticks)
        cx.select_font_face(self.options.axis.tickFont,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cx.set_font_size(self.options.axis.tickFontSize)

        label = safe_unicode(tick[1], self.options.encoding)
        extents = cx.text_extents(label)
        labelWidth = extents[2]
        labelHeight = extents[3]

        x, y = center
        cx.move_to(x, y)

        if self.options.axis.x.rotate:
            radians = math.radians(self.options.axis.x.rotate)
            cx.move_to(x - (labelHeight * math.cos(radians)),
                       y + self.options.axis.tickSize
                       + (labelHeight * math.cos(radians))
                       + 4.0)
            cx.rotate(radians)
            cx.show_text(label)
            cx.rotate(-radians)
        else:
            offset1 = i * 2 * math.pi / count
            offset = math.pi / 2 - offset1

            rad = self.layout.chart.h / 2 + 10

            x = center[0] - math.cos(offset) * rad
            y = center[1] - math.sin(offset) * rad

            cx.move_to(x, y)
            cx.rotate(offset - math.pi / 2)

            if math.sin(offset) < 0.0:
                cx.rotate(math.pi)
                cx.rel_move_to(0.0, 5.0)

            cx.rel_move_to(-labelWidth / 2.0, 0)
            cx.show_text(label)
            if math.sin(offset) < 0.0:
                cx.rotate(-math.pi)

            cx.rotate(-(offset - math.pi / 2))
        return label

    def _renderChart(self, cx):
        """Renders a polygonal chart"""
        # draw the polygon.
        def preparePath(storeName):
            cx.new_path()
            firstPoint = True

            count = len(self.points) / len(self.datasets)
            centerx = self.layout.chart.x + self.layout.chart.w / 2
            centery = self.layout.chart.y + self.layout.chart.h / 2

            firstPointCoord = None

            for index, point in enumerate(self.points):
                if point.name == storeName:
                    offset1 = index * 2 * math.pi / count
                    offset = math.pi / 2 - offset1

                    rad = (self.layout.chart.h / 2) * (1 - point.y)

                    x = centerx - math.cos(offset) * rad
                    y = centery - math.sin(offset) * rad

                    if firstPointCoord is None:
                        firstPointCoord = (x, y)

                    if not self.options.shouldFill and firstPoint:
                        # starts the first point of the line
                        cx.move_to(x, y)
                        firstPoint = False
                        continue
                    cx.line_to(x, y)

            if not firstPointCoord is None:
                cx.line_to(firstPointCoord[0], firstPointCoord[1])

            if self.options.shouldFill:
                # Close the path to the start point
                y = ((1.0 - self.origin)
                     * self.layout.chart.h + self.layout.chart.y)
            else:
                cx.set_source_rgb(*self.colorScheme[storeName])
                cx.stroke()

        cx.save()
        cx.set_line_width(self.options.stroke.width)
        if self.options.shouldFill:

            def drawLine(storeName):
                if self.options.stroke.shadow:
                    # draw shadow
                    cx.save()
                    cx.set_source_rgba(0, 0, 0, 0.15)
                    cx.translate(2, -2)
                    preparePath(storeName)
                    cx.fill()
                    cx.restore()

                # fill the line
                cx.set_source_rgb(*self.colorScheme[storeName])
                preparePath(storeName)
                cx.fill()

                if not self.options.stroke.hide:
                    # draw stroke
                    cx.set_source_rgb(*hex2rgb(self.options.stroke.color))
                    preparePath(storeName)
                    cx.stroke()

            # draw the lines
            for key in self._getDatasetsKeys():
                drawLine(key)
        else:
            for key in self._getDatasetsKeys():
                preparePath(key)
        cx.restore()
