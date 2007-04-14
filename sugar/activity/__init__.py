"""Activity implementation code for Sugar-based activities

Each activity within the OLPC environment must provide two
dbus services.  The first, patterned after the 

    sugar.activity.activityfactory.ActivityFactory

class is responsible for providing a "create" method which 
takes a small dictionary with values corresponding to a 

    sugar.activity.activityhandle.ActivityHandle

describing an individual instance of the activity.  The 
ActivityFactory service is registered with dbus using the 
global

    sugar.activity.bundleregistry.BundleRegistry 

service, which creates dbus .service files in a well known
directory.  Those files tell dbus what executable to run 
in order to load the ActivityFactory which will provide 
the creation service.

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
