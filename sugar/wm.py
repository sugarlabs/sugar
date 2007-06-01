# Copyright (C) 2007, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gtk

import _sugarext

def get_activity_id(wnck_window)
    window = gtk.gdk.window_foreign_new(window.get_xid())
    return _sugarext.x11_get_string_property(
                            window, '_SUGAR_ACTIVITY_ID')

def get_bundle_id(wnck_window, prop):
    window = gtk.gdk.window_foreign_new(window.get_xid())
    return _sugarext.x11_get_string_property(
                            window, '_SUGAR_BUNDLE_ID')

def set_activity_id(window, activity_id):
    _sugarext.x11_set_string_property(
            window, '_SUGAR_ACTIVITY_ID', activity_id)

def set_bundle_id(window, bundle_id):
    _sugarext.x11_set_string_property(
            window, '_SUGAR_BUNDLE_ID', activity_id)
