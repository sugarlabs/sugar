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

import logging

from gi.repository import Gtk

from jarabe.desktop import favoritesview
from jarabe.desktop.activitieslist import ActivitiesList
from jarabe.util.normalize import normalize_string
from jarabe.model import desktop


class HomeBox(Gtk.VBox):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, toolbar):
        logging.debug('STARTUP: Loading the home view')

        Gtk.VBox.__init__(self)

        self._favorites_views_indicies = []
        for i in range(desktop.get_number_of_views()):
            self._favorites_views_indicies.append(i)
        self._list_view_index = self._favorites_views_indicies[-1] + 1

        self._favorites_boxes = []
        for i in range(desktop.get_number_of_views()):
            self._favorites_boxes.append(favoritesview.FavoritesBox(i))
        self._list_view = ActivitiesList()

        self._desktop_model = desktop.get_model()
        self._desktop_model.connect('desktop-view-icons-changed',
                                    self.__desktop_view_icons_changed_cb)

        toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        toolbar.connect('view-changed', self.__toolbar_view_changed_cb)
        toolbar.search_entry.connect('icon-press',
                                     self.__clear_icon_pressed_cb)
        self._list_view.connect('clear-clicked',
                                self.__activitylist_clear_clicked_cb, toolbar)

        self._set_view(self._favorites_views_indicies[0])
        self._query = ''

    def __desktop_view_icons_changed_cb(self, model):
        number_of_views = desktop.get_number_of_views()

        if len(self._favorites_views_indicies) < number_of_views:
            for i in range(number_of_views -
                           len(self._favorites_views_indicies)):
                self._favorites_views_indicies.append(
                    len(self._favorites_views_indicies) + i)
                self._favorites_boxes.append(
                    favoritesview.FavoritesBox(
                        len(self._favorites_views_indicies) - 1))
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
        self._query = normalize_string(query.decode('utf-8'))
        self._list_view.set_filter(self._query)
        for i in range(desktop.get_number_of_views()):
            self._favorites_boxes[i].set_filter(self._query)

    def __toolbar_view_changed_cb(self, toolbar, view):
        self._set_view(view)

    def __activitylist_clear_clicked_cb(self, widget, toolbar):
        toolbar.clear_query()

    def __clear_icon_pressed_cb(self, entry, icon_pos, event):
        self.grab_focus()

    def grab_focus(self):
        # overwrite grab focus to be able to grab focus on the
        # views which are packed inside a box
        children = self.get_children()
        if self._list_view in children:
            self._list_view.grab_focus()
        else:
            for i in range(desktop.get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self._favorites_boxes[i].grab_focus()

    def _set_view(self, view):
        if view in self._favorites_views_indicies:
            favorite = self._favorites_views_indicies.index(view)

            children = self.get_children()
            if self._list_view in children:
                self.remove(self._list_view)
            else:
                for i in range(desktop.get_number_of_views()):
                    if i != favorite and self._favorites_boxes[i] in children:
                        self.remove(self._favorites_boxes[i])

            if self._favorites_boxes[favorite] not in children:
                self.add(self._favorites_boxes[favorite])
                self._favorites_boxes[favorite].show()
                self._favorites_boxes[favorite].grab_focus()
        elif view == self._list_view_index:
            children = self.get_children()
            for i in range(desktop.get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self.remove(self._favorites_boxes[i])

            if self._list_view not in children:
                self.add(self._list_view)
                self._list_view.show()
                self._list_view.grab_focus()
        else:
            raise ValueError('Invalid view: %r' % view)

    _REDRAW_TIMEOUT = 5 * 60 * 1000  # 5 minutes

    def resume(self):
        pass

    def suspend(self):
        pass

    def has_activities(self):
        # TODO: Do we need this?
        # return self._donut.has_activities()
        return False

    def set_resume_mode(self, resume_mode, favorite_view=0):
        self._favorites_boxes[favorite_view].set_resume_mode(resume_mode)
        if resume_mode and self._query != '':
            self._list_view.set_filter(self._query)
            for i in range(desktop.get_number_of_views()):
                self._favorites_boxes[i].set_filter(self._query)
