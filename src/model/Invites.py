# Copyright (C) 2006-2007 Red Hat, Inc.
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

import gobject
from sugar.presence import presenceservice

class Invite:
    def __init__(self, issuer, bundle_id, activity_id):
        self._issuer = issuer
        self._activity_id = activity_id
        self._bundle_id = bundle_id

    def get_activity_id(self):
        return self._activity_id

    def get_bundle_id(self):
        return self._bundle_id

class Invites(gobject.GObject):
    __gsignals__ = {
        'invite-added':   (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE, ([object])),
        'invite-removed': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE, ([object])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._dict = {}

        ps = presenceservice.get_instance()
        owner = ps.get_owner()
        owner.connect('joined-activity', self._owner_joined_cb)

    def add_invite(self, issuer, bundle_id, activity_id):
        if activity_id in self._dict:
            # there is no point to add more than one time
            # an invite for the same activity
            return

        invite = Invite(issuer, bundle_id, activity_id)
        self._dict[activity_id] = invite
        self.emit('invite-added', invite)

    def remove_invite(self, invite):
        self._dict.pop(invite.get_activity_id())
        self.emit('invite-removed', invite)

    def remove_activity(self, activity_id):
        invite = self._dict.get(activity_id)
        if invite is not None:
            self.remove_invite(invite)

    def _owner_joined_cb(self, owner, activity):
        self.remove_activity(activity.props.id)

    def __iter__(self):
        return self._dict.values().__iter__()
