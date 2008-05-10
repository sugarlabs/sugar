import gtk
import gobject
import gettext
_ = lambda msg: gettext.dgettext('sugar', msg)

from sugar.graphics import style
from sugar.graphics import iconentry

from controlpanel.detailview import DetailView

ICON = 'module-date_and_time'
TITLE = _('Date & Time')

class Timezone(DetailView):
    def __init__(self, model, alerts):
        DetailView.__init__(self)
        self._model = model

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self.connect("realize", self.__realize_cb)

        self.restart = False
        self._zone_sid = 0
        self._zone = self._model.get_timezone()
        self._zone_set = self._zone

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

        self._store = gtk.ListStore(gobject.TYPE_STRING)        
        zones = model.read_timezones()
        for zone in zones:
            self._store.append([zone])

        self._treeview = gtk.TreeView(self._store)
        self._treeview.set_search_entry(self._entry)
        self._treeview.set_search_equal_func(self._search)
        self._treeview.set_search_column(0)
        self._scrolled_window.add(self._treeview)
        self._treeview.show()

        self._tvcolumn = gtk.TreeViewColumn(_('Timezone'))
        self.cell = gtk.CellRendererText()
        self._tvcolumn.pack_start(self.cell, True)
        self._tvcolumn.add_attribute(self.cell, 'text', 0)
        self._tvcolumn.set_sort_column_id(0)
        self._treeview.append_column(self._tvcolumn)

        for row in self._store:
            if self._zone == row[0]:
                self._treeview.set_cursor(row.path, self._tvcolumn, False)
                self._treeview.scroll_to_cell(row.path, self._tvcolumn, 
                                              True, 0.5, 0.5)
                break

        self._treeview.connect("cursor-changed", self.__zonechanged_cd)

        self.pack_start(self._scrolled_window)
        self._scrolled_window.show()

    def undo(self):
        self._model.set_timezone(self._zone)
        self.restart = False

    def __realize_cb(self, widget):
        self._entry.grab_focus()

    def _search(self, model, column_, key, iter_, data=None):
        for row in model:
            if key in row[0] or key.capitalize() in row[0]:        
                self._treeview.set_cursor(row.path, self._tvcolumn, False)
                self._treeview.scroll_to_cell(row.path, self._tvcolumn, 
                                              True, 0.5, 0.5)
                return True
        return False

    def __zonechanged_cd(self, treeview, data=None):
        list_, row = treeview.get_selection().get_selected()
        if not row:
            row = self._zone_set
        if self._zone_set == self._store.get_value(row, 0):
            return False
        
        if self._zone_sid:
            gobject.source_remove(self._zone_sid)
        self._zone_sid = gobject.timeout_add(1000, self.__lang_timeout_cb, row)
        return True

    def __lang_timeout_cb(self, row):        
        self._zone_sid = 0        
        self._model.set_timezone(self._store.get_value(row, 0))
        self.restart = True        
        self._zone_set = row
        return False
