import pygtk
pygtk.require('2.0')
import gtk
import gobject

class Toolbox(gtk.VBox):
	__gsignals__ = {
		'tool-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
				         ([gobject.TYPE_STRING]))
	}

	def __init__(self):
		gtk.VBox.__init__(self)
	
		self._tool_hbox = gtk.HBox()
		
		self._add_tool('FreeHand', 'freehand')
		self._add_tool('Text', 'text')
		
		self.pack_start(self._tool_hbox)
		self._tool_hbox.show()
		
		self._color_hbox = gtk.HBox()
		
		self._add_color([0, 0, 0])
		self._add_color([1, 0, 0])
		self._add_color([0, 1, 0])
		self._add_color([0, 0, 1])

		self.pack_start(self._color_hbox)		
		self._color_hbox.show()
				
	def _add_tool(self, label, tool_id):
		tool = gtk.Button(label)
		tool.connect('clicked', self.__tool_clicked_cb, tool_id)
		self._tool_hbox.pack_start(tool, False)
		tool.show()

	def _add_color(self, rgb):
		color = gtk.Button('Color')
		color.connect('clicked', self.__color_clicked_cb, rgb)
		self._color_hbox.pack_start(color, False)
		color.show()

	def __tool_clicked_cb(self, button, tool_id):
		self.emit("tool-selected", tool_id)
	
	def __color_clicked_cb(self, button, rgb):
		pass
