# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Graphene
import gi

gi.require_version('Gsk', '4.0')
from gi.repository import Gsk

try:
    gi.require_version('Gtk4LayerShell', '1.0')
    from gi.repository import Gtk4LayerShell
except ValueError:
    Gtk4LayerShell = None

from sugar4.graphics import style


def _get_screen_size():
    display = Gdk.Display.get_default()
    if display:
        monitors = display.get_monitors()
        if monitors and monitors.get_n_items() > 0:
            geometry = monitors.get_item(0).get_geometry()
            return geometry.width, geometry.height
    return 1024, 768


class FrameContainer(Gtk.Widget):
    """A container class for frame panel rendering. Hosts a child 'box' where
    frame elements can be added. Excludes grid-sized squares at each end
    of the frame panel, and a space alongside the inside of the screen where
    a border is drawn."""

    __gtype_name__ = 'SugarFrameContainer'

    def __init__(self, position):
        super().__init__()
        self._position = position

        if self.is_vertical():
            self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        else:
            self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.set_parent(self)

    def do_dispose(self):
        if self._box:
            self._box.unparent()
            self._box = None
        super().do_dispose()

    def get_child_box(self):
        return self._box

    def is_vertical(self):
        return self._position in (Gtk.PositionType.LEFT,
                                  Gtk.PositionType.RIGHT)

    def do_snapshot(self, snapshot):
        width = self.get_width()
        height = self.get_height()

        # Render CSS background (e.g. framewindow background color)
        context = self.get_style_context()
        snapshot.render_background(context, 0, 0, width, height)

        # Draw the inner border as a rectangle
        color = Gdk.RGBA()
        color.parse(style.COLOR_BUTTON_GREY.get_svg())

        if self.is_vertical():
            x = style.GRID_CELL_SIZE \
                if self._position == Gtk.PositionType.LEFT else 0
            y = style.GRID_CELL_SIZE
            rect_width = style.LINE_WIDTH
            rect_height = height - (style.GRID_CELL_SIZE * 2)
        else:
            x = style.GRID_CELL_SIZE
            y = style.GRID_CELL_SIZE \
                if self._position == Gtk.PositionType.TOP else 0
            rect_height = style.LINE_WIDTH
            rect_width = width - (style.GRID_CELL_SIZE * 2)

        if rect_width > 0 and rect_height > 0:
            rect = Graphene.Rect()
            rect.init(x, y, rect_width, rect_height)
            snapshot.append_color(color, rect)

        if self._box:
            self.snapshot_child(self._box, snapshot)

    def do_measure(self, orientation, for_size):
        if self._box:
            self._box.measure(orientation, for_size)
            
        sw, sh = _get_screen_size()
        if self.is_vertical():
            if orientation == Gtk.Orientation.VERTICAL:
                return sh, sh, -1, -1
            else:
                w = style.GRID_CELL_SIZE + style.LINE_WIDTH
                return w, w, -1, -1
        else:
            if orientation == Gtk.Orientation.HORIZONTAL:
                return sw, sw, -1, -1
            else:
                h = style.GRID_CELL_SIZE + style.LINE_WIDTH
                return h, h, -1, -1

    def do_size_allocate(self, width, height, baseline):
        # exclude grid squares at two ends of the frame
        # allocate remaining space to child box, minus the space needed for
        # drawing the border
        allocation = Gdk.Rectangle()
        if self.is_vertical():
            allocation.x = 0 if self._position == Gtk.PositionType.LEFT \
                else style.LINE_WIDTH
            allocation.y = style.GRID_CELL_SIZE
            allocation.width = max(0, width - style.LINE_WIDTH)
            allocation.height = max(0, height - (style.GRID_CELL_SIZE * 2))
        else:
            allocation.x = style.GRID_CELL_SIZE
            allocation.y = 0 if self._position == Gtk.PositionType.TOP \
                else style.LINE_WIDTH
            allocation.width = max(0, width - (style.GRID_CELL_SIZE * 2))
            allocation.height = max(0, height - style.LINE_WIDTH)

        if self._box:
            transform = Gsk.Transform.new().translate(Graphene.Point().init(allocation.x, allocation.y))
            self._box.allocate(allocation.width, allocation.height, baseline, transform)


class FrameWindow(Gtk.Revealer):
    """A frame panel that slides in/out using Gtk.Revealer.

    GTK3 used floating Gtk.Window objects that were moved with window.move().
    In GTK4, Gtk.Revealer is the correct widget for slide-in/out animations.
    It handles clipping, animation, and positioning natively.

    The Revealer wraps a FrameContainer (the actual drawing surface).
    It is added to the shell's Gtk.Overlay as an overlay child, positioned
    at its respective screen edge via valign/halign.
    """
    __gtype_name__ = 'SugarFrameWindow'

    def __init__(self, position):
        # Choose transition type based on panel edge
        if position == Gtk.PositionType.TOP:
            transition = Gtk.RevealerTransitionType.SLIDE_DOWN
        elif position == Gtk.PositionType.BOTTOM:
            transition = Gtk.RevealerTransitionType.SLIDE_UP
        elif position == Gtk.PositionType.LEFT:
            transition = Gtk.RevealerTransitionType.SLIDE_RIGHT
        else:  # RIGHT
            transition = Gtk.RevealerTransitionType.SLIDE_LEFT

        super().__init__(
            transition_type=transition,
            transition_duration=0,  # 0ms slide animation (driven by frame.py timer manually)
            reveal_child=False,
        )

        self.hover = False
        self.size = style.GRID_CELL_SIZE + style.LINE_WIDTH
        self._position = position

        # Shortcut controller
        self.shortcut_controller = Gtk.ShortcutController.new()
        self.shortcut_controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        self.add_controller(self.shortcut_controller)
        self.sugar_accel_group = self.shortcut_controller

        # Hover tracking
        controller = Gtk.EventControllerMotion.new()
        controller.connect('enter', self._enter_notify_cb)
        controller.connect('leave', self._leave_notify_cb)
        self.add_controller(controller)

        # The actual drawing surface
        self._container = FrameContainer(position)
        self._container.add_css_class('framewindow')
        self.set_child(self._container)

        # Position the revealer at its screen edge via Overlay alignment
        if position == Gtk.PositionType.TOP:
            self.set_valign(Gtk.Align.START)
            self.set_halign(Gtk.Align.FILL)
        elif position == Gtk.PositionType.BOTTOM:
            self.set_valign(Gtk.Align.END)
            self.set_halign(Gtk.Align.FILL)
        elif position == Gtk.PositionType.LEFT:
            self.set_valign(Gtk.Align.FILL)
            self.set_halign(Gtk.Align.START)
        elif position == Gtk.PositionType.RIGHT:
            self.set_valign(Gtk.Align.FILL)
            self.set_halign(Gtk.Align.END)

        self._update_size()

        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            if monitors:
                monitors.connect('items-changed', self._size_changed_cb)

    def set_margin(self, margin):
        """Called by frame.py animation with values from -size (hidden) to 0 (visible).

        We map this to Revealer reveal_child: when margin reaches 0, reveal;
        when margin is < 0, hide.

        The actual animation is driven externally by frame.py's _Animation
        which updates position continuously. We use the Revealer's own
        animation only as a backup for instant show/hide.
        """
        # Convert margin (-size..0) to fraction (0..1)
        fraction = (margin + self.size) / self.size  # 0 when hidden, 1 when visible
        reveal = fraction > 0.01
        if self.get_reveal_child() != reveal:
            self.set_reveal_child(reveal)

    def append(self, child, expand=True, fill=True):
        if expand:
            if self._container.is_vertical():
                child.set_vexpand(True)
            else:
                child.set_hexpand(True)
        if not fill:
            if self._container.is_vertical():
                child.set_valign(Gtk.Align.CENTER)
            else:
                child.set_halign(Gtk.Align.CENTER)
        self._container.get_child_box().append(child)

    def _update_size(self):
        sw, sh = _get_screen_size()
        if self._position in (Gtk.PositionType.TOP, Gtk.PositionType.BOTTOM):
            self._container.set_size_request(sw, self.size)
        else:
            self._container.set_size_request(self.size, sh)

    def _enter_notify_cb(self, controller, x, y):
        self.hover = True

    def _leave_notify_cb(self, controller):
        self.hover = False

    def _size_changed_cb(self, monitors, position, removed, added):
        self._update_size()
