# Copyright (C) 2006-2007, Red Hat, Inc.
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

"""Activity implementation code for Sugar-based activities

Each activity within the OLPC environment must provide two
dbus services.  The first, patterned after the 

    sugar.activity.activityfactory.ActivityFactory

class is responsible for providing a "create" method which 
takes a small dictionary with values corresponding to a 

    sugar.activity.activityhandle.ActivityHandle

describing an individual instance of the activity.

Each activity so registered is described by a

    sugar.activity.bundle.Bundle

instance, which parses a specially formatted activity.info 
file (stored in the activity directory's ./activity 
subdirectory).  The 

    sugar.activity.bundlebuilder

module provides facilities for the standard setup.py module 
which produces and registers bundles from activity source 
directories.

Once instantiated by the ActivityFactory's create method,
each activity must provide an introspection API patterned 
after the

    sugar.activity.activityservice.ActivityService

class.  This class allows for querying the ID of the root 
window, requesting sharing across the network, and basic
"what type of application are you" queries.
"""
from sugar.activity.registry import ActivityRegistry
from sugar.activity.registry import get_registry
from sugar.activity.registry import ActivityInfo
