# Copyright(c) 2009 by Yaco S.L. <lgs@yaco.es>
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

from jarabe.util.sugarpycha.bar import BarChart, VerticalBarChart, HorizontalBarChart, Rect
from jarabe.util.sugarpycha.chart import uniqueIndices
from functools import reduce


class StackedBarChart(BarChart):

    def __init__(self, surface=None, options={}, debug=False):
        super(StackedBarChart, self).__init__(surface, options, debug)
        self.barWidth = 0.0

    def _updateXY(self):
        super(StackedBarChart, self)._updateXY()
        # each dataset is centered around a line segment. that's why we
        # need n + 1 divisions on the x axis
        self.xscale = 1 / (self.xrange + 1.0)

        if self.options.axis.y.range is None:
            # Fix the yscale as we accumulate the y values
            stores = self._getDatasetsValues()
            n_stores = len(stores)
            flat_y = [pair[1] for pair in reduce(lambda a, b: a + b, stores)]
            store_size = len(flat_y) / n_stores
            accum = [sum(flat_y[j]for j in range(i,
                                                  i + store_size * n_stores,
                                                  store_size))
                     for i in range(len(flat_y) / n_stores)]
            self.yrange = float(max(accum))
            if self.yrange == 0:
                self.yscale = 1.0
            else:
                self.yscale = 1.0 / self.yrange

    def _updateChart(self):
        """Evaluates measures for vertical bars"""
        stores = self._getDatasetsValues()
        uniqx = uniqueIndices(stores)

        if len(uniqx) == 1:
            self.minxdelta = 1.0
        else:
            self.minxdelta = min([abs(uniqx[j] - uniqx[j - 1])
                                  for j in range(1, len(uniqx))])

        k = self.minxdelta * self.xscale
        self.barWidth = k * self.options.barWidthFillFraction
        self.barMargin = k * (1.0 - self.options.barWidthFillFraction) / 2

        self.bars = []


class StackedVerticalBarChart(StackedBarChart, VerticalBarChart):

    def _updateChart(self):
        """Evaluates measures for vertical bars"""
        super(StackedVerticalBarChart, self)._updateChart()

        accumulated_heights = {}
        for i, (name, store) in enumerate(self.datasets):
            for item in store:
                xval, yval = item
                x = ((xval - self.minxval) * self.xscale) + self.barMargin
                w = self.barWidth
                h = abs(yval) * self.yscale
                if yval > 0:
                    y = (1.0 - h) - self.origin
                else:
                    y = 1 - self.origin

                accumulated_height = accumulated_heights.setdefault(xval, 0)
                y -= accumulated_height
                accumulated_heights[xval] += h

                rect = Rect(x, y, w, h, xval, yval, name)

                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)


class StackedHorizontalBarChart(StackedBarChart, HorizontalBarChart):

    def _updateChart(self):
        """Evaluates measures for horizontal bars"""
        super(StackedHorizontalBarChart, self)._updateChart()

        accumulated_widths = {}
        for i, (name, store) in enumerate(self.datasets):
            for item in store:
                xval, yval = item
                y = ((xval - self.minxval) * self.xscale) + self.barMargin
                h = self.barWidth
                w = abs(yval) * self.yscale
                if yval > 0:
                    x = self.origin
                else:
                    x = self.origin - w

                accumulated_width = accumulated_widths.setdefault(xval, 0)
                x += accumulated_width
                accumulated_widths[xval] += w

                rect = Rect(x, y, w, h, xval, yval, name)

                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)
