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

from gettext import gettext as _
import logging
import os

import gobject
import gtk

from sugar.graphics import style
from sugar.graphics import iconentry
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.alert import Alert
from sugar.graphics.icon import Icon
from sugar import profile
from sugar import activity
from sugar.bundle.activitybundle import ActivityBundle

from view.home import favoritesview
from view.home.activitieslist import ActivitiesList

_FAVORITES_VIEW = 0
_LIST_VIEW = 1

_AUTOSEARCH_TIMEOUT = 1000

def _convert_layout_constant(profile_constant):
    for layoutid, layoutclass in favoritesview._LAYOUT_MAP.items():
        if profile_constant == layoutclass.profile_key:
            return layoutid
    logging.warning('Incorrect favorites_layout value: %r' % \
                    profile_constant)
    return favoritesview.RING_LAYOUT

class HomeBox(gtk.VBox):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self):
        gobject.GObject.__init__(self)

        self._favorites_view = favoritesview.FavoritesView()
        self._list_view = ActivitiesList()
        self._enable_xo_palette = False

        self._favorites_view.connect('erase-activated',
                                     self.__erase_activated_cb)
        self._list_view.connect('erase-activated', self.__erase_activated_cb)

        self._toolbar = HomeToolbar()
        self._toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        self._toolbar.connect('view-changed', self.__toolbar_view_changed_cb)
        self.pack_start(self._toolbar, expand=False)
        self._toolbar.show()

        profile_layout_constant = profile.get_profile().favorites_layout
        layout = _convert_layout_constant(profile_layout_constant)
        self._set_view(_FAVORITES_VIEW, layout)

    def __erase_activated_cb(self, view, bundle_id):
        registry = activity.get_registry()
        activity_info = registry.get_activity(bundle_id)

        alert = Alert()
        alert.props.title = _('Confirm erase')
        alert.props.msg = \
                _('Confirm erase: Do you want to permanently erase %s?') \
                % activity_info.name

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(gtk.RESPONSE_CANCEL, _('Keep'), cancel_icon)

        erase_icon = Icon(icon_name='dialog-ok')
        alert.add_button(gtk.RESPONSE_OK, _('Erase'), erase_icon)

        if self._list_view in self.get_children():
            self._list_view.add_alert(alert)
        else:
            self._favorites_view.add_alert(alert)
        # TODO: If the favorite layouts didn't hardcoded the box size, we could
        # just pack an alert between the toolbar and the canvas.
        #self.pack_start(alert, False)
        #self.reorder_child(alert, 1)
        alert.connect('response', self.__erase_confirmation_dialog_response_cb,
                bundle_id)

    def __erase_confirmation_dialog_response_cb(self, alert, response_id,
                                                bundle_id):
        if self._list_view in self.get_children():
            self._list_view.remove_alert()
        else:
            self._favorites_view.remove_alert()
        if response_id == gtk.RESPONSE_OK:
            registry = activity.get_registry()
            activity_info = registry.get_activity(bundle_id)
            ActivityBundle(activity_info.path).uninstall()
            
    def show_software_updates_alert(self):
        alert = Alert()
        updater_icon = Icon(icon_name='module-updater', 
                    pixel_size = style.STANDARD_ICON_SIZE)
        alert.props.icon = updater_icon
        updater_icon.show()
        alert.props.title = _('Software Update')
        alert.props.msg = _('Update your activities to ensure' 
                            ' compatibility with your new software') 

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(gtk.RESPONSE_CANCEL, _('Cancel'), cancel_icon)

        alert.add_button(gtk.RESPONSE_REJECT, _('Later'))

        erase_icon = Icon(icon_name='dialog-ok')
        alert.add_button(gtk.RESPONSE_OK, _('Check now'), erase_icon)

        if self._list_view in self.get_children():
            self._list_view.add_alert(alert)
        else:
            self._favorites_view.add_alert(alert)
        alert.connect('response', self.__software_update_response_cb)
        
    def __software_update_response_cb(self, alert, response_id):
        if self._list_view in self.get_children():
            self._list_view.remove_alert()
        else:
            self._favorites_view.remove_alert()

        if response_id != gtk.RESPONSE_REJECT:
            update_trigger_file = os.path.expanduser('~/.sugar-update')
            try:
                os.unlink(update_trigger_file)
            except OSError:
                logging.error('Software-update: Can not remove file %s' % 
                              update_trigger_file)

        if response_id == gtk.RESPONSE_OK:
            from controlpanel.gui import ControlPanel
            panel = ControlPanel()
            panel.set_transient_for(self.get_toplevel())
            panel.show()
            panel.show_section_view('updater')
            panel.set_section_view_auto_close()

    def __toolbar_query_changed_cb(self, toolbar, query):
        query = query.lower()
        self._list_view.set_filter(query)

    def __toolbar_view_changed_cb(self, toolbar, view, layout):
        self._set_view(view, layout)
        if layout is not None:
            current_profile = profile.get_profile()
            profile_key = favoritesview._LAYOUT_MAP[layout].profile_key
            if profile_key != current_profile.favorites_layout:
                current_profile.favorites_layout = profile_key
                current_profile.save()
            else:
                logging.warning('Incorrect layout requested: %r' % layout)

    def _set_view(self, view, layout):
        if view == _FAVORITES_VIEW:
            if self._list_view in self.get_children():
                self.remove(self._list_view)

            self._favorites_view.layout = layout

            if self._enable_xo_palette:
                self._favorites_view.enable_xo_palette()

            if self._favorites_view not in self.get_children():
                self.add(self._favorites_view)
                self._favorites_view.show()
        elif view == _LIST_VIEW:
            if self._favorites_view in self.get_children():
                self.remove(self._favorites_view)

            if self._list_view not in self.get_children():
                self.add(self._list_view)
                self._list_view.show()
        else:
            raise ValueError('Invalid view: %r' % view)

    _REDRAW_TIMEOUT = 5 * 60 * 1000 # 5 minutes

    def resume(self):
        pass

    def suspend(self):
        pass

    def has_activities(self):
        # TODO: Do we need this?
        #return self._donut.has_activities()
        return False

    def enable_xo_palette(self):
        self._enable_xo_palette = True
        if self._favorites_view is not None:
            self._favorites_view.enable_xo_palette()

    def focus_search_entry(self):
        self._toolbar.search_entry.grab_focus()


class HomeToolbar(gtk.Toolbar):
    __gtype_name__ = 'SugarHomeToolbar'

    __gsignals__ = {
        'query-changed': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([str])),
        'view-changed':  (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([object, object]))
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self._query = None
        self._autosearch_timer = None

        self._add_separator()

        tool_item = gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'system-search')
        self.search_entry.add_clear_button()
        self.search_entry.set_width_chars(25)
        self.search_entry.connect('activate', self.__entry_activated_cb)
        self.search_entry.connect('changed', self.__entry_changed_cb)
        tool_item.add(self.search_entry)
        self.search_entry.show()

        self._add_separator(expand=True)

        favorites_button = FavoritesButton()
        favorites_button.connect('toggled', self.__view_button_toggled_cb,
                                 _FAVORITES_VIEW)
        self.insert(favorites_button, -1)
        favorites_button.show()

        self._list_button = RadioToolButton(named_icon='view-list')
        self._list_button.props.group = favorites_button
        self._list_button.props.tooltip = _('List view')
        self._list_button.props.accelerator = _('<Ctrl>2')
        self._list_button.connect('toggled', self.__view_button_toggled_cb,
                            _LIST_VIEW)
        self.insert(self._list_button, -1)
        self._list_button.show()

        self._add_separator()

    def __view_button_toggled_cb(self, button, view):
        if button.props.active:
            if view == _FAVORITES_VIEW:
                self.emit('view-changed', view, button.layout)
            else:
                self.emit('view-changed', view, None)
            
    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE,
                                       style.GRID_CELL_SIZE)
        self.insert(separator, -1)
        separator.show()

    def __entry_activated_cb(self, entry):
        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query

            if self._query is not '':
                self._list_button.props.active = True
            self.emit('query-changed', self._query)

    def __entry_changed_cb(self, entry):
        if not entry.props.text:
            entry.activate()
            return

        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        self._autosearch_timer = gobject.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                     self.__autosearch_timer_cb)

    def __autosearch_timer_cb(self):
        self._autosearch_timer = None
        self.search_entry.activate()
        return False

class FavoritesButton(RadioToolButton):
    __gtype_name__ = 'SugarFavoritesButton'
    
    def __init__(self):
        RadioToolButton.__init__(self)

        self.props.tooltip = _('Favorites view')
        self.props.accelerator = _('<Ctrl>1')
        self.props.group = None

        profile_layout_constant = profile.get_profile().favorites_layout
        self._layout = _convert_layout_constant(profile_layout_constant)
        self._update_icon()

        i = 0
        for layoutid, layoutclass in sorted(favoritesview._LAYOUT_MAP.items()):
            menu_item = gtk.MenuItem()
            menu_item.add(Icon(icon_name=layoutclass.icon_name,
                               icon_size=gtk.ICON_SIZE_MENU))
            menu_item.connect('activate', self.__layout_activate_cb,
                              layoutid)
            self.props.palette.menu.attach(menu_item, i, i+1, 0, 1)
            menu_item.show_all()
            i += 1
        # in HEAD, we can have the palette.menu emit('item-inserted'),
        # but sucrose-0.82 doesn't have that patch, so call a private method =(
        self.props.palette._update_separators()
        self.props.palette.menu.show()


    def __layout_activate_cb(self, menu_item, layout):
        if self._layout == layout and self.props.active:
            return
        elif self._layout != layout:
            self._layout = layout
            self._update_icon()
        if not self.props.active:
            self.props.active = True
        else:
            self.emit('toggled')

    def _update_icon(self):
        self.props.named_icon = favoritesview._LAYOUT_MAP[self._layout]\
                                .icon_name

    def _get_layout(self):
        return self._layout
    layout = property(_get_layout, None)

