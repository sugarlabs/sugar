# Copyright (C) 2008 One Laptop Per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import gettext
import os
import gobject
import logging

from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar.graphics.alert import Alert
import config 

from controlpanel.controltoolbar import MainToolbar
from controlpanel.controltoolbar import DetailToolbar

_ = lambda msg: gettext.dgettext('sugar', msg)


class ControlPanel(gtk.Window):
    __gtype_name__ = 'SugarControlPanel'

    def __init__(self):
        gtk.Window.__init__(self)

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = gtk.gdk.screen_width() - offset * 2
        height = gtk.gdk.screen_height() - offset * 2
        self.set_size_request(width, height)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS) 
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        self._toolbar = None
        self._canvas = None
        self._table = None
        self._separator = None
        self._detail_view = None
        self._detail_toolbar = None
        self._main_toolbar = None
        
        self._vbox = gtk.VBox()
        self._hbox = gtk.HBox()
        self._vbox.pack_start(self._hbox)
        self._hbox.show()

        self._main_view = gtk.EventBox()
        self._hbox.pack_start(self._main_view)
        self._main_view.modify_bg(gtk.STATE_NORMAL, 
                                  style.COLOR_BLACK.get_gdk_color())
        self._main_view.show()

        self.add(self._vbox)
        self._vbox.show()

        self.connect("realize", self.__realize_cb)

        self._options = {}
        self._current_option = None
        self._get_options()
        self._setup_main()
        self._setup_detail()
        self._show_main_view()

    def _update_accept_focus(self):
        self.window.set_accept_focus(True)

    def __realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self._update_accept_focus()

    def _set_canvas(self, canvas):
        if self._canvas:
            self._main_view.remove(self._canvas)
        if canvas:
            self._main_view.add(canvas)        
        self._canvas = canvas

    def _set_toolbar(self, toolbar):
        if self._toolbar:
            self._vbox.remove(self._toolbar)            
        self._vbox.pack_start(toolbar, False)
        self._vbox.reorder_child(toolbar, 0) 
        self._toolbar = toolbar
        if not self._separator: 
            self._separator = gtk.HSeparator()
            self._vbox.pack_start(self._separator, False)
            self._vbox.reorder_child(self._separator, 1)
            self._separator.show()

    def _setup_main(self):
        self._main_toolbar = MainToolbar()

        self._table = gtk.Table()
        #self._table.set_row_spacings(style.DEFAULT_SPACING)
        self._table.set_col_spacings(style.GRID_CELL_SIZE)
        self._table.set_border_width(style.GRID_CELL_SIZE)
        self._setup_options()
        self._main_toolbar.connect('stop-clicked', 
                                   self.__stop_clicked_cb)
        self._main_toolbar.connect('search-changed', 
                                   self.__search_changed_cb)

    def _setup_options(self):
        row = 0
        column = 0
        for option in self._options:
            gridwidget = _GridWidget(icon_name=self._options[option]['icon'],
                                     title=self._options[option]['title'],
                                     xo_color = self._options[option]['color'],
                                     pixel_size=style.GRID_CELL_SIZE)
            gridwidget.connect('button_press_event', 
                               self.__select_option_cb, option)
            gridwidget.show()
            
            self._table.attach(gridwidget, column, column+1, row, row+1) 
            self._options[option]['button'] = gridwidget

            column += 1
            if column == 5:
                column = 0
                row += 1        

    def _show_main_view(self):
        self._set_toolbar(self._main_toolbar)
        self._main_toolbar.show()
        self._set_canvas(self._table)
        self._main_view.modify_bg(gtk.STATE_NORMAL, 
                                  style.COLOR_BLACK.get_gdk_color())
        self._table.show()
        entry = self._main_toolbar.get_entry()
        entry.grab_focus()
        entry.set_text('')

    def _update(self, query):
        for option in self._options:            
            found = False
            for key in self._options[option]['keywords']:
                if query in key or query in key.upper() \
                        or query in key.capitalize():
                    self._options[option]['button'].set_sensitive(True)
                    found = True
                    break
            if not found:
                self._options[option]['button'].set_sensitive(False)

    def _setup_detail(self):
        self._detail_toolbar = DetailToolbar()
        self._detail_toolbar.connect('cancel-clicked', 
                                     self.__cancel_clicked_cb)
        self._detail_toolbar.connect('accept-clicked', 
                                     self.__accept_clicked_cb)

    def _show_detail_view(self, option):
        self._set_toolbar(self._detail_toolbar)

        icon = self._detail_toolbar.get_icon()
        icon.set_from_icon_name(self._options[option]['icon'], 
                                gtk.ICON_SIZE_LARGE_TOOLBAR)
        icon.props.xo_color = self._options[option]['color']
        title = self._detail_toolbar.get_title()
        title.set_text(self._options[option]['title'])
        self._detail_toolbar.show()
        self._detail_toolbar.accept_button.set_sensitive(True)

        self._current_option = option
        class_pointer =  self._options[option]['view']
        model = self._options[option]['model']
        self._detail_view = class_pointer(model, 
                                          self._options[option]['alerts'])
        self._set_canvas(self._detail_view)        
        self._detail_view.show()
        self._detail_view.connect('valid-section', self.__valid_section_cb)
        self._main_view.modify_bg(gtk.STATE_NORMAL, 
                                  style.COLOR_WHITE.get_gdk_color())

    def _get_options(self):    
        '''Get the available option information from the subfolders 
        model and view.
        structure: 
            {'optionname': {'view', 'model', 'button', 'keywords', 'icon'} }
        '''

        subpath = ['controlpanel', 'view']
        names = os.listdir(os.path.join(config.shell_path, '/'.join(subpath)))        
        for name in names:
            if name.endswith('.py') and name != '__init__.py':
                tmp = name.strip('.py')
                mod = __import__('.'.join(subpath) + '.' + tmp, globals(), 
                                 locals(), [tmp])                            
                class_pointer = getattr(mod, tmp[0].capitalize()  
                                        + tmp[1:], None)
                if class_pointer:
                    self._options[tmp] = {}
                    self._options[tmp]['alerts'] = []
                    self._options[tmp]['view'] = class_pointer                
                    self._options[tmp]['icon'] = getattr(mod, 'ICON', tmp)
                    self._options[tmp]['title'] = getattr(mod, 'TITLE', tmp)
                    self._options[tmp]['color'] = getattr(mod, 'COLOR', None)

        subpath = ['controlpanel', 'model']
        names = os.listdir(os.path.join(config.shell_path, '/'.join(subpath)))        
        for name in names:
            if name.endswith('.py') and name != '__init__.py':
                tmp = name.strip('.py')
                if tmp in self._options:
                    mod = __import__('.'.join(subpath) + '.' + tmp, 
                                     globals(), locals(), [tmp])            
                    keywords = getattr(mod, 'KEYWORDS', [])
                    keywords.append(self._options[tmp]['title'].lower())
                    if tmp not in keywords:
                        keywords.append(tmp)
                    self._options[tmp]['model'] = mod
                    self._options[tmp]['keywords'] = keywords

    def __cancel_clicked_cb(self, widget, data=None):
        self._detail_view.undo()
        self._show_main_view()

    def __accept_clicked_cb(self, widget, data=None):
        if self._detail_view.restart:
            self._detail_toolbar.accept_button.set_sensitive(False)
            alert = Alert()
            alert.props.title = _('Warning') 
            alert.props.msg = _('Changes require restart to take effect') 
                
            cancel_icon = Icon(icon_name='dialog-cancel')
            alert.add_button(gtk.RESPONSE_CANCEL, _('Cancel'), cancel_icon) 
            cancel_icon.show() 

            later_icon = Icon(icon_name='dialog-ok') 
            alert.add_button(gtk.RESPONSE_ACCEPT, _('Later'), later_icon) 
            later_icon.show() 

            # TODO
            # Handle restart

            self._vbox.pack_start(alert, False)
            self._vbox.reorder_child(alert, 2) 
            alert.connect('response', self.__response_cb)
            alert.show()
        else:
            self._show_main_view()

    def __response_cb(self, alert, response_id):
        self._vbox.remove(alert)        
        if response_id is gtk.RESPONSE_CANCEL:             
            logging.debug('Cancel...')        
            self._detail_view.undo()
            self._detail_toolbar.accept_button.set_sensitive(True)
        elif response_id is gtk.RESPONSE_ACCEPT:             
            logging.debug('Later...')
            self._options[self._current_option]['alerts'] = \
                self._detail_view.restart_alerts
            self._show_main_view()
        elif response_id is gtk.RESPONSE_APPLY:             
            logging.debug('Restart...')

    def __select_option_cb(self, button, event, option=None):
        self._show_detail_view(option)

    def __search_changed_cb(self, maintoolbar, query):
        self._update(query)            

    def __stop_clicked_cb(self, widget, data=None):
        self.destroy()
    
    def __valid_section_cb(self, widget, valid):
        self._detail_toolbar.accept_button.set_sensitive(valid)

class _GridWidget(gtk.EventBox):
    __gtype_name__ = "SugarGridWidget"

    __gproperties__ = {
        'icon-name'    : (str, None, None, None,
                          gobject.PARAM_READWRITE),
        'pixel-size'   : (object, None, None,
                          gobject.PARAM_READWRITE),
        'xo-color'     : (object, None, None,
                          gobject.PARAM_READWRITE),
        'title'        : (str, None, None, None,
                          gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs): 
        self.icon_name = None
        self.pixel_size = style.GRID_CELL_SIZE
        self.xo_color = None
        self.title = 'No Title'

        gobject.GObject.__init__(self, **kwargs)

        self._vbox = gtk.VBox()
        self._icon = Icon(icon_name=self.icon_name, pixel_size=self.pixel_size, 
                          xo_color=self.xo_color)
        self._vbox.pack_start(self._icon, expand=False, fill=False)

        self._label = gtk.Label(self.title)
        self._label.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_WHITE.get_gdk_color())
        self._vbox.pack_start(self._label, expand=False, fill=False)
        
        self._vbox.set_spacing(style.DEFAULT_SPACING)
        self.set_visible_window(False)
        self.set_app_paintable(True)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK)

        self.add(self._vbox)
        self._vbox.show()
        self._label.show()
        self._icon.show()

    def get_icon(self):
        return self._icon

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            if self.icon_name != value:
                self.icon_name = value
        elif pspec.name == 'pixel-size':
            if self.pixel_size != value:
                self.pixel_size = value
        elif pspec.name == 'xo-color':
            if self.xo_color != value:
                self.xo_color = value
        elif pspec.name == 'title':
            if self.title != value:
                self.title = value

    def do_get_property(self, pspec):
        if pspec.name == 'icon-name':
            return self.icon_name
        elif pspec.name == 'pixel-size':
            return self.pixel_size
        elif pspec.name == 'xo-color':
            return self.xo_color
        elif pspec.name == 'title':
            return self.title
