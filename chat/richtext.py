#!/usr/bin/env python
# -*- tab-width: 4; indent-tabs-mode: t -*- 

import pygtk
pygtk.require('2.0')
import gtk
import pango

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
				
	def to_xml():
		next_iter = buffer.get_start_iter()
		while not next_iter.is_end():
			

		
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

def test_quit(window, rich_buf):
	print rich_buf.to_xml()
	gtk.main_quit()

if __name__ == "__main__":
	window = gtk.Window()
	window.set_default_size(400, 300)
	
	vbox = gtk.VBox()
	
	rich_buf = RichTextBuffer()
	
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
