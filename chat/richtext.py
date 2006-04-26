#!/usr/bin/env python

import pygtk
import gobject
pygtk.require('2.0')
import gtk
import pango
import xml.sax

class RichTextView(gtk.TextView):
	
	__gsignals__ = {
		'link-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
					    ([gobject.TYPE_STRING]))
	}

	def __init__(self, rich_buf = None):
		gtk.TextView.__init__(self, rich_buf)
		self.connect("motion-notify-event", self.__motion_notify_cb)
		self.connect("button-press-event", self.__button_press_cb)
		self.__hover_link = False

	def _set_hover_link(self, hover_link):
		if hover_link != self.__hover_link:
			self.__hover_link = hover_link
			display = self.get_toplevel().get_display()
			child_window = self.get_window(gtk.TEXT_WINDOW_TEXT)
			
			if hover_link:
				cursor = gtk.gdk.Cursor(display, gtk.gdk.HAND2)
			else:
				cursor = gtk.gdk.Cursor(display, gtk.gdk.XTERM)
				
			child_window.set_cursor(cursor)
			gtk.gdk.flush()
	
	def __iter_is_link(self, it):
		return it.has_tag(self.get_buffer().get_tag_table().lookup("link"))
	
	def __get_event_iter(self, event):
		return self.get_iter_at_location(int(event.x), int(event.y))

	def __motion_notify_cb(self, widget, event):
		if event.is_hint:
			[x, y, state] = event.window.get_pointer();
		
		it = self.__get_event_iter(event)
		if it:
			hover_link = self.__iter_is_link(it)
		else:
			hover_link = False

		self._set_hover_link(hover_link)
		
	def __button_press_cb(self, widget, event):
		it = self.__get_event_iter(event)
		if it and self.__iter_is_link(it):
			address_tag = buf.get_tag_table().lookup("link-address")

			address_end = it.copy()
			address_end.backward_to_tag_toggle(address_tag)
			
			address_start = address_end.copy()
			address_start.backward_to_tag_toggle(address_tag)
			
			address = self.get_buffer().get_text(address_start, address_end)
			self.emit("link-clicked", address)

class RichTextBuffer(gtk.TextBuffer):
	def __init__(self):
		gtk.TextBuffer.__init__(self)

		self.connect_after("insert-text", self.__insert_text_cb)
		
		self.__create_tags()
		self.active_tags = []

	def append_link(self, title, address):
		it = self.get_iter_at_mark(self.get_insert())
		self.insert_with_tags_by_name(it, address, "link", "link-address")
		self.insert_with_tags_by_name(it, title, "link")
		
	def apply_tag(self, tag_name):
		self.active_tags.append(tag_name)
		
		bounds = self.get_selection_bounds()
		if bounds:
			[start, end] = bounds
			self.apply_tag_by_name(tag_name, start, end)

	def unapply_tag(self, tag_name):
		self.active_tags.remove(tag_name)

		bounds = self.get_selection_bounds()
		if bounds:
			[start, end] = bounds
			self.remove_tag_by_name(tag_name, start, end)
	
	def __create_tags(self):
		tag = self.create_tag("link")
		tag.set_property("underline", pango.UNDERLINE_SINGLE)
		tag.set_property("foreground", "#0000FF")

		tag = self.create_tag("link-address")
		tag.set_property("invisible", True)

		tag = self.create_tag("bold")
		tag.set_property("weight", pango.WEIGHT_BOLD)
		
		tag = self.create_tag("italic")
		tag.set_property("style", pango.STYLE_ITALIC)

		tag = self.create_tag("font-size-xx-small")
		tag.set_property("scale", pango.SCALE_XX_SMALL)

		tag = self.create_tag("font-size-x-small")
		tag.set_property("scale", pango.SCALE_X_SMALL)

		tag = self.create_tag("font-size-small")
		tag.set_property("scale", pango.SCALE_SMALL)

		tag = self.create_tag("font-size-large")
		tag.set_property("scale", pango.SCALE_LARGE)

		tag = self.create_tag("font-size-x-large")
		tag.set_property("scale", pango.SCALE_X_LARGE)

		tag = self.create_tag("font-size-xx-large")
		tag.set_property("scale", pango.SCALE_XX_LARGE)
	
	def __insert_text_cb(self, widget, pos, text, length):
		for tag in self.active_tags:
				pos_end = pos.copy()
				pos_end.backward_chars(length)
				self.apply_tag_by_name(tag, pos, pos_end)
		
class RichTextToolbar(gtk.Toolbar):
	def __init__(self, buf):
		gtk.Toolbar.__init__(self)
		
		self.buf = buf
		
		self.set_style(gtk.TOOLBAR_ICONS)
		
		self._font_size = "normal"
		self._font_scales = [ "xx-small", "x-small", "small",	\
							  "normal",							\
							  "large", "x-large", "xx-large" ]
		
		item = gtk.ToggleToolButton(gtk.STOCK_BOLD)
		item.connect("toggled", self.__toggle_style_cb, "bold")
		self.insert(item, -1)
		item.show()

		item = gtk.ToggleToolButton(gtk.STOCK_ITALIC)
		item.connect("toggled", self.__toggle_style_cb, "italic")
		self.insert(item, -1)
		item.show()

		self._font_size_up = gtk.ToolButton(gtk.STOCK_GO_UP)
		self._font_size_up.connect("clicked", self.__font_size_up_cb)
		self.insert(self._font_size_up, -1)
		self._font_size_up.show()

		self._font_size_down = gtk.ToolButton(gtk.STOCK_GO_DOWN)
		self._font_size_down.connect("clicked", self.__font_size_down_cb)
		self.insert(self._font_size_down, -1)
		self._font_size_down.show()
	
	def _get_font_size_index(self):
		return self._font_scales.index(self._font_size);
	
	def __toggle_style_cb(self, toggle, tag_name):
		if toggle.get_active():
			self.buf.apply_tag(tag_name)
		else:
			self.buf.unapply_tag(tag_name)

	def _set_font_size(self, font_size):
		if self._font_size != "normal":
			self.buf.unapply_tag("font-size-" + self._font_size)
		if font_size != "normal":
			self.buf.apply_tag("font-size-" + font_size)
			
		self._font_size = font_size
		
		can_up = self._get_font_size_index() < len(self._font_scales) - 1
		can_down = self._get_font_size_index() > 0
		self._font_size_up.set_sensitive(can_up)
		self._font_size_down.set_sensitive(can_down)

	def __font_size_up_cb(self, button): 
		index = self._get_font_size_index()
		if index + 1 < len(self._font_scales):
			self._set_font_size(self._font_scales[index + 1])

	def __font_size_down_cb(self, button):
		index = self._get_font_size_index()
		if index > 0:
			self._set_font_size(self._font_scales[index - 1])
			
class RichTextHandler(xml.sax.handler.ContentHandler):
	def __init__(self, serializer, buf):
		self.buf = buf
		self.serializer = serializer
		self.tags = []

	def startElement(self, name, attrs):
		if name != "richtext":
			tag = self.serializer.deserialize_element(name, attrs)
			self.tags.append(tag)
		if name == "link":
			self.href = attrs['href']
 
	def characters(self, data):
		start_it = it = self.buf.get_end_iter()
		mark = self.buf.create_mark(None, start_it, True)
		self.buf.insert(it, data)
		start_it = self.buf.get_iter_at_mark(mark)

		for tag in self.tags:
			self.buf.apply_tag_by_name(tag, start_it, it)
			if tag == "link":
				self.buf.insert_with_tags_by_name(start_it, self.href,
											      "link", "link-address")
 
	def endElement(self, name):
		if name != "richtext":
			self.tags.pop()

class RichTextSerializer:
	def __init__(self):
		self._open_tags = []

	def deserialize_element(self, el_name, attributes):
		if el_name == "bold":
			return "bold"
		elif el_name == "italic":
			return "italic"
		elif el_name == "font":
			return "font-size-" + attributes["size"]
		elif el_name == "link":
			return "link"
		else:
			return None

	def serialize_tag_start(self, tag, it):
		name = tag.get_property("name")
		if name == "bold":
			return "<bold>"
		elif name == "italic":
			return "<italic>"
		elif name == "link":
			address_tag = self.buf.get_tag_table().lookup("link-address")
			end = it.copy()
			end.forward_to_tag_toggle(address_tag)
			address = self.buf.get_text(it, end)
			return "<link " + "href=\"" + address + "\">"
		elif name == "link-address":
			return ""
		elif name.startswith("font-size-"):
			tag_name = name.replace("font-size-", "", 1)
			return "<font size=\"" + tag_name + "\">"
		else:
			return "<unknown>"

	def serialize_tag_end(self, tag):
		name = tag.get_property("name")
		if name == "bold":
			return "</bold>"
		elif name == "italic":
			return "</italic>"
		elif name == "link":
			return "</link>"
		elif name == "link-address":
			return ""
		elif name.startswith("font-size-"):
			return "</font>"
		else:
			return "</unknown>"
	
	def serialize(self, buf):
		self.buf = buf
		
		xml = "<richtext>"

		next_it = buf.get_start_iter()
		while not next_it.is_end():
			it = next_it.copy()
			if not next_it.forward_to_tag_toggle(None):
				next_it = buf.get_end_iter()

			tags_to_reopen = []

			for tag in it.get_toggled_tags(False):
				while 1:
					open_tag = self._open_tags.pop()
					xml += self.serialize_tag_end(tag)
					if open_tag == tag:
						break						
					tags_to_reopen.append(open_tag)
					
			for tag in tags_to_reopen:
				self._open_tags.append(tag)
				xml += self.serialize_tag_start(tag, it)
			
			for tag in it.get_toggled_tags(True):
				self._open_tags.append(tag)
				xml += self.serialize_tag_start(tag, it)
			
			xml += buf.get_text(it, next_it, False)

		if next_it.is_end():
			self._open_tags.reverse()
			for tag in self._open_tags:
				xml += self.serialize_tag_end(tag)
		
		xml += "</richtext>"
		
		return xml

	def deserialize(self, xml_string, buf):
		parser = xml.sax.make_parser()
		handler = RichTextHandler(self, buf)
		parser.setContentHandler(handler)
		parser.feed(xml_string)
		parser.close()

def test_quit(window, rich_buf):
	print RichTextSerializer().serialize(rich_buf)
	gtk.main_quit()
	
def link_clicked(view, address):
	print "Link clicked " + address

if __name__ == "__main__":
	window = gtk.Window()
	window.set_default_size(400, 300)
	
	vbox = gtk.VBox()
	
	rich_buf = RichTextBuffer()

	xml_string = "<richtext>"	

	xml_string += "<bold><italic>Test</italic>one</bold>\n"
	xml_string += "<bold><italic>Test two</italic></bold>"
	xml_string += "<font size=\"xx-small\">Test three</font>"
	xml_string += "<link href=\"http://www.gnome.org\">Test link</link>"
	xml_string += "</richtext>"

	RichTextSerializer().deserialize(xml_string, rich_buf)
	
	view = RichTextView(rich_buf)
	view.connect("link-clicked", link_clicked)
	vbox.pack_start(view)
	view.show()
	
	toolbar = RichTextToolbar(rich_buf)
	vbox.pack_start(toolbar, False)
	toolbar.show()
	
	window.add(vbox)
	vbox.show()
	
	window.show()
	
	window.connect("destroy", test_quit, rich_buf)

	gtk.main()
