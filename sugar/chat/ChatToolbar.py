import gtk, gobject

from sugar.chat.Emoticons import Emoticons
from sugar.chat.sketchpad.Toolbox import Toolbox
import richtext

class ChatToolbar(gtk.HBox):
	def __init__(self, editor):
		gtk.HBox.__init__(self, False, 24)
		
		self._editor = editor
		self._emt_popup = None

		spring = gtk.Label('')
		self.pack_start(spring, True)
		spring.show()

		toolbox = richtext.RichTextToolbox(editor.get_buffer())
		self.pack_start(toolbox, False)
		toolbox.show()
		
		item = gtk.Button()
		item.unset_flags(gtk.CAN_FOCUS)

		e_hbox = gtk.HBox(False, 6)
		
		e_image = gtk.Image()
		e_image.set_from_icon_name('stock_smiley-1', gtk.ICON_SIZE_SMALL_TOOLBAR)
		e_hbox.pack_start(e_image)
		e_image.show()
		
		arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE)
		e_hbox.pack_start(arrow)
		arrow.show()

		item.set_image(e_hbox)
		item.connect("clicked", self.__emoticons_button_clicked_cb)
		toolbox.pack_start(item, False)
		item.show()
		
#		separator = gtk.SeparatorToolItem()
#		toolbar.insert(separator, -1)
#		separator.show()

#		item = gtk.MenuToolButton(None, "Links")
#		item.set_menu(gtk.Menu())
#		item.connect("show-menu", self.__show_link_menu_cb)
#		toolbar.insert(item, -1)
#		item.show()

		toolbox = Toolbox()
		toolbox.connect('color-selected', self._color_selected)
		self.pack_start(toolbox, False)
		toolbox.show()

		spring = gtk.Label('')
		self.pack_start(spring, True)
		spring.show()

	def _color_selected(self, toolbox, color):
		self._editor.set_color(color)

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

	def _create_emoticons_popup(self):
		model = gtk.ListStore(gtk.gdk.Pixbuf, str)
		
		for name in Emoticons.get_instance().get_all():
			icon_theme = gtk.icon_theme_get_default()
			try:
				pixbuf = icon_theme.load_icon(name, 16, 0)
				model.append([pixbuf, name])
			except gobject.GError:
				pass

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
