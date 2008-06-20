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
import os
import gobject
import logging
from gettext import gettext as _

from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar.graphics.alert import Alert
import config 
from session import get_session_manager

from controlpanel.toolbar import MainToolbar
from controlpanel.toolbar import SectionToolbar

_logger = logging.getLogger('ControlPanel')
_MAX_COLUMNS = 5

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
        self._section_view = None
        self._section_toolbar = None
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

        self._options = self._get_options()
        self._current_option = None
        self._setup_main()
        self._setup_section()
        self._show_main_view()

    def __realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(True)

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
            sectionicon = _SectionIcon(icon_name=self._options[option]['icon'],
                                       title=self._options[option]['title'],
                                       xo_color=self._options[option]['color'],
                                       pixel_size=style.GRID_CELL_SIZE)
            sectionicon.connect('button_press_event', 
                               self.__select_option_cb, option)
            sectionicon.show()
            
            self._table.attach(sectionicon, column, column + 1, row, row + 1) 
            self._options[option]['button'] = sectionicon

            column += 1
            if column == _MAX_COLUMNS:
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
                if query.lower() in key.lower():
                    self._options[option]['button'].set_sensitive(True)
                    found = True
                    break
            if not found:
                self._options[option]['button'].set_sensitive(False)

    def _setup_section(self):
        self._section_toolbar = SectionToolbar()
        self._section_toolbar.connect('cancel-clicked', 
                                     self.__cancel_clicked_cb)
        self._section_toolbar.connect('accept-clicked', 
                                     self.__accept_clicked_cb)

    def _show_section_view(self, option):
        self._set_toolbar(self._section_toolbar)

        icon = self._section_toolbar.get_icon()
        icon.set_from_icon_name(self._options[option]['icon'], 
                                gtk.ICON_SIZE_LARGE_TOOLBAR)
        icon.props.xo_color = self._options[option]['color']
        title = self._section_toolbar.get_title()
        title.set_text(self._options[option]['title'])
        self._section_toolbar.show()
        self._section_toolbar.accept_button.set_sensitive(True)

        self._current_option = option
        view_class =  self._options[option]['view']
        model = self._options[option]['model']
        self._section_view = view_class(model, 
                                         self._options[option]['alerts'])
        self._set_canvas(self._section_view)        
        self._section_view.show()
        self._section_view.connect('notify::is-valid', 
                                   self.__valid_section_cb)
        self._main_view.modify_bg(gtk.STATE_NORMAL, 
                                  style.COLOR_WHITE.get_gdk_color())

    def _get_options(self):    
        '''Get the available option information from the subfolders 
        model and view.
        '''
        options = {}

        subpath = ['controlpanel', 'view']
        names = os.listdir(os.path.join(config.shell_path, '/'.join(subpath))) 

        for name in names:
            if name.endswith('.py') and name != '__init__.py':
                tmp = name.strip('.py')
                mod = __import__('.'.join(subpath) + '.' + tmp, globals(), 
                                 locals(), [tmp]) 
                view_class_str = getattr(mod, 'CLASS', None)
                if view_class_str:
                    view_class = getattr(mod, view_class_str, None)
                    if not view_class:
                        _logger.error('The CLASS constant \'%s\' does not ' \
                                          'match a class name.' % view_class)
                    else:
                        options[tmp] = {}
                        options[tmp]['alerts'] = []
                        options[tmp]['view'] = view_class
                        options[tmp]['icon'] = getattr(mod, 'ICON', tmp)
                        options[tmp]['title'] = getattr(mod, 'TITLE', 
                                                              tmp)
                        options[tmp]['color'] = getattr(mod, 'COLOR', 
                                                              None)
                else:    
                    _logger.error('There is no CLASS constant specified in ' \
                                      'the view file \'%s\'.' % tmp)

        subpath = ['controlpanel', 'model']
        names = os.listdir(os.path.join(config.shell_path, '/'.join(subpath)))
     
        for name in names:
            if name.endswith('.py') and name != '__init__.py':
                tmp = name.strip('.py')
                if tmp in options:
                    mod = __import__('.'.join(subpath) + '.' + tmp, 
                                     globals(), locals(), [tmp])            
                    keywords = getattr(mod, 'KEYWORDS', [])
                    keywords.append(options[tmp]['title'].lower())
                    if tmp not in keywords:
                        keywords.append(tmp)
                    options[tmp]['model'] = ModelWrapper(mod)
                    options[tmp]['keywords'] = keywords

        return options

    def __cancel_clicked_cb(self, widget):
        self._section_view.undo()
        self._options[self._current_option]['alerts'] = [] 
        self._show_main_view()

    def __accept_clicked_cb(self, widget):
        if self._section_view.needs_restart:
            self._section_toolbar.accept_button.set_sensitive(False)
            alert = Alert()
            alert.props.title = _('Warning') 
            alert.props.msg = _('Changes require restart') 
                
            icon = Icon(icon_name='dialog-cancel')
            alert.add_button(gtk.RESPONSE_CANCEL, _('Cancel changes'), icon) 
            icon.show() 

            icon = Icon(icon_name='dialog-ok') 
            alert.add_button(gtk.RESPONSE_ACCEPT, _('Later'), icon) 
            icon.show() 

            icon = Icon(icon_name='system-restart') 
            alert.add_button(gtk.RESPONSE_APPLY, _('Restart now'), icon) 
            icon.show() 

            self._vbox.pack_start(alert, False)
            self._vbox.reorder_child(alert, 2) 
            alert.connect('response', self.__response_cb)
            alert.show()
        else:
            self._show_main_view()

    def __response_cb(self, alert, response_id):
        self._vbox.remove(alert)        
        if response_id is gtk.RESPONSE_CANCEL:             
            self._section_view.undo()
            self._section_view.setup()
            self._options[self._current_option]['alerts'] = []
            self._section_toolbar.accept_button.set_sensitive(True)
        elif response_id is gtk.RESPONSE_ACCEPT:             
            self._options[self._current_option]['alerts'] = \
                self._section_view.restart_alerts
            self._show_main_view()
        elif response_id is gtk.RESPONSE_APPLY:                         
            session_manager = get_session_manager()
            session_manager.logout()

    def __select_option_cb(self, button, event, option):
        self._show_section_view(option)

    def __search_changed_cb(self, maintoolbar, query):
        self._update(query)            

    def __stop_clicked_cb(self, widget):
        self.destroy()
    
    def __valid_section_cb(self, section_view, pspec):
        section_is_valid = section_view.props.is_valid
        self._section_toolbar.accept_button.set_sensitive(section_is_valid)
        
class ModelWrapper(object):
    def __init__(self, module):
        self._module = module
        self._options = {}
        self._setup()

    def _setup(self):
        methods = dir(self._module)
        for method in methods:
            if method.startswith('get_') and method[4:] != 'color':
                try:                        
                    self._options[method[4:]] = getattr(self._module, method)()
                except Exception:
                    self._options[method[4:]] = None

    def __getattr__(self, name):
        if name.startswith('get_') or name.startswith('set_') or  \
                name.startswith('read_'):
            return getattr(self._module, name)

    def undo(self):
        for key in self._options.keys():
            method = getattr(self._module, 'set_' + key, None)            
            if method and self._options[key] is not None:
                try:
                    method(self._options[key])
                except Exception, detail:
                    _logger.debug('Error undo option: %s' % detail)        

class _SectionIcon(gtk.EventBox):
    __gtype_name__ = "SugarSectionIcon"

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
        self._icon_name = None
        self._pixel_size = style.GRID_CELL_SIZE
        self._xo_color = None
        self._title = 'No Title'

        gobject.GObject.__init__(self, **kwargs)

        self._vbox = gtk.VBox()
        self._icon = Icon(icon_name=self._icon_name, 
                          pixel_size=self._pixel_size, 
                          xo_color=self._xo_color)
        self._vbox.pack_start(self._icon, expand=False, fill=False)

        self._label = gtk.Label(self._title)
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
            if self._icon_name != value:
                self._icon_name = value
        elif pspec.name == 'pixel-size':
            if self._pixel_size != value:
                self._pixel_size = value
        elif pspec.name == 'xo-color':
            if self._xo_color != value:
                self._xo_color = value
        elif pspec.name == 'title':
            if self._title != value:
                self._title = value

    def do_get_property(self, pspec):
        if pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'pixel-size':
            return self._pixel_size
        elif pspec.name == 'xo-color':
            return self._xo_color
        elif pspec.name == 'title':
            return self._title
