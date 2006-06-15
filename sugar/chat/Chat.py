#!/usr/bin/env python

import sha

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango

from sugar.chat.sketchpad.Toolbox import Toolbox
from sugar.chat.sketchpad.SketchPad import SketchPad
from sugar.chat.Emoticons import Emoticons

import richtext

PANGO_SCALE = 1024 # Where is this defined?

class Chat(gtk.Window):
	SERVICE_TYPE = "_olpc_chat._tcp"
	SERVICE_PORT = 6100

	def __init__(self, controller):
		gtk.Window.__init__(self)
	
		#Buddy.recognize_buddy_service_type(Chat.SERVICE_TYPE)
		self._controller = controller
		self._stream_writer = None		
		self._emt_popup = None

		vbox = gtk.VBox(False, 6)

		self._hbox = gtk.HBox(False, 12)
		self._hbox.set_border_width(12)

		[chat_vbox, buf] = self._create_chat()
		self._hbox.pack_start(chat_vbox)
		chat_vbox.show()
		
		vbox.pack_start(self._hbox)
		self._hbox.show()

		toolbar = self._create_toolbar(buf)
		vbox.pack_start(toolbar, False)
		toolbar.show()

		self.add(vbox)
		vbox.show()

	def _create_toolbox(self):
		vbox = gtk.VBox(False, 12)
		
		toolbox = Toolbox()
		toolbox.connect('tool-selected', self._tool_selected)
		toolbox.connect('color-selected', self._color_selected)
		vbox.pack_start(toolbox, False)
		toolbox.show()
		
		button_box = gtk.HButtonBox()

		send_button = gtk.Button('Send')
		button_box.pack_start(send_button, False)
		send_button.connect('clicked', self.__send_button_clicked_cb)

		vbox.pack_start(button_box, False)
		button_box.show()
	
		return vbox
		
	def __send_button_clicked_cb(self, button):
		self.send_sketch(self._sketchpad.to_svg())
		self._sketchpad.clear()

	def _color_selected(self, toolbox, color):
		self._sketchpad.set_color(color)
	
	def _tool_selected(self, toolbox, tool_id):
		if tool_id == 'text':
			self._editor_nb.set_current_page(0)
		else:
			self._editor_nb.set_current_page(1)
	
	def _create_chat_editor(self):
		nb = gtk.Notebook()
		nb.set_show_tabs(False)
		nb.set_show_border(False)
		nb.set_size_request(-1, 70)
	
		chat_view_sw = gtk.ScrolledWindow()
		chat_view_sw.set_shadow_type(gtk.SHADOW_IN)
		chat_view_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self._editor = richtext.RichTextView()
		self._editor.connect("key-press-event", self.__key_press_event_cb)
		chat_view_sw.add(self._editor)
		self._editor.show()
		
		nb.append_page(chat_view_sw)
		chat_view_sw.show()
		
		self._sketchpad = SketchPad()
		nb.append_page(self._sketchpad)
		self._sketchpad.show()
		
		nb.set_current_page(0)
		
		return nb
	
	def _create_chat(self):
		chat_vbox = gtk.VBox()
		chat_vbox.set_spacing(6)

		self._chat_sw = gtk.ScrolledWindow()
		self._chat_sw.set_shadow_type(gtk.SHADOW_IN)
		self._chat_sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
		self._chat_view = richtext.RichTextView()
		self._chat_view.connect("link-clicked", self.__link_clicked_cb)
		self._chat_view.set_editable(False)
		self._chat_view.set_cursor_visible(False)
		self._chat_view.set_pixels_above_lines(7)
		self._chat_view.set_left_margin(5)
		self._chat_sw.add(self._chat_view)
		self._chat_view.show()
		chat_vbox.pack_start(self._chat_sw)
		self._chat_sw.show()

		self._editor_nb = self._create_chat_editor()
		chat_vbox.pack_start(self._editor_nb, False)
		self._editor_nb.show()
		
		return chat_vbox, self._editor.get_buffer()

	def __get_browser_shell(self):
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Browser', '/com/redhat/Sugar/Browser')
		self._browser_shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.BrowserShell')

	def __link_clicked_cb(self, view, address):
		self.__get_browser_shell().open_browser(address)

	def __key_press_event_cb(self, text_view, event):
		if event.keyval == gtk.keysyms.Return:
			buf = text_view.get_buffer()
			text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
			if len(text.strip()) > 0:
				serializer = richtext.RichTextSerializer()
				text = serializer.serialize(buf)
				self.send_text_message(text)

			buf.set_text("")
			buf.place_cursor(buf.get_start_iter())

			return True

	def _create_emoticons_popup(self):
		model = gtk.ListStore(gtk.gdk.Pixbuf, str)
		
		for name in Emoticons.get_instance().get_all():
			icon_theme = gtk.icon_theme_get_default()
			pixbuf = icon_theme.load_icon(name, 16, 0)
			model.append([pixbuf, name])
		
		icon_view = gtk.IconView(model)
		icon_view.connect('selection-changed', self.__emoticon_selection_changed_cb)
		icon_view.set_pixbuf_column(0)
		icon_view.set_selection_mode(gtk.SELECTION_SINGLE)
		
		frame = gtk.Frame()
		frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		frame.add(icon_view)
		icon_view.show()		
		
		window = gtk.Window(gtk.WINDOW_POPUP)
		window.add(frame)
		frame.show()
		
		return window
		
	def __emoticon_selection_changed_cb(self, icon_view):
		items = icon_view.get_selected_items()
		if items:
			model = icon_view.get_model()
			icon_name = model[items[0]][1]
			self._editor.get_buffer().append_icon(icon_name)
		self._emt_popup.hide()

	def _create_toolbar(self, rich_buf):
		toolbar = richtext.RichTextToolbar(rich_buf)

		item = gtk.ToolButton()

		hbox = gtk.HBox(False, 6)

		e_image = gtk.Image()
		e_image.set_from_icon_name('stock_smiley-1', gtk.ICON_SIZE_SMALL_TOOLBAR)
		hbox.pack_start(e_image)
		e_image.show()
		
		arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE)
		hbox.pack_start(arrow)
		arrow.show()

		item.set_icon_widget(hbox)
		item.set_homogeneous(False)
		item.connect("clicked", self.__emoticons_button_clicked_cb)
		toolbar.insert(item, -1)
		item.show()
		
		separator = gtk.SeparatorToolItem()
		toolbar.insert(separator, -1)
		separator.show()

		item = gtk.MenuToolButton(None, "Links")
		item.set_menu(gtk.Menu())
		item.connect("show-menu", self.__show_link_menu_cb)
		toolbar.insert(item, -1)
		item.show()
		
		return toolbar
		
	def __emoticons_button_clicked_cb(self, button):
		# FIXME grabs...
		if not self._emt_popup:
			self._emt_popup = self._create_emoticons_popup()

		if self._emt_popup.get_property('visible'):
			self._emt_popup.hide()
		else:
			width = 180
			height = 130
		
			self._emt_popup.set_default_size(width, height)
		
			[x, y] = button.window.get_origin()
			x += button.allocation.x
			y += button.allocation.y - height
			self._emt_popup.move(x, y)
		
			self._emt_popup.show()

	def __link_activate_cb(self, item, link):
		buf = self._editor.get_buffer()
		buf.append_link(link['title'], link['address'])

	def __show_link_menu_cb(self, button):
		menu = gtk.Menu()
		
		links = self.__get_browser_shell().get_links()

		for link in links:
			item = gtk.MenuItem(link['title'], False)
			item.connect("activate", self.__link_activate_cb, link)
			menu.append(item)
			item.show()
		
		button.set_menu(menu)
		
	def _scroll_chat_view_to_bottom(self):
		# Only scroll to bottom if the view is already close to the bottom
		vadj = self._chat_sw.get_vadjustment()
		if vadj.value + vadj.page_size > vadj.upper * 0.8:
			vadj.value = vadj.upper - vadj.page_size
			self._chat_sw.set_vadjustment(vadj)

	def _message_inserted(self):
		gobject.idle_add(self._scroll_chat_view_to_bottom)
		self.set_has_changes(True)

	def _insert_buddy(self, buf, nick):
		# Stuff in the buddy icon, if we have one for this buddy
		buddy = self._controller.get_group().get_buddy(nick)
		icon = buddy.get_icon_pixbuf()
		if icon:
			rise = int(icon.get_height() / 4) * -1

			chat_service = buddy.get_service(Chat.SERVICE_TYPE)
			hash_string = "%s-%s" % (nick, chat_service.get_address())
			sha_hash = sha.new()
			sha_hash.update(hash_string)
			tagname = "buddyicon-%s" % sha_hash.hexdigest()

			if not buf.get_tag_table().lookup(tagname):
				buf.create_tag(tagname, rise=(rise * PANGO_SCALE))

			aniter = buf.get_end_iter()
			buf.insert_pixbuf(aniter, icon)
			aniter.backward_char()
			enditer = buf.get_end_iter()
			buf.apply_tag_by_name(tagname, aniter, enditer)

		# Stick in the buddy's nickname
		if not buf.get_tag_table().lookup("nickname"):
			buf.create_tag("nickname", weight=pango.WEIGHT_BOLD)
		aniter = buf.get_end_iter()
		offset = aniter.get_offset()
		buf.insert(aniter, " " + nick + ": ")
		enditer = buf.get_iter_at_offset(offset)
		buf.apply_tag_by_name("nickname", aniter, enditer)
		
	def _insert_rich_message(self, nick, msg):
		msg = Emoticons.get_instance().replace(msg)

		buf = self._chat_view.get_buffer()
		self._insert_buddy(buf, nick)
		
		serializer = richtext.RichTextSerializer()
		serializer.deserialize(msg, buf)
		aniter = buf.get_end_iter()
		buf.insert(aniter, "\n")
		
		self._message_inserted()

	def _insert_sketch(self, nick, svgdata):
		"""Insert a sketch object into the chat buffer."""
		pbl = gtk.gdk.PixbufLoader("svg")
		pbl.write(svgdata)
		pbl.close()
		pbuf = pbl.get_pixbuf()
		
		buf = self._chat_view.get_buffer()

		self._insert_buddy(buf, nick)
		
		rise = int(pbuf.get_height() / 3) * -1
		sha_hash = sha.new()
		sha_hash.update(svgdata)
		tagname = "sketch-%s" % sha_hash.hexdigest()
		if not buf.get_tag_table().lookup(tagname):
			buf.create_tag(tagname, rise=(rise * PANGO_SCALE))

		aniter = buf.get_end_iter()
		buf.insert_pixbuf(aniter, pbuf)
		aniter.backward_char()
		enditer = buf.get_end_iter()
		buf.apply_tag_by_name(tagname, aniter, enditer)
		aniter = buf.get_end_iter()
		buf.insert(aniter, "\n")

		self._message_inserted()

	def _get_first_richtext_chunk(self, msg):
		"""Scan the message for the first richtext-tagged chunk and return it."""
		rt_last = -1
		tag_rt_start = "<richtext>"
		tag_rt_end = "</richtext>"
		rt_first = msg.find(tag_rt_start)
		length = -1
		if rt_first >= 0:
			length = len(msg)
			rt_last = msg.find(tag_rt_end, rt_first)
		if rt_first >= 0 and rt_last >= (rt_first + len(tag_rt_start)) and length > 0:
			return msg[rt_first:rt_last + len(tag_rt_end)]
		return None

	def _get_first_sketch_chunk(self, msg):
		"""Scan the message for the first SVG-tagged chunk and return it."""
		svg_last = -1
		tag_svg_start = "<svg"
		tag_svg_end = "</svg>"
		desc_start = msg.find("<?xml version='1.0' encoding='UTF-8'?>")
		if desc_start < 0:
			return None
		ignore = msg.find("<!DOCTYPE svg")
		if ignore < 0:
			return None
		svg_first = msg.find(tag_svg_start)
		length = -1
		if svg_first >= 0:
			length = len(msg)
			svg_last = msg.find(tag_svg_end, svg_first)
		if svg_first >= 0 and svg_last >= (svg_first + len(tag_svg_start)) and length > 0:
			return msg[desc_start:svg_last + len(tag_svg_end)]
		return None

	def recv_message(self, buddy, msg):
		"""Insert a remote chat message into the chat buffer."""
		if not buddy:
			return

		chunk = self._get_first_richtext_chunk(msg)
		if chunk:
			self._insert_rich_message(buddy.get_nick_name(), chunk)
			return

		chunk = self._get_first_sketch_chunk(msg)
		if chunk:
			self._insert_sketch(buddy.get_nick_name(), chunk)
			return

	def send_sketch(self, svgdata):
		if not svgdata or not len(svgdata):
			return
		self._stream_writer.write(svgdata)
		owner = self._controller.get_group().get_owner()
		self._insert_sketch(owner.get_nick_name(), svgdata)

	def send_text_message(self, text):
		"""Send a chat message and insert it into the local buffer."""
		if len(text) <= 0:
			return
		self._stream_writer.write(text)
		owner = self._controller.get_group().get_owner()
		self._insert_rich_message(owner.get_nick_name(), text)
