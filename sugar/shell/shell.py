#!/usr/bin/python
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import dbus
import dbus.service
import dbus.glib
import pygtk
pygtk.require('2.0')
import gtk
import pango

activity_counter = 0

class ActivityHost(dbus.service.Object):

	def __init__(self, activity_container, activity_name):
		global activity_counter

		self.activity_name = activity_name
		self.ellipsize_tab = False

		self.activity_container = activity_container
		
		self.activity_id = activity_counter
		activity_counter += 1
		
		self.dbus_object_name = "/com/redhat/Sugar/Shell/Activities/%d" % self.activity_id
		#print "object name = %s"%self.dbus_object_name
		
		dbus.service.Object.__init__(self, activity_container.service, self.dbus_object_name)
		self.socket = gtk.Socket()
		self.socket.set_data("sugar-activity", self)
		self.socket.show()
		
		hbox = gtk.HBox(False, 4);

		self.tab_activity_image = gtk.Image()
		self.tab_activity_image.set_from_stock(gtk.STOCK_CONVERT, gtk.ICON_SIZE_MENU)
		hbox.pack_start(self.tab_activity_image)
		#self.tab_activity_image.show()		
		
		self.label_hbox = gtk.HBox(False, 4);
		self.label_hbox.connect("style-set", self.__tab_label_style_set_cb)
		hbox.pack_start(self.label_hbox)

		self.tab_label = gtk.Label(self.activity_name)
		self.tab_label.set_single_line_mode(True)
		self.tab_label.set_alignment(0.0, 0.5)
		self.tab_label.set_padding(0, 0)
		self.tab_label.show()
		
		close_image = gtk.Image()
		close_image.set_from_stock (gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
		close_image.show()
		
		self.tab_close_button = gtk.Button()
		rcstyle = gtk.RcStyle();
		rcstyle.xthickness = rcstyle.ythickness = 0;
		self.tab_close_button.modify_style (rcstyle);
		self.tab_close_button.add(close_image)
		self.tab_close_button.set_relief(gtk.RELIEF_NONE)
		self.tab_close_button.set_focus_on_click(False)
		self.tab_close_button.connect("clicked", self.tab_close_button_clicked)
		
		self.label_hbox.pack_start(self.tab_label)
		self.label_hbox.pack_start(self.tab_close_button, False, False, 0)
		self.label_hbox.show()
		
		hbox.show()
		
		notebook = self.activity_container.notebook
		index = notebook.append_page(self.socket, hbox)
		notebook.set_current_page(index)

	def __close_button_clicked_reply_cb(self):
		pass

	def __close_button_clicked_error_cb(self, error):
		pass
		
	def tab_close_button_clicked(self, button):
		self.peer_service.close_from_user(reply_handler = self.__close_button_clicked_reply_cb, \
										  error_handler = self.__close_button_clicked_error_cb)

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
							 in_signature="", \
							 out_signature="t")
	def get_host_xembed_id(self):
		window_id = self.socket.get_id()
		#print "window_id = %d"%window_id
		return window_id

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="ss", \
			 out_signature="")
	def set_peer_service_name(self, peer_service_name, peer_object_name):
		#print "peer_service_name = %s, peer_object_name = %s"%(peer_service_name, peer_object_name)
		self.__peer_service_name = peer_service_name
		self.__peer_object_name = peer_object_name
		self.peer_service = dbus.Interface(self.activity_container.bus.get_object( \
				self.__peer_service_name, self.__peer_object_name), \
										   "com.redhat.Sugar.Activity")

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="b", \
			 out_signature="")
	def set_ellipsize_tab(self, ellipsize):
		self.ellipsize_tab = True
		self.update_tab_size()

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="b", \
			 out_signature="")
	def set_can_close(self, can_close):
		if can_close:
			self.tab_close_button.show()
		else:
			self.tab_close_button.hide()

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="b", \
			 out_signature="")
	def set_tab_show_icon(self, show_icon):
		if show_icon:
			self.tab_activity_image.show()
		else:
			self.tab_activity_image.hide()

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="s", \
			 out_signature="")
	def set_tab_text(self, text):
		self.tab_label.set_text(text)

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
			 in_signature="ayibiiii", \
			 out_signature="")
	def set_tab_icon(self, data, colorspace, has_alpha, bits_per_sample, width, height, rowstride):
	    #print "width=%d, height=%d"%(width, height)
		#print "  data = ", data
		pixstr = ""
		for c in data:
			pixstr += chr(c)

		pixbuf = gtk.gdk.pixbuf_new_from_data(pixstr, colorspace, has_alpha, bits_per_sample, width, height, rowstride)
		#print pixbuf
		self.tab_activity_image.set_from_pixbuf(pixbuf)

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost", \
						 in_signature="", \
						 out_signature="")
	def shutdown(self):
		#print "shutdown"
		for owner, activity in self.activity_container.activities[:]:
			if activity == self:
				self.activity_container.activities.remove((owner, activity))
				
		for i in range(self.activity_container.notebook.get_n_pages()):
			child = self.activity_container.notebook.get_nth_page(i)
			if child == self.socket:
				#print "found child"
				self.activity_container.notebook.remove_page(i)
				break

		del self

	def get_host_activity_id(self):
		return self.activity_id

	def get_object_path(self):
		return self.dbus_object_name

	def update_tab_size(self):
		if self.ellipsize_tab:
			self.tab_label.set_ellipsize(pango.ELLIPSIZE_END)

			context = self.label_hbox.get_pango_context()
			font_desc = self.label_hbox.style.font_desc
			metrics = context.get_metrics(font_desc, context.get_language())
			char_width = metrics.get_approximate_digit_width()
			[w, h] = self.__get_close_icon_size()
			tab_width = 15 * pango.PIXELS(char_width) + 2 * w
			self.label_hbox.set_size_request(tab_width, -1);
		else:
			self.tab_label.set_ellipsize(pango.ELLIPSIZE_NONE)
			self.label_hbox.set_size_request(-1, -1)

	def __get_close_icon_size(self):
		settings = self.label_hbox.get_settings()
		return gtk.icon_size_lookup_for_settings(settings, gtk.ICON_SIZE_MENU)

	def __tab_label_style_set_cb(self, widget, previous_style):
		[w, h] = self.__get_close_icon_size()
		self.tab_close_button.set_size_request (w + 5, h + 2)
		self.update_tab_size()

class ActivityContainer(dbus.service.Object):

	def __init__(self, service, bus):

		self.activities = []

		self.bus = bus
		self.service = service

		dbus.service.Object.__init__(self, self.service, "/com/redhat/Sugar/Shell/ActivityContainer")
		bus.add_signal_receiver(self.name_owner_changed, dbus_interface = "org.freedesktop.DBus", signal_name = "NameOwnerChanged")

		self.window = gtk.Window()
		self.window.set_title("OLPC Sugar")
		self.window.resize(640, 480)
		self.window.set_geometry_hints(min_width = 640, max_width = 640, min_height = 480, max_height = 480)
		self.notebook = gtk.Notebook()

		#tab_label = gtk.Label("My Laptop")
		#empty_label = gtk.Label("This activity could launch other activities / be a help page")
		#empty_label.show()
		#self.notebook.append_page(empty_label, tab_label)

		self.notebook.show()
		self.notebook.connect("switch-page", self.notebook_tab_changed)
		self.window.add(self.notebook)
		
		self.window.connect("destroy", lambda w: gtk.main_quit())
		
		self.current_activity = None

	def show(self):
		self.window.show()

	def __focus_reply_cb(self):
		pass

	def __focus_error_cb(self, error):
		pass


	def notebook_tab_changed(self, notebook, page, page_number):
		#print "in notebook_tab_changed"
		#print notebook.get_nth_page(page_number)
		new_activity = notebook.get_nth_page(page_number).get_data("sugar-activity")
		#print " Current activity: ", self.current_activity
		#print " New activity:	 ", new_activity

		if self.current_activity != None:
			if self.has_activity(self.current_activity):
				self.current_activity.peer_service.lost_focus(reply_handler = self.__focus_reply_cb, error_handler = self.__focus_error_cb)
				
				self.current_activity = new_activity

		if self.current_activity != None:
			if self.has_activity(self.current_activity):
				self.current_activity.peer_service.got_focus(reply_handler = self.__focus_reply_cb, error_handler = self.__focus_error_cb)


	def has_activity(self, activity_to_check_for):
		for owner, activity in self.activities[:]:
			if activity_to_check_for == activity:
				return True
		return False
	

	def name_owner_changed(self, service_name, old_service_name, new_service_name):
		#print "in name_owner_changed: svc=%s oldsvc=%s newsvc=%s"%(service_name, old_service_name, new_service_name)
		for owner, activity in self.activities[:]:
			if owner == old_service_name:
				self.activities.remove((owner, activity))
		#self.__print_activities()


	@dbus.service.method("com.redhat.Sugar.Shell.ActivityContainer", \
			 in_signature="s", \
			 out_signature="i", \
			 sender_keyword="sender")
	def add_activity(self, activity_name, sender):
		#print "hello world, activity_name = '%s', sender = '%s'"%(activity_name, sender)
		activity = ActivityHost(self, activity_name)
		self.activities.append((sender, activity))

		#self.__print_activities()
		return activity.get_host_activity_id()

	def __print_activities(self):
		print "__print_activities: %d activities registered" % len(self.activities)
		i = 0
		for owner, activity in self.activities:
			print "  %d: owner=%s activity_object_name=%s" % (i, owner, activity.dbus_object_name)
			i += 1


def main():
	session_bus = dbus.SessionBus()
	service = dbus.service.BusName("com.redhat.Sugar.Shell", bus=session_bus)

	activityContainer = ActivityContainer(service, session_bus)
	activityContainer.show()
