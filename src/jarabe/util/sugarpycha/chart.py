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

import copy
import inspect
import math

import cairo

from jarabe.util.sugarpycha.color import ColorScheme, hex2rgb, DEFAULT_COLOR
from jarabe.util.sugarpycha.utils import safe_unicode
from functools import reduce


class Chart(object):

    def __init__(self, surface, options={}, debug=False):
        # this flag is useful to reuse this chart for drawing different data
        # or use different options
        self.resetFlag = False

        # initialize storage
        self.datasets = []

        # computed values used in several methods
        self.layout = Layout()
        self.minxval = None
        self.maxxval = None
        self.minyval = None
        self.maxyval = None
        self.xscale = 1.0
        self.yscale = 1.0
        self.xrange = None
        self.yrange = None
        self.origin = 0.0

        self.xticks = []
        self.yticks = []

        # set the default options
        self.options = copy.deepcopy(DEFAULT_OPTIONS)
        if options:
            self.options.merge(options)

        # initialize the surface
        self._initSurface(surface)

        self.colorScheme = None

        # debug mode to draw aditional hints
        self.debug = debug

    def addDataset(self, dataset):
        """Adds an object containing chart data to the storage hash"""
        self.datasets += dataset

    def _getDatasetsKeys(self):
        """Return the name of each data set"""
        return [d[0] for d in self.datasets]

    def _getDatasetsValues(self):
        """Return the data (value) of each data set"""
        return [d[1] for d in self.datasets]

    def setOptions(self, options={}):
        """Sets options of this chart"""
        self.options.merge(options)

    def getSurfaceSize(self):
        cx = cairo.Context(self.surface)
        x, y, w, h = cx.clip_extents()
        return w, h

    def reset(self):
        """Resets options and datasets.

        In the next render the surface will be cleaned before any drawing.
        """
        self.resetFlag = True
        self.options = copy.deepcopy(DEFAULT_OPTIONS)
        self.datasets = []

    def render(self, surface=None, options={}):
        """Renders the chart with the specified options.

        The optional parameters can be used to render a chart in a different
        surface with new options.
        """
        self._update(options)
        if surface:
            self._initSurface(surface)

        cx = cairo.Context(self.surface)

        # calculate area data
        surface_width, surface_height = self.getSurfaceSize()
        self.layout.update(cx, self.options, surface_width, surface_height,
                           self.xticks, self.yticks)

        self._renderBackground(cx)
        if self.debug:
            self.layout.render(cx)
        self._renderChart(cx)
        self._renderAxis(cx)
        self._renderTitle(cx)
        self._renderLegend(cx)

    def clean(self):
        """Clears the surface with a white background."""
        cx = cairo.Context(self.surface)
        cx.save()
        cx.set_source_rgb(1, 1, 1)
        cx.paint()
        cx.restore()

    def _setColorscheme(self):
        """Sets the colorScheme used for the chart using the
        options.colorScheme option
        """
        name = self.options.colorScheme.name
        keys = self._getDatasetsKeys()
        colorSchemeClass = ColorScheme.getColorScheme(name, None)
        if colorSchemeClass is None:
            raise ValueError('Color scheme "%s" is invalid!' % name)

        # Remove invalid args before calling the constructor
        kwargs = dict(self.options.colorScheme.args)
        validArgs = inspect.getargspec(colorSchemeClass.__init__)[0]
        kwargs = dict([(k, v) for k, v in list(kwargs.items()) if k in validArgs])
        self.colorScheme = colorSchemeClass(keys, **kwargs)

    def _initSurface(self, surface):
        self.surface = surface

        if self.resetFlag:
            self.resetFlag = False
            self.clean()

    def _update(self, options={}):
        """Update all the information needed to render the chart"""
        self.setOptions(options)
        self._setColorscheme()
        self._updateXY()
        self._updateChart()
        self._updateTicks()

    def _updateXY(self):
        """Calculates all kinds of metrics for the x and y axis"""
        x_range_is_defined = self.options.axis.x.range is not None
        y_range_is_defined = self.options.axis.y.range is not None

        if not x_range_is_defined or not y_range_is_defined:
            stores = self._getDatasetsValues()

        # gather data for the x axis
        if x_range_is_defined:
            self.minxval, self.maxxval = self.options.axis.x.range
        else:
            xdata = [pair[0] for pair in reduce(lambda a, b: a + b, stores)]
            self.minxval = float(min(xdata))
            self.maxxval = float(max(xdata))
            if self.minxval * self.maxxval > 0 and self.minxval > 0:
                self.minxval = 0.0

        self.xrange = self.maxxval - self.minxval
        if self.xrange == 0:
            self.xscale = 1.0
        else:
            self.xscale = 1.0 / self.xrange

        # gather data for the y axis
        if y_range_is_defined:
            self.minyval, self.maxyval = self.options.axis.y.range
        else:
            ydata = [pair[1] for pair in reduce(lambda a, b: a + b, stores)]
            self.minyval = float(min(ydata))
            self.maxyval = float(max(ydata))
            if self.minyval * self.maxyval > 0 and self.minyval > 0:
                self.minyval = 0.0

        self.yrange = self.maxyval - self.minyval
        if self.yrange == 0:
            self.yscale = 1.0
        else:
            self.yscale = 1.0 / self.yrange

        if self.minyval * self.maxyval < 0:  # different signs
            self.origin = abs(self.minyval) * self.yscale
        else:
            self.origin = 0.0

    def _updateChart(self):
        raise NotImplementedError

    def _updateTicks(self):
        """Evaluates ticks for x and y axis.

        You should call _updateXY before because that method computes the
        values of xscale, minxval, yscale, and other attributes needed for
        this method.
        """
        stores = self._getDatasetsValues()

        # evaluate xTicks
        self.xticks = []
        if self.options.axis.x.ticks:
            for tick in self.options.axis.x.ticks:
                if not isinstance(tick, Option):
                    tick = Option(tick)
                if tick.label is None:
                    label = str(tick.v)
                else:
                    label = tick.label
                pos = self.xscale * (tick.v - self.minxval)
                if 0.0 <= pos <= 1.0:
                    self.xticks.append((pos, label))

        elif self.options.axis.x.interval > 0:
            interval = self.options.axis.x.interval
            label = (divmod(self.minxval, interval)[0] + 1) * interval
            pos = self.xscale * (label - self.minxval)
            prec = self.options.axis.x.tickPrecision
            while 0.0 <= pos <= 1.0:
                pretty_label = round(label, prec)
                if prec == 0:
                    pretty_label = int(pretty_label)
                self.xticks.append((pos, pretty_label))
                label += interval
                pos = self.xscale * (label - self.minxval)

        elif self.options.axis.x.tickCount > 0:
            uniqx = list(range(len(uniqueIndices(stores)) + 1))
            roughSeparation = self.xrange / self.options.axis.x.tickCount
            i = j = 0
            while i < len(uniqx) and j < self.options.axis.x.tickCount:
                if (uniqx[i] - self.minxval) >= (j * roughSeparation):
                    pos = self.xscale * (uniqx[i] - self.minxval)
                    if 0.0 <= pos <= 1.0:
                        self.xticks.append((pos, uniqx[i]))
                        j += 1
                i += 1

        # evaluate yTicks
        self.yticks = []
        if self.options.axis.y.ticks:
            for tick in self.options.axis.y.ticks:
                if not isinstance(tick, Option):
                    tick = Option(tick)
                if tick.label is None:
                    label = str(tick.v)
                else:
                    label = tick.label
                pos = 1.0 - (self.yscale * (tick.v - self.minyval))
                if 0.0 <= pos <= 1.0:
                    self.yticks.append((pos, label))

        elif self.options.axis.y.interval > 0:
            interval = self.options.axis.y.interval
            label = (divmod(self.minyval, interval)[0] + 1) * interval
            pos = 1.0 - (self.yscale * (label - self.minyval))
            prec = self.options.axis.y.tickPrecision
            while 0.0 <= pos <= 1.0:
                pretty_label = round(label, prec)
                if prec == 0:
                    pretty_label = int(pretty_label)
                self.yticks.append((pos, pretty_label))
                label += interval
                pos = 1.0 - (self.yscale * (label - self.minyval))

        elif self.options.axis.y.tickCount > 0:
            prec = self.options.axis.y.tickPrecision
            num = self.yrange / self.options.axis.y.tickCount
            if (num < 1 and prec == 0):
                roughSeparation = 1
            else:
                roughSeparation = round(num, prec)

            for i in range(self.options.axis.y.tickCount + 1):
                yval = self.minyval + (i * roughSeparation)
                pos = 1.0 - ((yval - self.minyval) * self.yscale)
                if 0.0 <= pos <= 1.0:
                    pretty_label = round(yval, prec)
                    if prec == 0:
                        pretty_label = int(pretty_label)
                    self.yticks.append((pos, pretty_label))

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
            surface_width, surface_height = self.getSurfaceSize()
            cx.rectangle(self.options.padding.left, self.options.padding.top,
                         surface_width - (self.options.padding.left
                                          + self.options.padding.right),
                         surface_height - (self.options.padding.top
                                           + self.options.padding.bottom))
            cx.fill()

        if self.options.background.lineColor:
            cx.set_source_rgb(*hex2rgb(self.options.background.lineColor))
            cx.set_line_width(self.options.axis.lineWidth)
            self._renderLines(cx)

        cx.restore()

    def _renderLines(self, cx):
        """Aux function for _renderBackground"""
        if self.options.axis.y.showLines and self.yticks:
            for tick in self.yticks:
                self._renderLine(cx, tick, False)
        if self.options.axis.x.showLines and self.xticks:
            for tick in self.xticks:
                self._renderLine(cx, tick, True)

    def _renderLine(self, cx, tick, horiz):
        """Aux function for _renderLines"""
        x1, x2, y1, y2 = (0, 0, 0, 0)
        if horiz:
            x1 = x2 = tick[0] * self.layout.chart.w + self.layout.chart.x
            y1 = self.layout.chart.y
            y2 = y1 + self.layout.chart.h
        else:
            x1 = self.layout.chart.x
            x2 = x1 + self.layout.chart.w
            y1 = y2 = tick[0] * self.layout.chart.h + self.layout.chart.y

        cx.new_path()
        cx.move_to(x1, y1)
        cx.line_to(x2, y2)
        cx.close_path()
        cx.stroke()

    def _renderChart(self, cx):
        raise NotImplementedError

    def _renderTick(self, cx, tick, x, y, x2, y2, rotate, text_position):
        """Aux method for _renderXTick and _renderYTick"""
        if callable(tick):
            return

        cx.new_path()
        cx.move_to(x, y)
        cx.line_to(x2, y2)
        cx.close_path()
        cx.stroke()
        cx.set_source_rgb(*hex2rgb('#000000'))
        cx.select_font_face(self.options.axis.tickFont,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cx.set_font_size(self.options.axis.tickFontSize)

        label = safe_unicode(tick[1], self.options.encoding)
        xb, yb, width, height, xa, ya = cx.text_extents(label)

        x, y = text_position

        if rotate:
            cx.save()
            cx.translate(x, y)
            cx.rotate(math.radians(rotate))
            x = -width / 2.0
            y = -height / 2.0
            cx.move_to(x - xb, y - yb)
            cx.show_text(label)
            cx.set_source_rgb(*hex2rgb(self.options.axis.lineColor))
            if self.debug:
                cx.rectangle(x, y, width, height)
                cx.stroke()
            cx.restore()
        else:
            x -= width / 2.0
            y -= height / 2.0
            cx.move_to(x - xb, y - yb)
            cx.show_text(label)
            cx.set_source_rgb(*hex2rgb(self.options.axis.lineColor))
            if self.debug:
                cx.rectangle(x, y, width, height)
                cx.stroke()

        return label

    def _renderYTick(self, cx, tick):
        """Aux method for _renderAxis"""
        x = self.layout.y_ticks.x + self.layout.y_ticks.w
        y = self.layout.y_ticks.y + tick[0] * self.layout.y_ticks.h

        text_position = ((self.layout.y_tick_labels.x
                          + self.layout.y_tick_labels.w / 2.0 - 5), y)

        return self._renderTick(cx, tick,
                                x, y,
                                x - self.options.axis.tickSize, y,
                                self.options.axis.y.rotate,
                                text_position)

    def _renderXTick(self, cx, tick):
        """Aux method for _renderAxis"""

        x = self.layout.x_ticks.x + tick[0] * self.layout.x_ticks.w
        y = self.layout.x_ticks.y

        text_position = (x, (self.layout.x_tick_labels.y + 5
                             + self.layout.x_tick_labels.h / 2.0))

        return self._renderTick(cx, tick,
                                x, y,
                                x, y + self.options.axis.tickSize,
                                self.options.axis.x.rotate,
                                text_position)

    def _renderAxisLabel(self, cx, label, x, y, vertical=False):
        cx.save()
        cx.select_font_face(self.options.axis.labelFont,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_BOLD)
        cx.set_font_size(self.options.axis.labelFontSize)
        cx.set_source_rgb(*hex2rgb(self.options.axis.labelColor))

        xb, yb, width, height, xa, ya = cx.text_extents(label)

        if vertical:
            y = y + width / 2.0
            cx.move_to(x - xb, y - yb)
            cx.translate(x, y)
            cx.rotate(-math.radians(90))
            cx.move_to(-xb, -yb)
            cx.show_text(label)
            if self.debug:
                cx.rectangle(0, 0, width, height)
                cx.stroke()
        else:
            x = x - width / 2.0
            cx.move_to(x - xb, y - yb)
            cx.show_text(label)
            if self.debug:
                cx.rectangle(x, y, width, height)
                cx.stroke()
        cx.restore()

    def _renderYAxisLabel(self, cx, label_text):
        label = safe_unicode(label_text, self.options.encoding)
        x = self.layout.y_label.x
        y = self.layout.y_label.y + self.layout.y_label.h / 2.0
        self._renderAxisLabel(cx, label, x, y, True)

    def _renderYAxis(self, cx):
        """Draws the vertical line represeting the Y axis"""
        cx.new_path()
        cx.move_to(self.layout.chart.x, self.layout.chart.y)
        cx.line_to(self.layout.chart.x,
                   self.layout.chart.y + self.layout.chart.h)
        cx.close_path()
        cx.stroke()

    def _renderXAxisLabel(self, cx, label_text):
        label = safe_unicode(label_text, self.options.encoding)
        x = self.layout.x_label.x + self.layout.x_label.w / 2.0
        y = self.layout.x_label.y
        self._renderAxisLabel(cx, label, x, y, False)

    def _renderXAxis(self, cx):
        """Draws the horizontal line representing the X axis"""
        cx.new_path()
        y = self.layout.chart.y + (1.0 - self.origin) * self.layout.chart.h
        cx.move_to(self.layout.chart.x, y)
        cx.line_to(self.layout.chart.x + self.layout.chart.w, y)
        cx.close_path()
        cx.stroke()

    def _renderAxis(self, cx):
        """Renders axis"""
        if self.options.axis.x.hide and self.options.axis.y.hide:
            return

        cx.save()
        cx.set_line_width(self.options.axis.lineWidth)

        if not self.options.axis.y.hide:
            if self.yticks:
                for tick in self.yticks:
                    self._renderYTick(cx, tick)

            if self.options.axis.y.label:
                self._renderYAxisLabel(cx, self.options.axis.y.label)

            cx.set_source_rgb(*hex2rgb(self.options.axis.lineColor))
            self._renderYAxis(cx)

        if not self.options.axis.x.hide:
            if self.xticks:
                for tick in self.xticks:
                    self._renderXTick(cx, tick)

            if self.options.axis.x.label:
                self._renderXAxisLabel(cx, self.options.axis.x.label)

            cx.set_source_rgb(*hex2rgb(self.options.axis.lineColor))
            self._renderXAxis(cx)

        cx.restore()

    def _renderTitle(self, cx):
        if self.options.title:
            cx.save()
            cx.select_font_face(self.options.titleFont,
                                cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_BOLD)
            cx.set_font_size(self.options.titleFontSize)
            cx.set_source_rgb(*hex2rgb(self.options.titleColor))

            title = safe_unicode(self.options.title, self.options.encoding)
            extents = cx.text_extents(title)
            title_width = extents[2]

            x = (self.layout.title.x
                 + self.layout.title.w / 2.0
                 - title_width / 2.0)
            y = self.layout.title.y - extents[1] - 10

            cx.move_to(x, y)
            cx.show_text(title)

            cx.restore()

    def _renderLegend(self, cx):
        """This function adds a legend to the chart"""
        if self.options.legend.hide:
            return

        surface_width, surface_height = self.getSurfaceSize()

        # Compute legend dimensions
        padding = 4
        bullet = 15
        width = 0
        height = padding
        keys = self._getDatasetsKeys()
        cx.select_font_face(self.options.legend.legendFont,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cx.set_font_size(self.options.legend.legendFontSize)
        for key in keys:
            key = safe_unicode(key, self.options.encoding)
            extents = cx.text_extents(key)
            width = max(extents[2], width)
            height += max(extents[3], bullet) + padding
        width = padding + bullet + padding + width + padding

        # Compute legend position
        legend = self.options.legend
        if legend.position.right is not None:
            legend.position.left = (surface_width
                                    - legend.position.right
                                    - width)
        if legend.position.bottom is not None:
            legend.position.top = (surface_height
                                   - legend.position.bottom
                                   - height)

        # Draw the legend
        cx.save()
        cx.rectangle(self.options.legend.position.left,
                     self.options.legend.position.top,
                     width, height)
        cx.set_source_rgba(1, 1, 1, self.options.legend.opacity)
        cx.fill_preserve()
        cx.set_line_width(self.options.legend.borderWidth)
        cx.set_source_rgb(*hex2rgb(self.options.legend.borderColor))
        cx.stroke()

        def drawKey(key, x, y, text_height):
            cx.rectangle(x, y, bullet, bullet)
            cx.set_source_rgb(*self.colorScheme[key])
            cx.fill_preserve()
            cx.set_source_rgb(0, 0, 0)
            cx.stroke()
            cx.move_to(x + bullet + padding,
                       y + bullet / 2.0 + text_height / 2.0)
            cx.show_text(key)

        cx.set_line_width(1)
        x = self.options.legend.position.left + padding
        y = self.options.legend.position.top + padding
        for key in keys:
            extents = cx.text_extents(key)
            drawKey(key, x, y, extents[3])
            y += max(extents[3], bullet) + padding

        cx.restore()


def uniqueIndices(arr):
    """Return a list with the indexes of the biggest element of arr"""
    return list(range(max([len(a) for a in arr])))


class Area(object):
    """Simple rectangle to hold an area coordinates and dimensions"""

    def __init__(self, x=0.0, y=0.0, w=0.0, h=0.0):
        self.x, self.y, self.w, self.h = x, y, w, h

    def __str__(self):
        msg = "<pycha.chart.Area@(%.2f, %.2f) %.2f x %.2f>"
        return  msg % (self.x, self.y, self.w, self.h)


def get_text_extents(cx, text, font, font_size, encoding):
    if text:
        cx.save()
        cx.select_font_face(font,
                            cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cx.set_font_size(font_size)
        safe_text = safe_unicode(text, encoding)
        extents = cx.text_extents(safe_text)
        cx.restore()
        return extents[2:4]
    return (0.0, 0.0)


class Layout(object):
    """Set of chart areas"""

    def __init__(self):
        self.title = Area()
        self.x_label = Area()
        self.y_label = Area()
        self.x_tick_labels = Area()
        self.y_tick_labels = Area()
        self.x_ticks = Area()
        self.y_ticks = Area()
        self.chart = Area()

        self._areas = (
            (self.title, (1, 126 / 255.0, 0)),  # orange
            (self.y_label, (41 / 255.0, 91 / 255.0, 41 / 255.0)),  # grey
            (self.x_label, (41 / 255.0, 91 / 255.0, 41 / 255.0)),  # grey
            (self.y_tick_labels, (0, 115 / 255.0, 0)),  # green
            (self.x_tick_labels, (0, 115 / 255.0, 0)),  # green
            (self.y_ticks, (229 / 255.0, 241 / 255.0, 18 / 255.0)),  # yellow
            (self.x_ticks, (229 / 255.0, 241 / 255.0, 18 / 255.0)),  # yellow
            (self.chart, (75 / 255.0, 75 / 255.0, 1.0)),  # blue
            )

    def update(self, cx, options, width, height, xticks, yticks):
        self.title.x = options.padding.left
        self.title.y = options.padding.top
        self.title.w = width - (options.padding.left + options.padding.right)
        self.title.h = get_text_extents(cx,
                                        options.title,
                                        options.titleFont,
                                        options.titleFontSize,
                                        options.encoding)[1]
        x_axis_label_height = get_text_extents(cx,
                                               options.axis.x.label,
                                               options.axis.labelFont,
                                               options.axis.labelFontSize,
                                               options.encoding)[1]
        y_axis_label_width = get_text_extents(cx,
                                              options.axis.y.label,
                                              options.axis.labelFont,
                                              options.axis.labelFontSize,
                                              options.encoding)[1]

        x_axis_tick_labels_height = self._getAxisTickLabelsSize(cx, options,
                                                                options.axis.x,
                                                                xticks)[1]
        y_axis_tick_labels_width = self._getAxisTickLabelsSize(cx, options,
                                                               options.axis.y,
                                                               yticks)[0]

        self.y_label.x = options.padding.left
        self.y_label.y = options.padding.top + self.title.h
        self.y_label.w = y_axis_label_width
        self.y_label.h = height - (options.padding.bottom
                                   + options.padding.top
                                   + x_axis_label_height
                                   + x_axis_tick_labels_height
                                   + options.axis.tickSize
                                   + self.title.h)
        self.x_label.x = (options.padding.left
                          + y_axis_label_width
                          + y_axis_tick_labels_width
                          + options.axis.tickSize)
        self.x_label.y = height - (options.padding.bottom
                                   + x_axis_label_height)
        self.x_label.w = width - (options.padding.left
                                  + options.padding.right
                                  + options.axis.tickSize
                                  + y_axis_label_width
                                  + y_axis_tick_labels_width)
        self.x_label.h = x_axis_label_height

        self.y_tick_labels.x = self.y_label.x + self.y_label.w
        self.y_tick_labels.y = self.y_label.y
        self.y_tick_labels.w = y_axis_tick_labels_width
        self.y_tick_labels.h = self.y_label.h

        self.x_tick_labels.x = self.x_label.x
        self.x_tick_labels.y = self.x_label.y - x_axis_tick_labels_height
        self.x_tick_labels.w = self.x_label.w
        self.x_tick_labels.h = x_axis_tick_labels_height

        self.y_ticks.x = self.y_tick_labels.x + self.y_tick_labels.w
        self.y_ticks.y = self.y_tick_labels.y
        self.y_ticks.w = options.axis.tickSize
        self.y_ticks.h = self.y_label.h

        self.x_ticks.x = self.x_tick_labels.x
        self.x_ticks.y = self.x_tick_labels.y - options.axis.tickSize
        self.x_ticks.w = self.x_label.w
        self.x_ticks.h = options.axis.tickSize

        self.chart.x = self.y_ticks.x + self.y_ticks.w
        self.chart.y = self.title.y + self.title.h
        self.chart.w = self.x_ticks.w
        self.chart.h = self.y_ticks.h

    def render(self, cx):

        def draw_area(area, r, g, b):
            cx.rectangle(area.x, area.y, area.w, area.h)
            cx.set_source_rgba(r, g, b, 0.5)
            cx.fill()

        cx.save()
        for area, color in self._areas:
            draw_area(area, *color)
        cx.restore()

    def _getAxisTickLabelsSize(self, cx, options, axis, ticks):
        cx.save()
        cx.select_font_face(options.axis.tickFont,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cx.set_font_size(options.axis.tickFontSize)

        max_width = max_height = 0.0
        if not axis.hide:
            extents = [cx.text_extents(safe_unicode(
                        tick[1], options.encoding,
                        ))[2:4]  # get width and height as a tuple
                       for tick in ticks]
            if extents:
                widths, heights = list(zip(*extents))
                max_width, max_height = max(widths), max(heights)
                if axis.rotate:
                    radians = math.radians(axis.rotate)
                    sin = math.sin(radians)
                    cos = math.cos(radians)
                    max_width, max_height = (
                        max_width * cos + max_height * sin,
                        max_width * sin + max_height * cos,
                        )
        cx.restore()
        return max_width, max_height


class Option(dict):
    """Useful dict that allow attribute-like access to its keys"""

    def __getattr__(self, name):
        if name in list(self.keys()):
            return self[name]
        else:
            raise AttributeError(name)

    def merge(self, other):
        """Recursive merge with other Option or dict object"""
        for key, value in list(other.items()):
            if key in self:
                if isinstance(self[key], Option):
                    self[key].merge(other[key])
                else:
                    self[key] = other[key]


DEFAULT_OPTIONS = Option(
    axis=Option(
        lineWidth=1.0,
        lineColor='#0f0000',
        tickSize=3.0,
        labelColor='#666666',
        labelFont='Tahoma',
        labelFontSize=9,
        tickFont='Tahoma',
        tickFontSize=9,
        x=Option(
            hide=False,
            ticks=None,
            tickCount=10,
            tickPrecision=1,
            range=None,
            rotate=None,
            label=None,
            interval=0,
            showLines=False,
        ),
        y=Option(
            hide=False,
            ticks=None,
            tickCount=10,
            tickPrecision=1,
            range=None,
            rotate=None,
            label=None,
            interval=0,
            showLines=True,
        ),
    ),
    background=Option(
        hide=False,
        baseColor=None,
        chartColor='#f5f5f5',
        lineColor='#ffffff',
        lineWidth=1.5,
    ),
    legend=Option(
        opacity=0.8,
        borderColor='#000000',
        borderWidth=2,
        hide=False,
        legendFont='Tahoma',
        legendFontSize=9,
        position=Option(top=20, left=40, bottom=None, right=None),
    ),
    padding=Option(
        left=10,
        right=10,
        top=10,
        bottom=10,
    ),
    stroke=Option(
        color='#000000',
        hide=False,
        shadow=True,
        width=1
    ),
    yvals=Option(
        show=False,
        inside=False,
        fontSize=11,
        fontColor='#000000',
        skipSmallValues=True,
        snapToOrigin=False,
        renderer=None
    ),
    fillOpacity=1.0,
    shouldFill=True,
    barWidthFillFraction=0.75,
    pieRadius=0.4,
    colorScheme=Option(
        name='gradient',
        args=Option(
            initialColor=DEFAULT_COLOR,
            colors=None,
            ),
    ),
    title=None,
    titleColor='#000000',
    titleFont='Tahoma',
    titleFontSize=12,
    encoding='utf-8',
)
