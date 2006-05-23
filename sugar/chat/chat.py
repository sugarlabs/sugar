#!/usr/bin/python -t
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import sys
import base64
import sha

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango

from sugar.shell import activity
from sugar.p2p.Group import Group
from sugar.p2p import Buddy
from sugar.p2p.Group import LocalGroup
from sugar.p2p.Service import Service
from sugar.p2p.Stream import Stream
from sugar.session.LogWriter import LogWriter
from sugar.chat.sketchpad.Toolbox import Toolbox
from sugar.chat.sketchpad.SketchPad import SketchPad
from sugar.chat.Emoticons import Emoticons
import sugar.env

import richtext

PANGO_SCALE=1024 # Where is this defined?

CHAT_SERVICE_TYPE = "_olpc_chat._tcp"
CHAT_SERVICE_PORT = 6100

GROUP_CHAT_SERVICE_TYPE = "_olpc_group_chat._udp"
GROUP_CHAT_SERVICE_ADDRESS = "224.0.0.221"
GROUP_CHAT_SERVICE_PORT = 6200

class Chat(activity.Activity):
	def __init__(self, controller):
		Buddy.recognize_buddy_service_type(CHAT_SERVICE_TYPE)
		self._controller = controller
		activity.Activity.__init__(self)
		self._stream_writer = None
		
		self._emt_popup = None

		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Browser', '/com/redhat/Sugar/Browser')
		self._browser_shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.BrowserShell')

	def activity_on_connected_to_shell(self):
		self.activity_set_tab_text(self._act_name)
		self._plug = self.activity_get_gtk_plug()
		self._ui_setup(self._plug)
		self._plug.show_all()
	
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

	def _ui_setup(self, base):
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

		base.add(vbox)
		vbox.show()

	def __link_clicked_cb(self, view, address):
		self._browser_shell.open_browser(address)

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
		
		links = self._browser_shell.get_links()

		for link in links:
			item = gtk.MenuItem(link['title'], False)
			item.connect("activate", self.__link_activate_cb, link)
			menu.append(item)
			item.show()
		
		button.set_menu(menu)
		
	def activity_on_close_from_user(self):
		print "act %d: in activity_on_close_from_user" % self.activity_get_id()
		self.activity_shutdown()

    def _scroll_chat_view_to_bottom(self):
        # Only scroll to bottom if the view is already close to the bottom
        vadj = self._chat_sw.get_vadjustment()
        if vadj.value + vadj.page_size > vadj.upper * 0.8:
            vadj.value = vadj.upper - vadj.page_size
            self._chat_sw.set_vadjustment(vadj)

	def _message_inserted(self):
        gobject.idle_add(self._scroll_chat_view_to_bottom)
		self.activity_set_has_changes(True)

	def _insert_buddy(self, buf, nick):
		# Stuff in the buddy icon, if we have one for this buddy
		buddy = self._controller.get_group().get_buddy(nick)
		icon = buddy.get_icon_pixbuf()
		if icon:
			rise = int(icon.get_height() / 4) * -1

			chat_service = buddy.get_service(CHAT_SERVICE_TYPE)
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


class BuddyChat(Chat):
	def __init__(self, controller, buddy):
		self._buddy = buddy
		self._act_name = "Chat: %s" % buddy.get_nick_name()
		Chat.__init__(self, controller)

	def activity_on_connected_to_shell(self):
		Chat.activity_on_connected_to_shell(self)
		self.activity_set_can_close(True)
		self.activity_set_tab_icon_name("im")
		self.activity_show_icon(True)
		self._stream_writer = self._controller.new_buddy_writer(self._buddy)

	def recv_message(self, sender, msg):
		Chat.recv_message(self, self._buddy, msg)
		self._controller.notify_new_message(self, self._buddy)

	def activity_on_close_from_user(self):
		Chat.activity_on_close_from_user(self)
		del self._chats[self._buddy]


class BuddyIconRequestHandler(object):
	def __init__(self, group, stream):
		self._group = group
		self._stream = stream
		self._stream.register_handler(self._handle_buddy_icon_request, "get_buddy_icon")

	def _handle_buddy_icon_request(self):
		"""XMLRPC method, return the owner's icon encoded with base64."""
		icon = self._group.get_owner().get_icon()
		if icon:
			return base64.b64encode(icon)
		return ''


class GroupChat(Chat):

	_MODEL_COL_NICK = 0
	_MODEL_COL_ICON = 1
	_MODEL_COL_BUDDY = 2
	
	def __init__(self):
		self._act_name = "Chat"
		self._chats = {}
		
		Chat.__init__(self, self)

	def get_group(self):
		return self._group

	def new_buddy_writer(self, buddy):
		service = buddy.get_service(CHAT_SERVICE_TYPE)
		return self._buddy_stream.new_writer(service)

	def _start(self):
		self._group = LocalGroup()
		self._group.add_presence_listener(self._on_group_presence_event)
		self._group.add_service_listener(self._on_group_service_event)
		self._group.join()

		name = self._group.get_owner().get_nick_name()

		# Group controls the Stream for incoming messages for
		# specific buddy chats
		buddy_service = Service(name, CHAT_SERVICE_TYPE, CHAT_SERVICE_PORT)
		self._buddy_stream = Stream.new_from_service(buddy_service, self._group)
		self._buddy_icon_handler = BuddyIconRequestHandler(self._group, self._buddy_stream)
		self._buddy_stream.set_data_listener(getattr(self, "_buddy_recv_message"))
		buddy_service.register(self._group)

		# Group chat Stream
		group_service = Service(name, GROUP_CHAT_SERVICE_TYPE,
						  GROUP_CHAT_SERVICE_PORT,
						  GROUP_CHAT_SERVICE_ADDRESS)
		self._group.add_service(group_service)

		self._group_stream = Stream.new_from_service(group_service, self._group)
		self._group_stream.set_data_listener(self._group_recv_message)
		self._stream_writer = self._group_stream.new_writer()

	def _create_sidebar(self):
		vbox = gtk.VBox(False, 6)
		
		label = gtk.Label("Who's around:")
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label, False)
		label.show()

		self._buddy_list_model = gtk.ListStore(gobject.TYPE_STRING, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT)

		image_path = sugar.env.get_data_file('bubbleOutline.png')
		self._pixbuf_active_chat = gtk.gdk.pixbuf_new_from_file(image_path)
		
		image_path = sugar.env.get_data_file('bubble.png')
		self._pixbuf_new_message = gtk.gdk.pixbuf_new_from_file(image_path)

		sw = gtk.ScrolledWindow()
		sw.set_shadow_type(gtk.SHADOW_IN)
		sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		self._buddy_list_view = gtk.TreeView(self._buddy_list_model)
		self._buddy_list_view.set_headers_visible(False)
		self._buddy_list_view.connect("cursor-changed", self._on_buddyList_buddy_selected)
		self._buddy_list_view.connect("row-activated", self._on_buddyList_buddy_double_clicked)

		sw.set_size_request(120, -1)
		sw.add(self._buddy_list_view)
		self._buddy_list_view.show()

		renderer = gtk.CellRendererPixbuf()
		column = gtk.TreeViewColumn("", renderer, pixbuf=self._MODEL_COL_ICON)
		column.set_resizable(False)
		column.set_expand(False);
		self._buddy_list_view.append_column(column)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("", renderer, text=self._MODEL_COL_NICK)
		column.set_resizable(True)
		column.set_sizing("GTK_TREE_VIEW_COLUMN_GROW_ONLY");
		column.set_expand(True);
		self._buddy_list_view.append_column(column)

		vbox.pack_start(sw)
		sw.show()

		return vbox

	def _ui_setup(self, base):
		Chat._ui_setup(self, base)

		vbox = gtk.VBox(False, 12)

		sidebar = self._create_sidebar()
		vbox.pack_start(sidebar)
		sidebar.show()
		
		toolbox = self._create_toolbox()
		vbox.pack_start(toolbox, False)
		toolbox.show()
		
		self._hbox.pack_start(vbox, False)
		vbox.show()
		
		self._plug.show_all()

	def activity_on_connected_to_shell(self):
		Chat.activity_on_connected_to_shell(self)
		
		self.activity_set_tab_icon_name("stock_help-chat")
		self.activity_show_icon(True)

		self._start()

	def activity_on_disconnected_from_shell(self):
		Chat.activity_on_disconnected_from_shell(self)
		gtk.main_quit()

	def _on_buddyList_buddy_selected(self, widget, *args):
		(model, aniter) = widget.get_selection().get_selected()
		name = self._buddy_list_model.get(aniter, self._MODEL_COL_NICK)

	def _on_buddyList_buddy_double_clicked(self, widget, *args):
		""" Select the chat for this buddy or group """
		(model, aniter) = widget.get_selection().get_selected()
		chat = None
		buddy = self._buddy_list_model.get_value(aniter, self._MODEL_COL_BUDDY)
		if buddy and not self._chats.has_key(buddy):
			chat = BuddyChat(self, buddy)
			self._chats[buddy] = chat
			chat.activity_connect_to_shell()

	def _request_buddy_icon_cb(self, response, user_data):
		icon = response
		buddy = user_data
		if icon and len(icon):
			icon = base64.b64decode(icon)
			print "Buddy icon for '%s' is size %d" % (buddy.get_nick_name(), len(icon))
			buddy.set_icon(icon)
		else:
			# What the heck, try again!
			gobject.timeout_add(1000, self._request_buddy_icon, buddy)

	def _request_buddy_icon(self, buddy):
		writer = self.new_buddy_writer(buddy)
		icon = writer.custom_request("get_buddy_icon", self._request_buddy_icon_cb, buddy)

	def _on_group_service_event(self, action, service):
		if action == Group.SERVICE_ADDED:
			# Look for the olpc chat service
			if service.get_type() == CHAT_SERVICE_TYPE:
				# Find the buddy this service belongs to
				buddy = self._group.get_buddy(service.get_name())
				if buddy and buddy.get_address() == service.get_address():
					# Try to get the buddy's icon
					if buddy.get_nick_name() != self._group.get_owner().get_nick_name():
						print "Requesting buddy icon from '%s'." % buddy.get_nick_name()
						gobject.idle_add(self._request_buddy_icon, buddy)
		elif action == Group.SERVICE_REMOVED:
			pass
			
	def __buddy_icon_changed_cb(self, buddy):
		it = self._get_iter_for_buddy(buddy)
		self._buddy_list_model.set(it, self._MODEL_COL_ICON, buddy.get_icon_pixbuf())

	def _on_group_presence_event(self, action, buddy):
		if buddy.get_nick_name() == self._group.get_owner().get_nick_name():
			# Do not show ourself in the buddy list
			pass
		elif action == Group.BUDDY_JOIN:
			aniter = self._buddy_list_model.append(None)
			self._buddy_list_model.set(aniter,
									   self._MODEL_COL_NICK, buddy.get_nick_name(),
									   self._MODEL_COL_BUDDY, buddy)
			buddy.connect('icon-changed', self.__buddy_icon_changed_cb)
		elif action == Group.BUDDY_LEAVE:
			aniter = self._get_iter_for_buddy(buddy)
			if aniter:
				self._buddy_list_model.remove(aniter)

	def _get_iter_for_buddy(self, buddy):
		aniter = self._buddy_list_model.get_iter_first()
		while aniter:
			list_buddy = self._buddy_list_model.get_value(aniter, self._MODEL_COL_BUDDY)
			if buddy == list_buddy:
				return aniter
			aniter = self._buddy_list_model.iter_next(aniter)

	def _group_recv_message(self, buddy, msg):
		self.recv_message(buddy, msg)

	def _buddy_recv_message(self, buddy, msg):
		if not self._chats.has_key(buddy):
			chat = BuddyChat(self, buddy)
			self._chats[buddy] = chat
			chat.activity_connect_to_shell()
		else:
			chat = self._chats[buddy]
		chat.recv_message(buddy, msg)

class ChatShell(dbus.service.Object):
	instance = None

	def get_instance():
		if not ChatShell.instance:
			ChatShell.instance = ChatShell()
		return ChatShell.instance
		
	get_instance = staticmethod(get_instance)

	def __init__(self):
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Chat', bus=session_bus)
		object_path = '/com/redhat/Sugar/Chat'

		dbus.service.Object.__init__(self, bus_name, object_path)

	def open_group_chat(self):
		self._group_chat = GroupChat()
		self._group_chat.activity_connect_to_shell()

	@dbus.service.method('com.redhat.Sugar.ChatShell')
	def send_text_message(self, message):
		self._group_chat.send_text_message(message)


def main():
	if len(sys.argv) > 1 and sys.argv[1] == "--console":
		sys.stdout = LogWriter("Chat")
		sys.stderr = LogWriter("Chat")

	ChatShell.get_instance().open_group_chat()
	try:
		gtk.main()
	except KeyboardInterrupt:
		pass

if __name__ == "__main__":
	main()
