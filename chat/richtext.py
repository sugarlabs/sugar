#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import pango
import xml.sax

class RichTextBuffer(gtk.TextBuffer):
	def __init__(self):
		gtk.TextBuffer.__init__(self)
		
		self.connect_after("insert-text", self.__insert_text_cb)
		
		self.__create_tags()
		self.active_tags = []
		
	def apply_tag(self, tag_name):
		self.active_tags.append(tag_name)

	def unapply_tag(self, tag_name):
		self.active_tags.remove(tag_name)
	
	def __create_tags(self):
		tag = self.create_tag("bold")
		tag.set_property("weight", pango.WEIGHT_BOLD)
		
		tag = self.create_tag("italic")
		tag.set_property("style", pango.STYLE_ITALIC)
	
	def __insert_text_cb(self, widget, pos, text, length):
		for tag in self.active_tags:
				pos_end = pos.copy()
				pos_end.backward_chars(length)
				self.apply_tag_by_name(tag, pos, pos_end)
		
class RichTextToolbar(gtk.Toolbar):
	def __init__(self, buf):
		gtk.Toolbar.__init__(self)
		
		self.buf = buf
		
		item = gtk.ToggleToolButton(gtk.STOCK_BOLD)
		item.connect("toggled", self.__toggle_style_cb, "bold")
		self.insert(item, -1)
		item.show()

		item = gtk.ToggleToolButton(gtk.STOCK_ITALIC)
		item.connect("toggled", self.__toggle_style_cb, "italic")
		self.insert(item, -1)
		item.show()
	
	def __toggle_style_cb(self, toggle, tag_name):
		if toggle.get_active():
			self.buf.apply_tag(tag_name)
		else:
			self.buf.unapply_tag(tag_name)
 
class RichTextHandler(xml.sax.handler.ContentHandler):
	def __init__(self, buf):
		self.buf = buf
		self.tags = []

	def _deserialize_element(self, el_name):
		if el_name == "bold":
			return "bold"
		elif el_name == "italic":
			return "italic"
		else:
			return None
 
	def startElement(self, name, attributes):
		tag = self._deserialize_element(name)
		if tag:
			self.tags.append(tag)
 
	def characters(self, data):
		start_it = it = self.buf.get_end_iter()
		mark = self.buf.create_mark(None, start_it, True)
		self.buf.insert(it, data)
		start_it = self.buf.get_iter_at_mark(mark)

		for tag in self.tags:
			self.buf.apply_tag_by_name(tag, start_it, it)
 
	def endElement(self, name):
		tag = self._deserialize_element(name)
		if tag:
			self.tags.remove(tag)

class RichTextSerializer:
	def __init__(self):
		self._open_xml_tags = []
	
	def _get_xml_tag(self, tag):
		if tag.get_property("name") == "bold":
			return "bold"
		elif tag.get_property("name") == "italic":
			return "italic"
		else:
			return "unknown_tag"
			
	def serialize(self, buf):
		xml = "<richtext>"

		next_it = buf.get_start_iter()
		while not next_it.is_end():
			it = next_it.copy()
			if not next_it.forward_to_tag_toggle(None):
				next_it = buf.get_end_iter()

			reopen_xml_tags = []
			for tag in it.get_toggled_tags(False):
				xml_tag = self._get_xml_tag(tag)
				while 1:
					open_xml_tag = self._open_xml_tags.pop()
					if open_xml_tag != xml_tag:
						xml += "</" + open_xml_tag + ">"
						reopen_xml_tags.append(open_xml_tag)
					else:
						xml += "</" + xml_tag + ">"
						break
				
			for xml_tag in reopen_xml_tags:
				self._open_xml_tags.append(xml_tag)
				xml += "<" + xml_tag + ">"
			
			for tag in it.get_toggled_tags(True):
				xml_tag = self._get_xml_tag(tag)
				self._open_xml_tags.append(xml_tag)
				xml += "<" + xml_tag + ">"
			
			xml += buf.get_text(it, next_it)

		if next_it.is_end():
			for xml_tag in self._open_xml_tags:
				xml += "</" + xml_tag + ">"
		
		xml += "</richtext>"
		
		return xml

	def deserialize(self, xml_string, buf):
		parser = xml.sax.make_parser()
		handler = RichTextHandler(buf)
		parser.setContentHandler(handler)
		parser.feed(xml_string)
		parser.close()

def test_quit(window, rich_buf):
	print RichTextSerializer().serialize(rich_buf)
	gtk.main_quit()

if __name__ == "__main__":
	window = gtk.Window()
	window.set_default_size(400, 300)
	
	vbox = gtk.VBox()
	
	rich_buf = RichTextBuffer()
	
	xml_string = "<richtext><bold><italic>Hello</italic>World</bold></richtext>"
	RichTextSerializer().deserialize(xml_string, rich_buf)
	
	view = gtk.TextView(rich_buf)
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
