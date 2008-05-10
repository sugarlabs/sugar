import gtk
import gobject
import gettext

_ = lambda msg: gettext.dgettext('sugar', msg)

from sugar.graphics import style
from sugar.graphics import iconentry

from controlpanel.detailview import DetailView

ICON = 'module-language'
TITLE = _('Language')

class Language(DetailView):
    def __init__(self, model, alerts):
        DetailView.__init__(self)
        self._model = model

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self.connect("realize", self.__realize_cb)

        self.restart = False
        self._lang_sid = 0
        self._lang = self._model.get_language()
        self._lang_set = self._lang

        self._entry = iconentry.IconEntry()
        self._entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                 'system-search')
        self._entry.add_clear_button()
        self._entry.modify_bg(gtk.STATE_INSENSITIVE, 
                        style.COLOR_WHITE.get_gdk_color())
        self._entry.modify_base(gtk.STATE_INSENSITIVE, 
                          style.COLOR_WHITE.get_gdk_color())          
        self.pack_start(self._entry, False)
        self._entry.show()

        self._scrolled_window = gtk.ScrolledWindow()
        self._scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self._scrolled_window.set_shadow_type(gtk.SHADOW_IN)

        self._store = gtk.ListStore(gobject.TYPE_STRING, 
                                    gobject.TYPE_STRING)        
        locales = model.readlocale()
        for locale in locales:
            self._store.append([locale[2], '%s (%s)' % 
                                (locale[0], locale[1])])

        self._treeview = gtk.TreeView(self._store)
        self._treeview.set_search_entry(self._entry)
        self._treeview.set_search_equal_func(self._search)
        self._treeview.set_search_column(1)
        self._scrolled_window.add(self._treeview)
        self._treeview.show()

        self._tvcolumn = gtk.TreeViewColumn(_('Language'))
        self.cell = gtk.CellRendererText()
        self._tvcolumn.pack_start(self.cell, True)
        self._tvcolumn.add_attribute(self.cell, 'text', 1)
        self._tvcolumn.set_sort_column_id(1)
        self._treeview.append_column(self._tvcolumn)

        for row in self._store:
            if self._lang in row[0]:
                self._treeview.set_cursor(row.path, self._tvcolumn, False)
                self._treeview.scroll_to_cell(row.path, self._tvcolumn, 
                                              True, 0.5, 0.5)
                break

        self._treeview.connect("cursor-changed", self.__langchanged_cd)

        self.pack_start(self._scrolled_window)
        self._scrolled_window.show()

    def undo(self):
        self._model.set_language(self._lang)
        self.restart = False

    def __realize_cb(self, widget):
        self._entry.grab_focus()

    def _search(self, model, column_, key, iter_, data=None):
        for row in model:
            if key in row[1] or key.capitalize() in row[1]:        
                self._treeview.set_cursor(row.path, self._tvcolumn, False)
                self._treeview.scroll_to_cell(row.path, self._tvcolumn, 
                                              True, 0.5, 0.5)
                return True
        return False

    def __langchanged_cd(self, treeview, data=None):
        row = treeview.get_selection().get_selected()
        if self._lang_set == self._store.get_value(row[1], 0):
            return

        if self._lang_sid:
            gobject.source_remove(self._lang_sid)
        self._lang_sid = gobject.timeout_add(1000, self.__lang_timeout_cb, 
                                             self._store.get_value(row[1], 0))

    def __lang_timeout_cb(self, code):        
        self._lang_sid = 0        
        self._model.set_language(code)
        self.restart = True        
        self._lang_set = code
        return False
