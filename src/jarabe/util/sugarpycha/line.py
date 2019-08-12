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

from jarabe.util.sugarpycha.chart import Chart
from jarabe.util.sugarpycha.color import hex2rgb


class LineChart(Chart):

    def __init__(self, surface=None, options={}, debug=False):
        super(LineChart, self).__init__(surface, options, debug)
        self.points = []

    def _updateChart(self):
        """Evaluates measures for line charts"""
        self.points = []

        for i, (name, store) in enumerate(self.datasets):
            for item in store:
                xval, yval = item
                x = (xval - self.minxval) * self.xscale
                y = 1.0 - (yval - self.minyval) * self.yscale
                point = Point(x, y, xval, yval, name)

                if 0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0:
                    self.points.append(point)

    def _renderChart(self, cx):
        """Renders a line chart"""

        def preparePath(storeName):
            cx.new_path()
            firstPoint = True
            lastX = None
            if self.options.shouldFill:
                # Go to the (0,0) coordinate to start drawing the area
                #cx.move_to(self.layout.chart.x,
                #           self.layout.chart.y + self.layout.chart.h)
                offset = (1.0 - self.origin) * self.layout.chart.h
                cx.move_to(self.layout.chart.x, self.layout.chart.y + offset)

            for point in self.points:
                if point.name == storeName:
                    if not self.options.shouldFill and firstPoint:
                        # starts the first point of the line
                        cx.move_to(point.x * self.layout.chart.w
                                   + self.layout.chart.x,
                                   point.y * self.layout.chart.h
                                   + self.layout.chart.y)
                        firstPoint = False
                        continue
                    cx.line_to(point.x * self.layout.chart.w
                               + self.layout.chart.x,
                               point.y * self.layout.chart.h
                               + self.layout.chart.y)
                    # we remember the last X coordinate to close the area
                    # properly. See bug #4
                    lastX = point.x

            if self.options.shouldFill:
                # Close the path to the start point
                y = ((1.0 - self.origin) * self.layout.chart.h
                     + self.layout.chart.y)
                cx.line_to(lastX * self.layout.chart.w
                           + self.layout.chart.x, y)
                cx.line_to(self.layout.chart.x, y)
                cx.close_path()
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


class Point(object):

    def __init__(self, x, y, xval, yval, name):
        self.x, self.y = x, y
        self.xval, self.yval = xval, yval
        self.name = name

    def __str__(self):
        return "<pycha.line.Point@(%.2f, %.2f)>" % (self.x, self.y)
