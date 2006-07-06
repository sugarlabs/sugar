import dbus
import gtk
import gobject

class ActivityHostSignalHelper(gobject.GObject):
	__gsignals__ = {
		'shared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
	}

	def __init__(self, parent):
		gobject.GObject.__init__(self)
		self._parent = parent

	def emit_shared(self):
		self.emit('shared')

class ActivityHost(dbus.service.Object):
	def __init__(self, activity_container, activity_name, default_type, activity_id = None):
		self.peer_service = None

		self.activity_name = activity_name
		self.ellipsize_tab = False
		self._shared = False

		self._signal_helper = ActivityHostSignalHelper(self)

		self.activity_container = activity_container
		
		if activity_id is None:
			self.activity_id = sugar.util.unique_id()
		else:
			self.activity_id = activity_id
		self._default_type = default_type	
	
		self.dbus_object_name = "/com/redhat/Sugar/Shell/Activities/%s" % self.activity_id
		
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

		self._create_chat()
				
		notebook = self.activity_container.notebook
		index = notebook.append_page(self.socket, hbox)
		notebook.set_current_page(index)
		
	def _create_chat(self):
		self._activity_chat = ActivityChat(self)

	def got_focus(self):
		if self.peer_service != None:
			self.peer_service.got_focus()
	
	def lost_focus(self):
		self.peer_service.lost_focus()

	def get_chat(self):
		return self._activity_chat

	def get_default_type(self):
		return self._default_type

	def __close_button_clicked_reply_cb(self):
		pass

	def __close_button_clicked_error_cb(self, error):
		pass
	
	def publish(self):
		self._activity_chat.publish()
		self.peer_service.publish()
	
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

	def connect(self, signal, func):
		self._signal_helper.connect(signal, func)

	def get_shared(self):
		"""Return True if this activity is shared, False if
		it has not been shared yet."""
		return self._shared

	def _shared_signal(self):
		self._shared = True
		self._signal_helper.emit_shared()

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
		self.activity_container.bus.add_signal_receiver(self._shared_signal,
				signal_name="ActivityShared",
				dbus_interface="com.redhat.Sugar.Activity",
				named_service=self.__peer_service_name,
				path=self.__peer_object_name)

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
			 in_signature="b", \
			 out_signature="")
	def set_has_changes(self, has_changes):
		if has_changes:
			attrs = pango.AttrList()
			attrs.insert(pango.AttrForeground(50000, 0, 0, 0, -1))
			attrs.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, -1))
			self.tab_label.set_attributes(attrs)
		else:
			self.tab_label.set_attributes(pango.AttrList())

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
			# Work around for a bug in dbus < 0.61 where integers
			# are not correctly marshalled
			if c < 0:
				c += 256
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
		"""Real function that the shell should use for getting the
		activity's ID."""
		return self.activity_id

	def get_id(self):
		"""Interface-type function to match activity.Activity's
		get_id() function."""
		return self.activity_id

	def default_type(self):
		"""Interface-type function to match activity.Activity's
		default_type() function."""
		return self._default_type

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
