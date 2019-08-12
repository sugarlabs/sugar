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

from jarabe.util.sugarpycha.line import LineChart


class ScatterplotChart(LineChart):

    def _renderChart(self, cx):
        """Renders a scatterplot"""

        def drawSymbol(point, size):
            ox = point.x * self.layout.chart.w + self.layout.chart.x
            oy = point.y * self.layout.chart.h + self.layout.chart.y
            cx.arc(ox, oy, size, 0.0, 2 * math.pi)
            cx.fill()

        for key in self._getDatasetsKeys():
            cx.set_source_rgb(*self.colorScheme[key])
            for point in self.points:
                if point.name == key:
                    drawSymbol(point, self.options.stroke.width)
