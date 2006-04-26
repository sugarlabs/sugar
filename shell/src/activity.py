# -*- tab-width: 4; indent-tabs-mode: t -*- 

import string

import gc
import dbus
import dbus.service
import dbus.glib
import gobject
import pygtk
pygtk.require('2.0')
import gtk,sys


class Activity(dbus.service.Object):
	""" Base Sugar activity object from which all other Activities should inherit """

	def __init__(self):
		pass

	def name_owner_changed(self, service_name, old_service_name, new_service_name):
		#print "in name_owner_changed: svc=%s oldsvc=%s newsvc=%s"%(service_name, old_service_name, new_service_name)
		if service_name == "com.redhat.Sugar.Shell" and new_service_name == "":
			self.activity_on_disconnected_from_shell()
		#elif service_name == "com.redhat.Sugar.Shell" and old_service_name == "":
		#	self.activity_on_shell_reappeared()

	def activity_connect_to_shell(self):
		self.__bus = dbus.SessionBus()

		self.__bus.add_signal_receiver(self.name_owner_changed, dbus_interface = "org.freedesktop.DBus", signal_name = "NameOwnerChanged")

		self.__activity_container_object = self.__bus.get_object("com.redhat.Sugar.Shell", \
															   "/com/redhat/Sugar/Shell/ActivityContainer")
		self.__activity_container = dbus.Interface(self.__activity_container_object, \
												   "com.redhat.Sugar.Shell.ActivityContainer")

		self.__activity_id = self.__activity_container.add_activity("")
		self.__object_path = "/com/redhat/Sugar/Shell/Activities/%d"%self.__activity_id

		print "object_path = %s"%self.__object_path

		self.__activity_object = dbus.Interface(self.__bus.get_object("com.redhat.Sugar.Shell", self.__object_path), \
											  "com.redhat.Sugar.Shell.ActivityHost")
		self.__window_id = self.__activity_object.get_host_xembed_id()

		print "XEMBED window_id = %d"%self.__window_id

		self.__plug = gtk.Plug(self.__window_id)

		# Now let the Activity register a peer service so the Shell can poke it
		self.__peer_service_name = "com.redhat.Sugar.Activity%d"%self.__activity_id
		self.__peer_object_name = "/com/redhat/Sugar/Activity/%d"%self.__activity_id
		self.__service = dbus.service.BusName(self.__peer_service_name, bus=self.__bus)
		dbus.service.Object.__init__(self, self.__service, self.__peer_object_name)

		self.__activity_object.set_peer_service_name(self.__peer_service_name, self.__peer_object_name)

		self.activity_on_connected_to_shell()

	def activity_get_gtk_plug(self):
		return self.__plug

	def activity_set_ellipsize_tab(self, ellipsize):
		self.__activity_object.set_ellipsize_tab(ellipsize)

	@dbus.service.method("com.redhat.Sugar.Activity", \
						 in_signature="", \
						 out_signature="")

	def activity_set_can_close(self, can_close):
		self.__activity_object.set_can_close(can_close)

	@dbus.service.method("com.redhat.Sugar.Activity", \
						 in_signature="", \
						 out_signature="")

	def activity_show_icon(self, show_icon):
		self.__activity_object.set_tab_show_icon(show_icon)

	@dbus.service.method("com.redhat.Sugar.Activity", \
						 in_signature="", \
						 out_signature="")

	def activity_set_icon(self, pixbuf):
		pixarray = []
		pixstr = pixbuf.get_pixels();
		for c in pixstr:
				pixarray.append(c)
		self.__activity_object.set_tab_icon(pixarray, \
											pixbuf.get_colorspace(), \
											pixbuf.get_has_alpha(),  \
											pixbuf.get_bits_per_sample(), \
											pixbuf.get_width(), \
											pixbuf.get_height(), \
											pixbuf.get_rowstride())

	@dbus.service.method("com.redhat.Sugar.Activity", \
						 in_signature="", \
						 out_signature="")
						 
	def activity_set_tab_text(self, text):
		self.__activity_object.set_tab_text(text)

	@dbus.service.method("com.redhat.Sugar.Activity", \
						 in_signature="", \
						 out_signature="")
	def lost_focus(self):
		self.activity_on_lost_focus()

	@dbus.service.method("com.redhat.Sugar.Activity", \
						 in_signature="", \
						 out_signature="")
	def got_focus(self):
		self.activity_on_got_focus()


	@dbus.service.method("com.redhat.Sugar.Activity", \
						 in_signature="", \
						 out_signature="")
	def close_from_user(self):
		self.activity_on_close_from_user()

	def activity_get_id(self):
		return self.__activity_id


	def __shutdown_reply_cb(self):
		print "in __reply_cb"

		self.__plug.destroy()
		self.__plug = None

		self.__bus = None
		self.__activity_container_object = None
		self.__activity_container = None
		self.__activity_object = None
		self.__service = None

		self.__bus.remove_signal_receiver(self.name_owner_changed, dbus_interface = "org.freedesktop.DBus", signal_name = "NameOwnerChanged")

		self.activity_on_disconnected_from_shell()


		del self



	def __shutdown_error_cb(self, error):
		print "in __error_cb"

	def activity_shutdown(self):
		self.__activity_object.shutdown(reply_handler = self.__shutdown_reply_cb, error_handler = self.__shutdown_error_cb)

	# pure virtual methods

	def activity_on_connected_to_shell(self):
		print "act %d: you need to override activity_on_connected_to_shell"%self.activity_get_id()

	def activity_on_disconnected_from_shell(self):
		print "act %d: you need to override activity_on_disconnected_from_shell"%self.activity_get_id()

	def activity_on_close_from_user(self):
		print "act %d: you need to override activity_on_close_from_user"%self.activity_get_id()

	def activity_on_lost_focus(self):
		print "act %d: you need to override activity_on_lost_focus"%self.activity_get_id()

	def activity_on_got_focus(self):
		print "act %d: you need to override activity_on_got_focus"%self.activity_get_id()
