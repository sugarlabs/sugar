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

from jarabe.util.sugarpycha.chart import Chart, uniqueIndices
from jarabe.util.sugarpycha.color import hex2rgb
from jarabe.util.sugarpycha.utils import safe_unicode


class BarChart(Chart):

    def __init__(self, surface=None, options={}, debug=False):
        super(BarChart, self).__init__(surface, options, debug)
        self.bars = []
        self.minxdelta = 0.0
        self.barWidthForSet = 0.0
        self.barMargin = 0.0

    def _updateXY(self):
        super(BarChart, self)._updateXY()
        # each dataset is centered around a line segment. that's why we
        # need n + 1 divisions on the x axis
        self.xscale = 1 / (self.xrange + 1.0)

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
        barWidth = k * self.options.barWidthFillFraction
        self.barWidthForSet = barWidth / len(stores)
        self.barMargin = k * (1.0 - self.options.barWidthFillFraction) / 2

        self.bars = []

    def _renderChart(self, cx):
        """Renders a horizontal/vertical bar chart"""

        def drawBar(bar):
            stroke_width = self.options.stroke.width
            ux, uy = cx.device_to_user_distance(stroke_width, stroke_width)
            if ux < uy:
                ux = uy
            cx.set_line_width(ux)

            # gather bar proportions
            x = self.layout.chart.x + self.layout.chart.w * bar.x
            y = self.layout.chart.y + self.layout.chart.h * bar.y
            w = self.layout.chart.w * bar.w
            h = self.layout.chart.h * bar.h

            if (w < 1 or h < 1) and self.options.yvals.skipSmallValues:
                return  # don't draw when the bar is too small

            if self.options.stroke.shadow:
                cx.set_source_rgba(0, 0, 0, 0.15)
                rectangle = self._getShadowRectangle(x, y, w, h)
                cx.rectangle(*rectangle)
                cx.fill()

            if self.options.shouldFill or (not self.options.stroke.hide):

                if self.options.shouldFill:
                    cx.set_source_rgb(*self.colorScheme[bar.name])
                    cx.rectangle(x, y, w, h)
                    cx.fill()

                if not self.options.stroke.hide:
                    cx.set_source_rgb(*hex2rgb(self.options.stroke.color))
                    cx.rectangle(x, y, w, h)
                    cx.stroke()

            if bar.yerr:
                self._renderError(cx, x, y, w, h, bar.yval, bar.yerr)

            # render yvals above/beside bars
            if self.options.yvals.show:
                cx.save()
                cx.set_font_size(self.options.yvals.fontSize)
                cx.set_source_rgb(*hex2rgb(self.options.yvals.fontColor))

                if callable(self.options.yvals.renderer):
                    label = safe_unicode(self.options.yvals.renderer(bar),
                                         self.options.encoding)
                else:
                    label = safe_unicode(bar.yval, self.options.encoding)
                extents = cx.text_extents(label)
                labelW = extents[2]
                labelH = extents[3]

                self._renderYVal(cx, label, labelW, labelH, x, y, w, h)

                cx.restore()

        cx.save()
        for bar in self.bars:
            drawBar(bar)
        cx.restore()

    def _renderYVal(self, cx, label, width, height, x, y, w, h):
        raise NotImplementedError


class VerticalBarChart(BarChart):

    def _updateChart(self):
        """Evaluates measures for vertical bars"""
        super(VerticalBarChart, self)._updateChart()
        for i, (name, store) in enumerate(self.datasets):
            for item in store:
                if len(item) == 3:
                    xval, yval, yerr = item
                else:
                    xval, yval = item

                x = (((xval - self.minxval) * self.xscale)
                    + self.barMargin + (i * self.barWidthForSet))
                w = self.barWidthForSet
                h = abs(yval) * self.yscale
                if yval > 0:
                    y = (1.0 - h) - self.origin
                else:
                    y = 1 - self.origin
                rect = Rect(x, y, w, h, xval, yval, name)

                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)

    def _updateTicks(self):
        """Evaluates bar ticks"""
        super(BarChart, self)._updateTicks()
        offset = (self.minxdelta * self.xscale) / 2
        self.xticks = [(tick[0] + offset, tick[1]) for tick in self.xticks]

    def _getShadowRectangle(self, x, y, w, h):
        return (x - 2, y - 2, w + 4, h + 2)

    def _renderYVal(self, cx, label, labelW, labelH, barX, barY, barW, barH):
        x = barX + (barW / 2.0) - (labelW / 2.0)
        if self.options.yvals.snapToOrigin:
            y = barY + barH - 0.5 * labelH
        elif self.options.yvals.inside:
            y = barY + (1.5 * labelH)
        else:
            y = barY - 0.5 * labelH

        # if the label doesn't fit below the bar, put it above the bar
        if y > (barY + barH):
            y = barY - 0.5 * labelH

        cx.move_to(x, y)
        cx.show_text(label)

    def _renderError(self, cx, barX, barY, barW, barH, value, error):
        center = barX + (barW / 2.0)
        errorWidth = max(barW * 0.1, 5.0)
        left = center - errorWidth
        right = center + errorWidth
        errorSize = barH * error / value
        top = barY + errorSize
        bottom = barY - errorSize

        cx.set_source_rgb(0, 0, 0)
        cx.move_to(left, top)
        cx.line_to(right, top)
        cx.stroke()
        cx.move_to(center, top)
        cx.line_to(center, bottom)
        cx.stroke()
        cx.move_to(left, bottom)
        cx.line_to(right, bottom)
        cx.stroke()


class HorizontalBarChart(BarChart):

    def _updateChart(self):
        """Evaluates measures for horizontal bars"""
        super(HorizontalBarChart, self)._updateChart()

        for i, (name, store) in enumerate(self.datasets):
            for item in store:
                if len(item) == 3:
                    xval, yval, yerr = item
                else:
                    xval, yval = item
                    yerr = 0.0

                y = (((xval - self.minxval) * self.xscale)
                     + self.barMargin + (i * self.barWidthForSet))
                h = self.barWidthForSet
                w = abs(yval) * self.yscale
                if yval > 0:
                    x = self.origin
                else:
                    x = self.origin - w
                rect = Rect(x, y, w, h, xval, yval, name, yerr)

                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)

    def _updateTicks(self):
        """Evaluates bar ticks"""
        super(BarChart, self)._updateTicks()
        offset = (self.minxdelta * self.xscale) / 2
        tmp = self.xticks
        self.xticks = [(1.0 - tick[0], tick[1]) for tick in self.yticks]
        self.yticks = [(tick[0] + offset, tick[1]) for tick in tmp]

    def _renderLines(self, cx):
        """Aux function for _renderBackground"""
        if self.options.axis.y.showLines and self.yticks:
            for tick in self.xticks:
                self._renderLine(cx, tick, True)
        if self.options.axis.x.showLines and self.xticks:
            for tick in self.yticks:
                self._renderLine(cx, tick, False)

    def _getShadowRectangle(self, x, y, w, h):
        return (x, y - 2, w + 2, h + 4)

    def _renderXAxisLabel(self, cx, labelText):
        labelText = self.options.axis.x.label
        super(HorizontalBarChart, self)._renderYAxisLabel(cx, labelText)

    def _renderXAxis(self, cx):
        """Draws the horizontal line representing the X axis"""
        cx.new_path()
        cx.move_to(self.layout.chart.x,
                   self.layout.chart.y + self.layout.chart.h)
        cx.line_to(self.layout.chart.x + self.layout.chart.w,
                   self.layout.chart.y + self.layout.chart.h)
        cx.close_path()
        cx.stroke()

    def _renderYAxisLabel(self, cx, labelText):
        labelText = self.options.axis.y.label
        super(HorizontalBarChart, self)._renderXAxisLabel(cx, labelText)

    def _renderYAxis(self, cx):
        # draws the vertical line representing the Y axis
        cx.new_path()
        cx.move_to(self.layout.chart.x + self.origin * self.layout.chart.w,
                   self.layout.chart.y)
        cx.line_to(self.layout.chart.x + self.origin * self.layout.chart.w,
                   self.layout.chart.y + self.layout.chart.h)
        cx.close_path()
        cx.stroke()

    def _renderYVal(self, cx, label, labelW, labelH, barX, barY, barW, barH):
        y = barY + (barH / 2.0) + (labelH / 2.0)
        if self.options.yvals.snapToOrigin:
            x = barX + 2
        elif self.options.yvals.inside:
            x = barX + barW - (1.2 * labelW)
        else:
            x = barX + barW + 0.2 * labelW

        # if the label doesn't fit to the left of the bar, put it to the right
        if x < barX:
            x = barX + barW + 0.2 * labelW

        cx.move_to(x, y)
        cx.show_text(label)

    def _renderError(self, cx, barX, barY, barW, barH, value, error):
        center = barY + (barH / 2.0)
        errorHeight = max(barH * 0.1, 5.0)
        top = center + errorHeight
        bottom = center - errorHeight
        errorSize = barW * error / value
        right = barX + barW + errorSize
        left = barX + barW - errorSize

        cx.set_source_rgb(0, 0, 0)
        cx.move_to(left, top)
        cx.line_to(left, bottom)
        cx.stroke()
        cx.move_to(left, center)
        cx.line_to(right, center)
        cx.stroke()
        cx.move_to(right, top)
        cx.line_to(right, bottom)
        cx.stroke()


class Rect(object):

    def __init__(self, x, y, w, h, xval, yval, name, yerr=0.0):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.xval, self.yval, self.yerr = xval, yval, yerr
        self.name = name

    def __str__(self):
        return ("<pycha.bar.Rect@(%.2f, %.2f) %.2fx%.2f (%.2f, %.2f, %.2f) %s>"
                % (self.x, self.y, self.w, self.h,
                   self.xval, self.yval, self.yerr,
                   self.name))
