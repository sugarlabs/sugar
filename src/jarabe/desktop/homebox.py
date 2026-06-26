# Copyright (C) 2008 One Laptop Per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio

from jarabe.desktop.favoritesview import FavoritesBox
from jarabe.desktop.activitieslist import ActivitiesList
from jarabe.util.normalize import normalize_string
from jarabe.model import desktop


def _get_children(box):
    children = []
    child = box.get_first_child()
    while child:
        children.append(child)
        child = child.get_next_sibling()
    return children


class HomeBox(Gtk.Box):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, toolbar):
        logging.debug('STARTUP: Loading the home view')

        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._favorites_views_indicies = []
        for i in range(desktop.get_number_of_views()):
            self._favorites_views_indicies.append(i)
        self._list_view_index = self._favorites_views_indicies[-1] + 1

        self._view_stack = Gtk.Stack()
        self._view_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self._view_stack.set_vexpand(True)
        self.append(self._view_stack)

        self._favorites_boxes = []
        for i in range(desktop.get_number_of_views()):
            box = FavoritesBox(i)
            self._favorites_boxes.append(box)
            self._view_stack.add_named(box, f"favorite_{i}")
            
        self._list_view = ActivitiesList()
        self._view_stack.add_named(self._list_view, "list")

        self._desktop_model = desktop.get_model()
        self._desktop_model.connect('desktop-view-icons-changed',
                                    self.__desktop_view_icons_changed_cb)

        toolbar.search_entry._icon_selected = []
        toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        toolbar.connect('view-changed', self.__toolbar_view_changed_cb)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed',
                               self.__search_entry_key_pressed_cb)
        toolbar.search_entry.add_controller(key_controller)


        self._list_view.connect('clear-clicked',
                                self.__activitylist_clear_clicked_cb, toolbar)

        self._last_view = self._favorites_views_indicies[0]
        self._query = ''
        self._resume_mode = Gio.Settings.new(
            'org.sugarlabs.user').get_boolean('resume-activity')

        # Show the default view after all state is initialised
        self._set_view(self._favorites_views_indicies[0])


    def __desktop_view_icons_changed_cb(self, model):
        number_of_views = desktop.get_number_of_views()

        if len(self._favorites_views_indicies) < number_of_views:
            for i in range(number_of_views -
                           len(self._favorites_views_indicies)):
                self._favorites_views_indicies.append(
                    len(self._favorites_views_indicies) + i)
                self._favorites_boxes.append(
                    FavoritesBox(len(self._favorites_views_indicies) - 1))
        elif number_of_views < len(self._favorites_views_indicies):
            for i in range(len(self._favorites_views_indicies) -
                           number_of_views):
                self._favorites_boxes.remove(self._favorites_boxes[-1])
                self._favorites_views_indicies.remove(
                    self._favorites_views_indicies[-1])

        self._list_view_index = number_of_views
        logging.debug('homebox: reassigning list view index to %d' %
                      (self._list_view_index))

    def __toolbar_query_changed_cb(self, toolbar, query):
        self._query = normalize_string(query)
        self._list_view.set_filter(self._query)
        for i in range(desktop.get_number_of_views()):
            self._favorites_boxes[i].set_filter(self._query)
        toolbar.search_entry._icon_selected = \
            self._list_view.get_activities_selected()

        # verify if one of the selected names is a perfect match
        # this is needed by the case of activities with names contained
        # in other activities like 'Paint' and 'MusicPainter'
        activity = None
        for activity in self._list_view.get_activities_selected():
            if activity['name'].upper() == query.upper():
                toolbar.search_entry._icon_selected = [activity]
                break

        # Don't change the selection if the entry has been autocompleted
        if activity is not None and len(toolbar.search_entry._icon_selected) == 1 \
           and not toolbar.search_entry.get_text() == activity['name']:
            pos = toolbar.search_entry.get_position()
            toolbar.search_entry.set_text(
                toolbar.search_entry._icon_selected[0]['name'])
            toolbar.search_entry.select_region(pos, -1)

        if not query and self._resume_mode:
            self._list_view.get_activities_selected()
        else:
            self.set_resume_mode(False)

        # when query has any string, then set search view else revert
        if query:
            self._set_view(self._list_view_index)
        else:
            self._set_view(self._last_view)

    def __toolbar_view_changed_cb(self, toolbar, view):
        self.set_view(view)

    def __search_entry_key_pressed_cb(self, controller, keyval, keycode, state):
        # wherever a single item is selected in a desktop view,
        # launch the activity on pressing return
        entry = controller.get_widget()
        if keyval == Gdk.KEY_Return and len(entry._icon_selected) == 1:
            self._list_view.run_activity(entry._icon_selected[0]['bundle_id'],
                                         self._resume_mode)
            entry._icon_selected = []
            self.set_resume_mode(self._resume_mode)
            return True

        return False

    def __activitylist_clear_clicked_cb(self, widget, toolbar):
        toolbar.search_entry.set_text('')
        toolbar.search_entry.grab_focus()

    def __clear_icon_pressed_cb(self, entry, icon_pos):
        self.grab_focus()

    def grab_focus(self):
        super().grab_focus()

    def set_view(self, view):
        if view in self._favorites_views_indicies:
            self._last_view = view
        self._set_view(view)

    def _set_view(self, view):
        if view in self._favorites_views_indicies:
            favorite = self._favorites_views_indicies.index(view)
            self._view_stack.set_visible_child_name(f"favorite_{favorite}")
            self._favorites_boxes[favorite].grab_focus()
        elif view == self._list_view_index:
            self._view_stack.set_visible_child_name("list")
            self._list_view.grab_focus()
        else:
            raise ValueError('Invalid view: %r' % view)

    _REDRAW_TIMEOUT = 5 * 60 * 1000  # 5 minutes

    def resume(self):
        pass

    def suspend(self):
        pass

    def set_resume_mode(self, resume_mode, favorite_view=0):
        self._resume_mode = resume_mode
        self._favorites_boxes[favorite_view].set_resume_mode(resume_mode)
        if resume_mode and self._query != '':
            self._list_view.set_filter(self._query)
            for i in range(desktop.get_number_of_views()):
                self._favorites_boxes[i].set_filter(self._query)
