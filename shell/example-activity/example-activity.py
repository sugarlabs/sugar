#!/usr/bin/python

import string

import dbus
import dbus.service
import dbus.glib
import gobject
import pygtk
pygtk.require('2.0')
import gtk,sys

if len(sys.argv) != 2:
    print "usage: example-activity.py <name_of_activity>"
    sys.exit(1)

bus = dbus.SessionBus()
activity_container_object = bus.get_object("com.redhat.Sugar.Shell", \
					   "/com/redhat/Sugar/Shell/ActivityContainer")
activity_container = dbus.Interface(activity_container_object, \
				    "com.redhat.Sugar.Shell.ActivityContainer")

window_id = activity_container.add_activity(sys.argv[1])
print "got XEMBED window_id = %d"%window_id

plug = gtk.Plug(window_id)
entry = gtk.Entry()
entry.set_text(sys.argv[1])
plug.add(entry)
plug.show_all()

gtk.main()


