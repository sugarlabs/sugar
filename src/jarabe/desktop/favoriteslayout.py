# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2010 Sugar Labs
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

import logging
import math
import hashlib
from gettext import gettext as _

from gi.repository import Gtk

from sugar.graphics import style

from jarabe.model import bundleregistry
from jarabe.desktop.grid import Grid


_logger = logging.getLogger('FavoritesLayout')

_CELL_SIZE = 4
_BASE_SCALE = 1000
_INTERMEDIATE_B = (style.STANDARD_ICON_SIZE + style.SMALL_ICON_SIZE) / 2
_INTERMEDIATE_A = (style.STANDARD_ICON_SIZE + _INTERMEDIATE_B) / 2
_INTERMEDIATE_C = (_INTERMEDIATE_B + style.SMALL_ICON_SIZE) / 2
_ICON_SIZES = [style.MEDIUM_ICON_SIZE, style.STANDARD_ICON_SIZE,
               _INTERMEDIATE_A, _INTERMEDIATE_B, _INTERMEDIATE_C,
               style.SMALL_ICON_SIZE]


class Layout(object):
    def __init__(self):
        pass

    def remove(self, child):
        pass

    def allocate_children(self, allocation, children):
        pass


class ViewLayout(Layout):
    def __init__(self):
        self._grid = None

    def setup(self, allocation, owner_icon, activity_icon=None):
        if self._grid is not None:
            return
        self._grid = Grid(int(allocation.width / _CELL_SIZE),
                          int(allocation.height / _CELL_SIZE))
        self._grid.connect('child-changed', self.__grid_child_changed_cb)
        self._allocate_owner_icon(allocation, owner_icon, activity_icon)

    def _allocate_owner_icon(self, allocation, owner_icon, activity_icon):
        # add owner icon to the grid, precisely centered on the screen
        # if not None, add an activity icon directly below the owner icon
        owner_width, owner_height = owner_icon.size_request()
        height = allocation.height + allocation.y
        width = allocation.width

        # Find vertical center point of screen
        y = height / 2

        # This container may be offset from the top by a certain amount
        # (e.g. for a toolbar at the top of the screen). Adjust the
        # center-point for that
        y -= allocation.y

        # Now subtract half of the owner height. This gives us the y
        # coordinate for the top of the owner icon.
        y -= owner_height / 2

        # calculate x coordinate and create allocation
        x = (width - owner_width) / 2
        owner_icon_allocation = (x, allocation.y + y,
                                                  owner_width, owner_height)
        owner_icon.size_allocate(owner_icon_allocation)

        # Determine grid coordinates and add to grid
        owner_grid_width, owner_grid_height = \
            self._get_child_grid_size(owner_icon)
        x = int(x / float(_CELL_SIZE))
        y = int(y / float(_CELL_SIZE))
        self._grid.add(owner_icon, owner_grid_width, owner_grid_height,
                       x, y, locked=True)

        if activity_icon is None:
            return

        # Position the current activity below the XO icon
        # FIXME must ensure we cross into next grid cell here..
        activity_width, activity_height = activity_icon.size_request()
        x = (width - activity_width) / 2
        y = owner_icon_allocation.y + owner_height
        activity_icon_allocation = (x, y, activity_width,
                                                     activity_height)
        activity_icon.size_allocate(activity_icon_allocation)

        # Determine grid coordinates and add to grid
        activity_grid_width, activity_grid_height = \
            self._get_child_grid_size(activity_icon)
        x = int(x / float(_CELL_SIZE))
        y = int(y / float(_CELL_SIZE))
        self._grid.add(activity_icon, activity_grid_width,
                       activity_grid_height, x, y, locked=True)

    def allocate_children(self, allocation, children):
        pass

    def move(self, child, x, y, allocation=None):
        self._grid.move(child, x / _CELL_SIZE, y / _CELL_SIZE, locked=True)
        width, height = child.size_request()
        rect = self._grid.get_child_rect(child)
        child_allocation = (int(round(rect.x * _CELL_SIZE)),
                                             int(round(rect.y * _CELL_SIZE)),
                                             width,
                                             height)
        child.size_allocate(child_allocation)

    def _get_child_grid_size(self, child):
        width, height = child.size_request()
        width = math.ceil(width / _CELL_SIZE)
        height = math.ceil(height / _CELL_SIZE)
        return int(width), int(height)

    def __grid_child_changed_cb(self, grid, child):
        width, height = child.size_request()
        rect = self._grid.get_child_rect(child)
        child_allocation = (int(round(rect.x * _CELL_SIZE)),
                                             int(round(rect.y * _CELL_SIZE)),
                                             width,
                                             height)
        child.size_allocate(child_allocation)


class SpreadLayout(ViewLayout):
    def __init__(self):
        ViewLayout.__init__(self)

    def remove(self, child):
        if self._grid is None:
            # the Grid is created during allocation time, so it might not
            # exist yet when this method is called, SL #3814
            return

        if self._grid.is_in_grid(child):
            self._grid.remove(child)

    def allocate_children(self, allocation, children):
        for child in children:
            if not self._grid.is_in_grid(child):
                width, height = self._get_child_grid_size(child)
                self._grid.add(child, width, height, None, None, locked=False)

            width, height = child.size_request()
            rect = self._grid.get_child_rect(child)
            x = int(round(rect.x * _CELL_SIZE))
            y = int(round(rect.y * _CELL_SIZE)) + allocation.y
            child_allocation = (x, y, width, height)
            child.size_allocate(child_allocation)


class RandomLayout(SpreadLayout):
    """Lay out icons randomly; try to nudge them around to resolve overlaps."""

    __gtype_name__ = 'RandomLayout'

    icon_name = 'view-freeform'
    """Name of icon used in home view dropdown palette."""

    key = 'random-layout'
    """String used in profile to represent this view."""

    # TRANS: label for the freeform layout in the favorites view
    palette_name = _('Freeform')
    """String used to identify this layout in home view dropdown palette."""

    def __init__(self):
        SpreadLayout.__init__(self)
        self.fixed_positions = {}

    def _add_fixed_position(self, icon, allocation, locked=False):
        if not hasattr(type(icon), 'fixed_position'):
            logging.debug('Icon without fixed_position: %r', icon)
            return

        icon.props.pixel_size = max(icon.props.pixel_size,
                                    style.STANDARD_ICON_SIZE)

        relative_x, relative_y = icon.fixed_position
        if relative_x < 0 or relative_y < 0:
            logging.debug('Icon out of bounds: %r', icon)
            return

        self.fixed_positions[icon] = \
                (int(relative_x * _BASE_SCALE / float(allocation.width)),
                 int(relative_y * _BASE_SCALE / float(allocation.height)))

    def allocate_children(self, allocation, children):
        for child in children:
            child_width, child_height = child.size_request()
            if not self._grid.is_in_grid(child):
                self._add_fixed_position(child, allocation)

                if child in self.fixed_positions:
                    x, y = self.fixed_positions[child]
                    x = min(x, allocation.width - child_width)
                    y = min(y, allocation.height - child_height)
                elif hasattr(child, 'get_bundle_id'):
                    name_hash = hashlib.md5(child.get_bundle_id())
                    x = int(name_hash.hexdigest()[:5], 16) % \
                        (allocation.width - child_width)
                    y = int(name_hash.hexdigest()[-5:], 16) % \
                        (allocation.height - child_height)
                else:
                    x = None
                    y = None

                if x is None or y is None:
                    self._grid.add(child, child_width / _CELL_SIZE,
                                   child_height / _CELL_SIZE)
                else:
                    self._grid.add(child, child_width / _CELL_SIZE,
                                   child_height / _CELL_SIZE,
                                   x / _CELL_SIZE, y / _CELL_SIZE)

            rect = self._grid.get_child_rect(child)
            x = int(round(rect.x * _CELL_SIZE))
            y = int(round(rect.y * _CELL_SIZE)) + allocation.y
            child_allocation = (x, y,
                                                 child_width, child_height)
            child.size_allocate(child_allocation)

    def move_icon(self, child, x, y, allocation):
        ViewLayout.move(self, child, x, y)

        if not (hasattr(child, 'get_bundle_id') and
                hasattr(child, 'get_version')):
            logging.debug('Not an activity icon %r', child)
            return

        registry = bundleregistry.get_registry()
        registry.set_bundle_position(
            child.get_bundle_id(), child.get_version(),
                x * allocation.width / float(_BASE_SCALE),
                y * allocation.height / float(_BASE_SCALE))
        self.fixed_positions[child] = (x, y)


_MINIMUM_RADIUS = style.XLARGE_ICON_SIZE / 2 + style.DEFAULT_SPACING + \
        style.STANDARD_ICON_SIZE * 2
_MAXIMUM_RADIUS = (Gdk.Screen.height() - style.GRID_CELL_SIZE) / 2 - \
        style.STANDARD_ICON_SIZE - style.DEFAULT_SPACING
_ICON_SPACING_FACTORS = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0]
_SPIRAL_SPACING_FACTORS = [1.5, 1.5, 1.5, 1.4, 1.3, 1.2]
_MIMIMUM_RADIUS_ENCROACHMENT = 0.75
_INITIAL_ANGLE = math.pi


class RingLayout(ViewLayout):
    """Lay out icons in a ring or spiral around the XO man."""

    __gtype_name__ = 'RingLayout'
    icon_name = 'view-radial'
    """Name of icon used in home view dropdown palette."""
    key = 'ring-layout'
    """String used in profile to represent this view."""
    # TRANS: label for the ring layout in the favorites view
    palette_name = _('Ring')
    """String used to identify this layout in home view dropdown palette."""

    def __init__(self):
        ViewLayout.__init__(self)
        self._spiral_mode = False

    def _calculate_radius_and_icon_size(self, children_count):
        """ Adjust the ring or spiral radius and icon size as needed. """
        self._spiral_mode = False
        distance = style.MEDIUM_ICON_SIZE + style.DEFAULT_SPACING * \
            _ICON_SPACING_FACTORS[_ICON_SIZES.index(style.MEDIUM_ICON_SIZE)]
        radius = max(children_count * distance / (2 * math.pi),
                     _MINIMUM_RADIUS)
        if radius < _MAXIMUM_RADIUS:
            return radius, style.MEDIUM_ICON_SIZE

        distance = style.STANDARD_ICON_SIZE + style.DEFAULT_SPACING * \
            _ICON_SPACING_FACTORS[_ICON_SIZES.index(style.STANDARD_ICON_SIZE)]
        radius = max(children_count * distance / (2 * math.pi),
                     _MINIMUM_RADIUS)
        if radius < _MAXIMUM_RADIUS:
            return radius, style.STANDARD_ICON_SIZE

        self._spiral_mode = True
        icon_size = style.STANDARD_ICON_SIZE
        angle_, radius = self._calculate_angle_and_radius(children_count,
                                                          icon_size)
        while radius > _MAXIMUM_RADIUS:
            i = _ICON_SIZES.index(icon_size)
            if i < len(_ICON_SIZES) - 1:
                icon_size = _ICON_SIZES[i + 1]
                angle_, radius = self._calculate_angle_and_radius(
                    children_count, icon_size)
            else:
                break
        return radius, icon_size

    def _calculate_position(self, radius, icon_size, icon_index,
                            children_count, width, height,
                            sin=math.sin, cos=math.cos):
        """ Calculate an icon position on a circle or a spiral. """
        if self._spiral_mode:
            angle, radius = self._calculate_angle_and_radius(icon_index,
                                                             icon_size)
            x, y = self._convert_from_polar_to_cartesian(angle, radius,
                                                         icon_size,
                                                         width, height)
        else:
            angle = icon_index * (2 * math.pi / children_count) - math.pi / 2
            x = radius * cos(angle) + (width - icon_size) / 2
            y = radius * sin(angle) + (height - icon_size - \
                                       (style.GRID_CELL_SIZE / 2)) / 2
        return int(x), int(y)

    def _convert_from_polar_to_cartesian(self, angle, radius, icon_size, width,
                                         height):
        """ Convert angle, radius to x, y """
        x = int(math.sin(angle) * radius)
        y = int(math.cos(angle) * radius)
        x = - x + (width - icon_size) / 2
        y = y + (height - icon_size - (style.GRID_CELL_SIZE / 2)) / 2
        return x, y

    def _calculate_angle_and_radius(self, icon_count, icon_size):
        """ Based on icon_count and icon_size, calculate radius and angle. """
        spiral_spacing = _SPIRAL_SPACING_FACTORS[_ICON_SIZES.index(icon_size)]
        icon_spacing = icon_size + style.DEFAULT_SPACING * \
            _ICON_SPACING_FACTORS[_ICON_SIZES.index(icon_size)]
        angle = _INITIAL_ANGLE
        radius = _MINIMUM_RADIUS - (icon_size * _MIMIMUM_RADIUS_ENCROACHMENT)
        for i_ in range(icon_count):
            circumference = radius * 2 * math.pi
            n = circumference / icon_spacing
            angle += (2 * math.pi / n)
            radius += (float(icon_spacing) * spiral_spacing / n)
        return angle, radius

    def allocate_children(self, allocation, children):
        radius, icon_size = self._calculate_radius_and_icon_size(len(children))

        children.sort(self.compare_activities)
        for n in range(len(children)):
            child = children[n]

            x, y = self._calculate_position(radius, icon_size, n,
                                            len(children), allocation.width,
                                            allocation.height)
            child.size_request()
            child.set_size(icon_size)
            child_allocation = (allocation.x + x,
                                                 allocation.y + y,
                                                 icon_size, icon_size)
            child.size_allocate(child_allocation)

    def compare_activities(self, icon_a, icon_b):
        if hasattr(icon_a, 'installation_time') and \
                hasattr(icon_b, 'installation_time'):
            return int(icon_b.installation_time - icon_a.installation_time)
        else:
            return 0


_SUNFLOWER_CONSTANT = style.STANDARD_ICON_SIZE * .75
"""Chose a constant such that STANDARD_ICON_SIZE icons are nicely spaced."""

_SUNFLOWER_OFFSET = \
    math.pow((style.XLARGE_ICON_SIZE / 2 + style.STANDARD_ICON_SIZE) /
             _SUNFLOWER_CONSTANT, 2)
"""
Compute a starting index for the `SunflowerLayout` which leaves space for
the XO man in the center.  Since r = _SUNFLOWER_CONSTANT * sqrt(n),
solve for n when r is (XLARGE_ICON_SIZE + STANDARD_ICON_SIZE)/2.
"""

_GOLDEN_RATIO = 1.6180339887498949
"""
Golden ratio: http://en.wikipedia.org/wiki/Golden_ratio
Calculation: (math.sqrt(5) + 1) / 2
"""

_SUNFLOWER_ANGLE = 2.3999632297286531
"""
The sunflower angle is approximately 137.5 degrees.
This is the golden angle: http://en.wikipedia.org/wiki/Golden_angle
Calculation: math.radians(360) / ( _GOLDEN_RATIO * _GOLDEN_RATIO )
"""


class SunflowerLayout(RingLayout):
    """Spiral layout based on Fibonacci ratio in phyllotaxis.

    See http://algorithmicbotany.org/papers/abop/abop-ch4.pdf
    for details of Vogel's model of florets in a sunflower head."""

    __gtype_name__ = 'SunflowerLayout'

    icon_name = 'view-spiral'
    """Name of icon used in home view dropdown palette."""

    key = 'spiral-layout'
    """String used in profile to represent this view."""

    # TRANS: label for the spiral layout in the favorites view
    palette_name = _('Spiral')
    """String used to identify this layout in home view dropdown palette."""

    def __init__(self):
        RingLayout.__init__(self)
        self.skipped_indices = []

    def _calculate_radius_and_icon_size(self, children_count):
        """Stub out this method; not used in `SunflowerLayout`."""
        return None, style.STANDARD_ICON_SIZE

    def adjust_index(self, i):
        """Skip floret indices which end up outside the desired bounding box.
        """
        for idx in self.skipped_indices:
            if i < idx:
                break
            i += 1
        return i

    def _calculate_position(self, radius, icon_size, oindex, children_count,
                            width, height, sin=math.sin, cos=math.cos):
        """Calculate the position of sunflower floret number 'oindex'.
        If the result is outside the bounding box, use the next index which
        is inside the bounding box."""

        while True:

            index = self.adjust_index(oindex)

            # tweak phi to get a nice gap lined up where the "active activity"
            # icon is, below the central XO man.
            phi = index * _SUNFLOWER_ANGLE + math.radians(-130)

            # we offset index when computing r to make space for the XO man.
            r = _SUNFLOWER_CONSTANT * math.sqrt(index + _SUNFLOWER_OFFSET)

            # x,y are the top-left corner of the icon, so remove icon_size
            # from width/height to compensate.  y has an extra GRID_CELL_SIZE/2
            # removed to make room for the "active activity" icon.
            x = r * cos(phi) + (width - icon_size) / 2
            y = r * sin(phi) + (height - icon_size - \
                                (style.GRID_CELL_SIZE / 2)) / 2

            # skip allocations outside the allocation box.
            # give up once we can't fit
            if r < math.hypot(width / 2, height / 2):
                if y < 0 or y > (height - icon_size) or \
                       x < 0 or x > (width - icon_size):
                    self.skipped_indices.append(index)
                    # try again
                    continue

            return int(x), int(y)


class BoxLayout(RingLayout):
    """Lay out icons in a square around the XO man."""

    __gtype_name__ = 'BoxLayout'

    icon_name = 'view-box'
    """Name of icon used in home view dropdown palette."""

    key = 'box-layout'
    """String used in profile to represent this view."""

    # TRANS: label for the box layout in the favorites view
    palette_name = _('Box')
    """String used to identify this layout in home view dropdown palette."""

    def __init__(self):
        RingLayout.__init__(self)

    def _calculate_position(self, radius, icon_size, index, children_count,
                            width, height, sin=None, cos=None):

        # use "orthogonal" versions of cos and sin in order to square the
        # circle and turn the 'ring view' into a 'box view'
        def cos_d(d):
            while d < 0:
                d += 360
            if d < 45:
                return 1
            if d < 135:
                return (90 - d) / 45.
            if d < 225:
                return -1
            # mirror around 180
            return cos_d(360 - d)

        cos = lambda r: cos_d(math.degrees(r))
        sin = lambda r: cos_d(math.degrees(r) - 90)

        return RingLayout._calculate_position(self, radius, icon_size, index,
                                              children_count, width, height,
                                              sin=sin, cos=cos)


class TriangleLayout(RingLayout):
    """Lay out icons in a triangle around the XO man."""

    __gtype_name__ = 'TriangleLayout'

    icon_name = 'view-triangle'
    """Name of icon used in home view dropdown palette."""

    key = 'triangle-layout'
    """String used in profile to represent this view."""

    # TRANS: label for the box layout in the favorites view
    palette_name = _('Triangle')
    """String used to identify this layout in home view dropdown palette."""

    def __init__(self):
        RingLayout.__init__(self)

    def _calculate_radius_and_icon_size(self, children_count):
        # use slightly larger minimum radius than parent, because sides
        # of triangle come awful close to the center.
        radius, icon_size = \
            RingLayout._calculate_radius_and_icon_size(self, children_count)
        return max(radius, _MINIMUM_RADIUS + style.MEDIUM_ICON_SIZE), icon_size

    def _calculate_position(self, radius, icon_size, index, children_count,
                            width, height, sin=math.sin, cos=math.cos):
        # tweak cos and sin in order to make the 'ring' into an equilateral
        # triangle.

        def cos_d(d):
            while d < -90:
                d += 360
            if d <= 30:
                return (d + 90) / 120.
            if d <= 90:
                return (90 - d) / 60.
            # mirror around 90
            return -cos_d(180 - d)

        sqrt_3 = math.sqrt(3)

        def sin_d(d):
            while d < -90:
                d += 360
            if d <= 30:
                return ((d + 90) / 120.) * sqrt_3 - 1
            if d <= 90:
                return sqrt_3 - 1
            # mirror around 90
            return sin_d(180 - d)

        cos = lambda r: cos_d(math.degrees(r))
        sin = lambda r: sin_d(math.degrees(r))

        return RingLayout._calculate_position(self, radius, icon_size, index,
                                              children_count, width, height,
                                              sin=sin, cos=cos)
