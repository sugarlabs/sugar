# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2007, Collabora Ltd.
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

import os
import gobject
import dbus, dbus.service

from sugar import profile
from sugar import env

_BUDDY_PATH = "/org/laptop/Sugar/Presence/Buddies/"
_BUDDY_INTERFACE = "org.laptop.Sugar.Presence.Buddy"
_OWNER_INTERFACE = "org.laptop.Sugar.Presence.Buddy.Owner"

class NotFoundError(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'

class DBusGObjectMetaclass(gobject.GObjectMeta, dbus.service.InterfaceType): pass
class DBusGObject(dbus.service.Object, gobject.GObject): __metaclass__ = DBusGObjectMetaclass


class Buddy(DBusGObject):
    """Represents another person on the network and keeps track of the
    activities and resources they make available for sharing."""

    __gtype_name__ = "Buddy"

    __gsignals__ = {
        'validity-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_BOOLEAN])),
        'property-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_PYOBJECT])),
        'icon-changed':     (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_PYOBJECT]))
    }

    __gproperties__ = {
        'key'              : (str, None, None, None,
                              gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT_ONLY),
        'icon'             : (object, None, None, gobject.PARAM_READWRITE),
        'nick'             : (str, None, None, None, gobject.PARAM_READWRITE),
        'color'            : (str, None, None, None, gobject.PARAM_READWRITE),
        'current-activity' : (str, None, None, None, gobject.PARAM_READWRITE),
        'valid'            : (bool, None, None, False, gobject.PARAM_READABLE),
        'owner'            : (bool, None, None, False, gobject.PARAM_READABLE)
    }

    def __init__(self, bus_name, object_id, **kwargs):
        if not bus_name:
            raise ValueError("DBus bus name must be valid")
        if not object_id or not isinstance(object_id, int):
            raise ValueError("object id must be a valid number")

        self._bus_name = bus_name
        self._object_id = object_id
        self._object_path = _BUDDY_PATH + str(self._object_id)
        dbus.service.Object.__init__(self, self._bus_name, self._object_path)

        self._activities = {}   # Activity ID -> Activity
        self.handles = {} # tp client -> handle

        self._valid = False
        self._owner = False
        self._key = None
        self._icon = ''
        self._current_activity = None
        self._nick = None
        self._color = None

        if not kwargs.get("key"):
            raise ValueError("key required")

        gobject.GObject.__init__(self, **kwargs)

    def do_get_property(self, pspec):
        if pspec.name == "key":
            return self._key
        elif pspec.name == "icon":
            return self._icon
        elif pspec.name == "nick":
            return self._nick
        elif pspec.name == "color":
            return self._color
        elif pspec.name == "current-activity":
            if not self._current_activity:
                return None
            if not self._activities.has_key(self._current_activity):
                return None
            return self._current_activity
        elif pspec.name == "valid":
            return self._valid
        elif pspec.name == "owner":
            return self._owner

    def do_set_property(self, pspec, value):
        if pspec.name == "icon":
            if str(value) != self._icon:
                self._icon = str(value)
                self.IconChanged(self._icon)
                self.emit('icon-changed', self._icon)
        elif pspec.name == "nick":
            self._nick = value
        elif pspec.name == "color":
            self._color = value
        elif pspec.name == "current-activity":
            self._current_activity = value
        elif pspec.name == "key":
            self._key = value

        self._update_validity()

    # dbus signals
    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="ay")
    def IconChanged(self, icon_data):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="o")
    def JoinedActivity(self, activity_path):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="o")
    def LeftActivity(self, activity_path):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="a{sv}")
    def PropertyChanged(self, updated):
        pass

    # dbus methods
    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="ay")
    def GetIcon(self):
        if not self.props.icon:
            return ""
        return dbus.ByteArray(self.props.icon)

    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="ao")
    def GetJoinedActivities(self):
        acts = []
        for act in self.get_joined_activities():
            acts.append(act.object_path())
        return acts

    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="a{sv}")
    def GetProperties(self):
        props = {}
        props['nick'] = self.props.nick
        props['owner'] = self.props.owner
        props['key'] = self.props.key
        props['color'] = self.props.color
        props['current-activity'] = self.props.current_activity
        return props

    # methods
    def object_path(self):
        return dbus.ObjectPath(self._object_path)

    def add_activity(self, activity):
        actid = activity.props.id
        if self._activities.has_key(actid):
            return
        self._activities[actid] = activity
        if activity.props.valid:
            self.JoinedActivity(activity.object_path())

    def remove_activity(self, activity):
        actid = activity.props.id
        if not self._activities.has_key(actid):
            return
        del self._activities[actid]
        if activity.props.valid:
            self.LeftActivity(activity.object_path())

    def get_joined_activities(self):
        acts = []
        for act in self._activities.values():
            if act.props.valid:
                acts.append(act)
        return acts

    def set_properties(self, properties):
        changed = False
        if "nick" in properties.keys():
            nick = properties["nick"]
            if nick != self._nick:
                self._nick = nick
                changed = True
        if "color" in properties.keys():
            color = properties["color"]
            if color != self._color:
                self._color = color
                changed = True
        if "current-activity" in properties.keys():
            curact = properties["current-activity"]
            if curact != self._current_activity:
                self._current_activity = curact
                changed = True

        if not changed:
            return

        # Try emitting PropertyChanged before updating validity
        # to avoid leaking a PropertyChanged signal before the buddy is
        # actually valid the first time after creation
        if self._valid:
            self.PropertyChanged(properties)
            self.emit('property-changed', properties)

        self._update_validity()

    def _update_validity(self):
        try:
            old_valid = self._valid
            if self._color and self._nick and self._key:
                self._valid = True
            else:
                self._valid = False

            if old_valid != self._valid:
                self.emit("validity-changed", self._valid)
        except AttributeError:
            self._valid = False


class Owner(Buddy):
    """Class representing the owner of the machine.  This is the client
    portion of the Owner, paired with the server portion in Owner.py."""

    _SHELL_SERVICE = "org.laptop.Shell"
    _SHELL_OWNER_INTERFACE = "org.laptop.Shell.Owner"
    _SHELL_PATH = "/org/laptop/Shell"

    def __init__(self, bus_name, object_id):
        key = profile.get_pubkey()
        nick = profile.get_nick_name()
        color = profile.get_color().to_string()

        icon_file = os.path.join(env.get_profile_path(), "buddy-icon.jpg")
        f = open(icon_file, "r")
        icon = f.read()
        f.close()

        self._bus = dbus.SessionBus()
        self._bus.add_signal_receiver(self._name_owner_changed_handler,
                                      signal_name="NameOwnerChanged",
                                      dbus_interface="org.freedesktop.DBus")

        # Connect to the shell to get notifications on Owner object
        # property changes
        try:
            self._connect_to_shell()
        except dbus.DBusException:
            pass

        Buddy.__init__(self, bus_name, object_id, key=key, nick=nick, color=color,
                icon=icon)
        self._owner = True

        # enable this to change random buddy properties
        if False:
            gobject.timeout_add(5000, self._update_something)

    def _update_something(self):
        import random
        it = random.randint(0, 3)
        if it == 0:
            data = get_random_image()
            self._icon_changed_cb(data)
        elif it == 1:
            from sugar.graphics import xocolor
            xo = xocolor.XoColor()
            self._color_changed_cb(xo.to_string())
        elif it == 2:
            names = ["Liam", "Noel", "Guigsy", "Whitey", "Bonehead"]
            foo = random.randint(0, len(names) - 1)
            self._nick_changed_cb(names[foo])
        elif it == 3:
            bork = random.randint(25, 65)
            it = ""
            for i in range(0, bork):
                it += chr(random.randint(40, 127))
            from sugar import util
            self._cur_activity_changed_cb(util.unique_id(it))
        return True

    def _name_owner_changed_handler(self, name, old, new):
        if name != self._SHELL_SERVICE:
            return
        if (old and len(old)) and (not new and not len(new)):
            # shell went away
            self._shell_owner = None
        elif (not old and not len(old)) and (new and len(new)):
            # shell started
            self._connect_to_shell()

    def _connect_to_shell(self):
        obj = self._bus.get_object(self._SHELL_SERVICE, self._SHELL_PATH)
        self._shell_owner = dbus.Interface(obj, self._SHELL_OWNER_INTERFACE)
        self._shell_owner.connect_to_signal('IconChanged', self._icon_changed_cb)
        self._shell_owner.connect_to_signal('ColorChanged', self._color_changed_cb)
        self._shell_owner.connect_to_signal('NickChanged', self._nick_changed_cb)
        self._shell_owner.connect_to_signal('CurrentActivityChanged',
                self._cur_activity_changed_cb)

    def _icon_changed_cb(self, icon):
        self.props.icon = icon

    def _color_changed_cb(self, color):
        props = {'color': color}
        self.set_properties(props)

    def _nick_changed_cb(self, nick):
        props = {'nick': nick}
        self.set_properties(props)

    def _cur_activity_changed_cb(self, activity_id):
        if not self._activities.has_key(activity_id):
            # This activity is local-only
            activity_id = None
        props = {'current-activity': activity_id}
        self.set_properties(props)



def get_random_image():
    import cairo, math, random, gtk

    def rand():
        return random.random()

    SIZE = 200

    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    cr = cairo.Context(s)

    # background gradient
    cr.save()
    g = cairo.LinearGradient(0, 0, 1, 1)
    g.add_color_stop_rgba(1, rand(), rand(), rand(), rand())
    g.add_color_stop_rgba(0, rand(), rand(), rand(), rand())
    cr.set_source(g)
    cr.rectangle(0, 0, SIZE, SIZE);
    cr.fill()
    cr.restore()

    # random path
    cr.set_line_width(10 * rand() + 5)
    cr.move_to(SIZE * rand(), SIZE * rand())
    cr.line_to(SIZE * rand(), SIZE * rand())
    cr.rel_line_to(SIZE * rand() * -1, 0)
    cr.close_path()
    cr.stroke()

    # a circle
    cr.set_source_rgba(rand(), rand(), rand(), rand())
    cr.arc(SIZE * rand(), SIZE * rand(), 100 * rand() + 30, 0, 2 * math.pi)
    cr.fill()

    # another circle
    cr.set_source_rgba(rand(), rand(), rand(), rand())
    cr.arc(SIZE * rand(), SIZE * rand(), 100 * rand() + 30, 0, 2 * math.pi)
    cr.fill()

    def img_convert_func(buf, data):
        data[0] += buf
        return True

    data = [""]
    pixbuf = gtk.gdk.pixbuf_new_from_data(s.get_data(), gtk.gdk.COLORSPACE_RGB,
            True, 8, s.get_width(), s.get_height(), s.get_stride())
    pixbuf.save_to_callback(img_convert_func, "jpeg", {"quality": "90"}, data)
    del pixbuf

    return str(data[0])

