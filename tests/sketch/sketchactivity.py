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

import gtk
import gobject
import os
import logging

from sugar.p2p import MostlyReliablePipe
from sugar.p2p.Stream import Stream

from sugar.presence import PresenceService
from sugar.activity.Activity import Activity
from sugar.chat.sketchpad import SketchPad
from sugar.chat.sketchpad import Sketch
from sugar.graphics.xocolor import XoColor
from sugar import profile

class NetworkController(gobject.GObject):
    __gsignals__ = {
        'new-path':(gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                   ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
    }

    def __init__(self, parent, ps_owner):
        gobject.GObject.__init__(self)
        self._parent = parent
        self._parent.connect('buddy-joined', self._buddy_joined)
        self._parent.connect('buddy-left', self._buddy_left)
        self._stream = None
        self._stream_writer = None
        self._joined_buddies = {}  # IP address -> buddy
        self._ps_owner = ps_owner

    def init_stream(self, service):
        self._stream = Stream.new_from_service(service)
        self._stream.set_data_listener(self._recv_message)
        self._stream_writer = self._stream.new_writer()

    def _recv_message(self, address, msg):
        # Ignore multicast messages from ourself
        if self._ps_owner and address == self._ps_owner.get_ip4_address():
            return

        # Ensure the message comes from somebody in this activity
        if not self._joined_buddies.has_key(address):
            logging.debug("Message from unjoined buddy.")
            return

        # Convert the points to an array and send to the sketchpad
        points = []
        msg = msg.strip()
        split_coords = msg.split(" ")
        for item in split_coords:
            x = 0
            y = 0
            try:
                (x, y) = item.split(",")
                x = float(x)
                y = float(y)
            except ValueError:
                continue
            if x < 0 or y < 0:
                continue
            points.append((x, y))

        buddy = self._joined_buddies[address]
        self.emit("new-path", buddy, points)

    def _buddy_joined(self, widget, activity, buddy, activity_type):
        activity_service = buddy.get_service_of_type(activity_type, activity)
        if not activity_service:
            logging.debug("Buddy Joined, but could not get activity service " \
                    "of %s" % activity_type)
            return

        address = activity_service.get_source_address()
        port = activity_service.get_port()
        if not address or not port:
            logging.debug("Buddy Joined, but could not get address/port from" \
                        " activity service %s" % activity_type)
            return
        if not self._joined_buddies.has_key(address):
            logging.debug("Buddy joined: %s (%s)" % (address, port))
            self._joined_buddies[address] = buddy

    def _buddy_left(self, widget, activity, buddy, activity_type):
        buddy_key = None
        for (key, value) in self._joined_buddies.items():
            if value == buddy:
                buddy_key = key
                break
        if buddy_key:
            del self._joined_buddies[buddy_key]

    def new_local_sketch(self, path):
        """ Receive an array of point tuples the local user created """
        cmd = ""
        # Convert points into the wire format
        for point in path:
            cmd = cmd + "%d,%d " % (point[0], point[1])

        # If there were no points, or we aren't in a shared activity yet,
        # don't send anything
        if not len(cmd) or not self._stream_writer:
            return

        # Send the points to other buddies
        self._stream_writer.write(cmd)

def _html_to_rgb_color(colorstring):
    """ converts #RRGGBB to cairo-suitable floats"""
    colorstring = colorstring.strip()
    while colorstring[0] == '#':
        colorstring = colorstring[1:]
    r = int(colorstring[:2], 16)
    g = int(colorstring[2:4], 16)
    b = int(colorstring[4:6], 16)
    color = ((float(r) / 255.0), (float(g) / 255.0), (float(b) / 255.0))
    return color


class SharedSketchPad(SketchPad.SketchPad):
    def __init__(self, net_controller, color):
        SketchPad.SketchPad.__init__(self, bgcolor=(1.0, 0.984313725, 0.560784314))
        self._net_controller = net_controller
        self._user_color = _html_to_rgb_color(color)
        self.set_color(self._user_color)

        # Receive notifications when our buddies send us new sketches
        self._net_controller.connect('new-path', self._new_buddy_path)

        self.connect('new-user-sketch', self._new_local_sketch_cb)

    def _new_buddy_path(self, net_controller, buddy, path):
        """ Called whenever a buddy on the mesh sends us a new sketch path """
        str_color = buddy.get_color()
        if not str_color:
            str_color = "#348798"  # FIXME
        color = XoColor(str_color)
        stroke_color = _html_to_rgb_color(color.get_stroke_color())
        sketch = Sketch.Sketch(stroke_color)
        for item in path:
            sketch.add_point(item[0], item[1])
        self.add_sketch(sketch)

    def _new_local_sketch_cb(self, widget, sketch):
        """ Send the sketch the user just made to the network """
        self._net_controller.new_local_sketch(sketch.get_points())


class SketchActivity(Activity):
    __gsignals__ = {
        'buddy-joined':(gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'buddy-left':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        Activity.__init__(self)
        self.connect('destroy', self._cleanup_cb)
    
        self.set_title("Sketch")

        self._ps = PresenceService.get_instance()
        self._ps_activity = None
        self._owner = self._ps.get_owner()
        
        self._net_controller = NetworkController(self, self._owner)
        self._sketchpad = SharedSketchPad(self._net_controller,
                                profile.get_color().get_stroke_color())
        self.add(self._sketchpad)
        self.show_all()

    def get_ps(self):
        return self._ps

    def _cleanup_cb(self):
        del self._net_controller

    def share(self):
        Activity.share(self)
        self._net_controller.init_stream(self._service)
        self._ps.connect('activity-appeared', self._activity_appeared_cb)

    def join(self, activity_ps):
        Activity.join(self, activity_ps)
        self._net_controller.init_stream(self._service)
        self._ps.connect('activity-appeared', self._activity_appeared_cb)
        self._activity_appeared_cb(self._ps, activity_ps)

    def _activity_appeared_cb(self, ps, activity):
        # Only care about our own activity
        if activity.get_id() != self.get_id():
            return

        # If we already have found our shared activity, do nothing
        if self._ps_activity:
            return

        self._ps_activity = activity

        # Connect signals to the shared activity so we are notified when
        # buddies join and leave
        self._ps_activity.connect('buddy-joined', self._add_buddy)
        self._ps_activity.connect('buddy-left', self._remove_buddy)

        # Get the list of buddies already in this shared activity so we can
        # connect to them
        buddies = self._ps_activity.get_joined_buddies()
        for buddy in buddies:
            self._add_buddy(self._ps_activity, buddy)

    def _add_buddy(self, ps_activity, buddy):
        service_type = self._ps_activity
        self.emit('buddy-joined', ps_activity, buddy, self.get_default_type())

    def _remove_buddy(self, ps_activity, buddy):
        self.emit('buddy-left', ps_activity, buddy, self.get_default_type())

