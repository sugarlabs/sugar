#!/usr/bin/env python

import sha

import dbus
import dbus.service
import dbus.glib

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango

from sugar.chat.Emoticons import Emoticons
from sugar.chat.ChatToolbar import ChatToolbar
from sugar.chat.ChatEditor import ChatEditor
from sugar.presence.PresenceService import PresenceService
import richtext

PANGO_SCALE = 1024 # Where is this defined?

class Chat(gtk.VBox):
	SERVICE_TYPE = "_olpc_chat._tcp"
	SERVICE_PORT = 6100

	TEXT_MODE = 0
	SKETCH_MODE = 1

	def __init__(self):
		gtk.VBox.__init__(self, False, 6)

		self._stream_writer = None
		self.set_border_width(12)

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
		
		self.pack_start(chat_vbox)
		chat_vbox.show()

		self._mode = Chat.TEXT_MODE
		self._editor = ChatEditor(self, ChatEditor.TEXT_MODE)

		toolbar = ChatToolbar(self._editor.get_buffer())
		self.pack_start(toolbar, False)
		toolbar.show()

		self.pack_start(self._editor, False)
		self._editor.show()

	def get_mode(self):
		return self._mode

	def set_mode(self, mode):
		self._mode = mode
		if self._mode == Chat.TEXT_MODE:
			self._editor.set_mode(ChatEditor.TEXT_MODE)
		elif self._mode == Chat.SKETCH_MODE:
			self._editor.set_mode(ChatEditor.SKETCH_MODE)

	def __get_browser_shell(self):
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Browser', '/com/redhat/Sugar/Browser')
		self._browser_shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.BrowserShell')

	def __link_clicked_cb(self, view, address):
		self.__get_browser_shell().open_browser(address)

	def _scroll_chat_view_to_bottom(self):
		# Only scroll to bottom if the view is already close to the bottom
		vadj = self._chat_sw.get_vadjustment()
		if vadj.value + vadj.page_size > vadj.upper * 0.8:
			vadj.value = vadj.upper - vadj.page_size
			self._chat_sw.set_vadjustment(vadj)

	def _message_inserted(self):
		gobject.idle_add(self._scroll_chat_view_to_bottom)

	def _insert_buddy(self, buf, buddy):
		# Stuff in the buddy icon, if we have one for this buddy
		icon = buddy.get_icon_pixbuf()
		if icon:
			rise = int(icon.get_height() / 4) * -1

			hash_string = "%s-%s" % (buddy.get_nick_name(), buddy.get_address())
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
		buf.insert(aniter, " " + buddy.get_nick_name() + ": ")
		enditer = buf.get_iter_at_offset(offset)
		buf.apply_tag_by_name("nickname", aniter, enditer)
		
	def _insert_rich_message(self, buddy, msg):
		msg = Emoticons.get_instance().replace(msg)

		buf = self._chat_view.get_buffer()
		self._insert_buddy(buf, buddy)
		
		serializer = richtext.RichTextSerializer()
		serializer.deserialize(msg, buf)
		aniter = buf.get_end_iter()
		buf.insert(aniter, "\n")
		
		self._message_inserted()

	def _insert_sketch(self, buddy, svgdata):
		"""Insert a sketch object into the chat buffer."""
		pbl = gtk.gdk.PixbufLoader("svg")
		pbl.write(svgdata)
		pbl.close()
		pbuf = pbl.get_pixbuf()
		
		buf = self._chat_view.get_buffer()

		self._insert_buddy(buf, buddy)
		
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

		# FIXME a better way to compare buddies?			
		owner = PresenceService.get_instance().get_owner()
		if buddy.get_nick_name() == owner.get_nick_name():
			return

		chunk = self._get_first_richtext_chunk(msg)
		if chunk:
			self._insert_rich_message(buddy, chunk)
			return

		chunk = self._get_first_sketch_chunk(msg)
		if chunk:
			self._insert_sketch(buddy, chunk)
			return

	def send_sketch(self, svgdata):
		if not svgdata or not len(svgdata):
			return
		self._stream_writer.write(self.serialize_message(svgdata))
		owner = PresenceService.get_instance().get_owner()
		self._insert_sketch(owner, svgdata)

	def send_text_message(self, text):
		"""Send a chat message and insert it into the local buffer."""
		if len(text) <= 0:
			return
		self._stream_writer.write(self.serialize_message(text))
		owner = PresenceService.get_instance().get_owner()
		self._insert_rich_message(owner, text)

	def serialize_message(self, message):
		owner = PresenceService.get_instance().get_owner()
		return owner.get_nick_name() + '||' + message
		
	def deserialize_message(self, message):
		return message.split('||', 1)
