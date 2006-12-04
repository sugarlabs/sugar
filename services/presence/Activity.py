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

import dbus

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"
ACTIVITY_DBUS_OBJECT_PATH = "/org/laptop/Presence/Activities/"
ACTIVITY_DBUS_INTERFACE = "org.laptop.Presence.Activity"


class ActivityDBusHelper(dbus.service.Object):
    def __init__(self, parent, bus_name, object_path):
        self._parent = parent
        self._bus_name = bus_name
        self._object_path = object_path
        dbus.service.Object.__init__(self, bus_name, self._object_path)

    @dbus.service.method(ACTIVITY_DBUS_INTERFACE,
                        in_signature="s", out_signature="ao")
    def getServicesOfType(self, stype):
        ret = []
        for serv in self._parent.get_services_of_type(stype):
            ret.append(serv.object_path())
        return ret

    @dbus.service.method(ACTIVITY_DBUS_INTERFACE,
                        in_signature="", out_signature="ao")
    def getServices(self):
        ret = []
        for serv in self._parent.get_services():
            ret.append(serv.object_path())
        return ret

    @dbus.service.method(ACTIVITY_DBUS_INTERFACE,
                        in_signature="", out_signature="s")
    def getId(self):
        return self._parent.get_id()

    @dbus.service.method(ACTIVITY_DBUS_INTERFACE,
                        in_signature="", out_signature="s")
    def getColor(self):
        return self._parent.get_color()

    @dbus.service.method(ACTIVITY_DBUS_INTERFACE,
                        in_signature="", out_signature="ao")
    def getJoinedBuddies(self):
        ret = []
        for buddy in self._parent.get_joined_buddies():
            ret.append(buddy.object_path())
        return ret
    
    @dbus.service.signal(ACTIVITY_DBUS_INTERFACE,
                        signature="o")
    def ServiceAppeared(self, object_path):
        pass

    @dbus.service.signal(ACTIVITY_DBUS_INTERFACE,
                        signature="o")
    def ServiceDisappeared(self, object_path):
        pass

    @dbus.service.signal(ACTIVITY_DBUS_INTERFACE,
                        signature="o")
    def BuddyJoined(self, object_path):
        pass

    @dbus.service.signal(ACTIVITY_DBUS_INTERFACE,
                        signature="o")
    def BuddyLeft(self, object_path):
        pass


class Activity(object):
    def __init__(self, bus_name, object_id, initial_service):
        if not initial_service.get_activity_id():
            raise ValueError("Service must have a valid Activity ID")
        self._activity_id = initial_service.get_activity_id()

        self._buddies = []
        self._services = {}    # service type -> list of Services
        self._color = None
        self._valid = False

        self._object_id = object_id
        self._object_path = "/org/laptop/Presence/Activities/%d" % self._object_id
        self._dbus_helper = ActivityDBusHelper(self, bus_name, self._object_path)
        
        self.add_service(initial_service)

    def object_path(self):
        return dbus.ObjectPath(self._object_path)

    def is_valid(self):
        """An activity is only valid when it's color is available."""
        return self._valid

    def get_id(self):
        return self._activity_id

    def get_color(self):
        return self._color

    def get_services(self):
        ret = []
        for serv_list in self._services.values():
            for service in serv_list:
                if service not in ret:
                    ret.append(service)
        return ret

    def get_services_of_type(self, stype):
        if self._services.has_key(stype):
            return self._services[stype]
        return []

    def get_joined_buddies(self):
        buddies = []
        for serv_list in self._services.values():
            for serv in serv_list:
                owner = serv.get_owner()
                if owner and not owner in buddies and owner.is_valid():
                    buddies.append(owner)
        return buddies

    def add_service(self, service):
        stype = service.get_type()
        if not self._services.has_key(stype):
            self._services[stype] = []

        if not self._color:
            color = service.get_one_property('color')
            if color:
                self._color = color
                self._valid = True

        # Send out the BuddyJoined signal if this is the first
        # service from the buddy that we've seen
        buddies = self.get_joined_buddies()
        serv_owner = service.get_owner()
        if serv_owner and serv_owner not in buddies and serv_owner.is_valid():
            self._dbus_helper.BuddyJoined(serv_owner.object_path())
            serv_owner.add_activity(self)

        if not service in self._services[stype]:
            self._services[stype].append(service)
            self._dbus_helper.ServiceAppeared(service.object_path())

    def remove_service(self, service):
        stype = service.get_type()
        if not self._services.has_key(stype):
            return
        self._services[stype].remove(service)
        self._dbus_helper.ServiceDisappeared(service.object_path())
        if len(self._services[stype]) == 0:
            del self._services[stype]

        # Send out the BuddyLeft signal if this is the last
        # service from the buddy
        buddies = self.get_joined_buddies()
        serv_owner = service.get_owner()
        if serv_owner and serv_owner not in buddies and serv_owner.is_valid():
            serv_owner.remove_activity(self)
            self._dbus_helper.BuddyLeft(serv_owner.object_path())
