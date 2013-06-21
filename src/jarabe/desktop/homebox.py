# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2008-2013 Sugar Labs
# Copyright (C) 2013 Daniel Francis
# Copyright (C) 2013 Walter Bender
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

from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.alert import Alert
from sugar3.graphics.icon import Icon

from jarabe.desktop import favoritesview
from jarabe.desktop.activitieslist import ActivitiesList
from jarabe.util.normalize import normalize_string
from jarabe.desktop.config import get_number_of_views

_favorites_views = []
for i in range(get_number_of_views()):
    _favorites_views.append(i)
_list_view = _favorites_views[-1] + 1


class HomeBox(Gtk.VBox):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, toolbar):
        logging.debug('STARTUP: Loading the home view')

        Gtk.VBox.__init__(self)

        self._favorites_boxes = []
        for i in range(get_number_of_views()):
            self._favorites_boxes.append(favoritesview.FavoritesBox(i))
        self._list_view = ActivitiesList()

        toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        toolbar.connect('view-changed', self.__toolbar_view_changed_cb)
        toolbar.search_entry.connect('icon-press',
                                     self.__clear_icon_pressed_cb)
        self._list_view.connect('clear-clicked',
                                self.__activitylist_clear_clicked_cb, toolbar)

        self._set_view(_favorites_views[0])
        self._query = ''

    def show_software_updates_alert(self):
        alert = Alert()
        updater_icon = Icon(icon_name='module-updater',
                            pixel_size=style.STANDARD_ICON_SIZE)
        alert.props.icon = updater_icon
        updater_icon.show()
        alert.props.title = _('Software Update')
        alert.props.msg = _('Update your activities to ensure'
                            ' compatibility with your new software')

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), cancel_icon)

        alert.add_button(Gtk.ResponseType.REJECT, _('Later'))

        erase_icon = Icon(icon_name='dialog-ok')
        alert.add_button(Gtk.ResponseType.OK, _('Check now'), erase_icon)

        children = self.get_children()
        if self._list_view in children:
            self._list_view.add_alert(alert)
        else:
            for i in range(get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self._favorites_boxes[i].add_alert(alert)
                    break
        alert.connect('response', self.__software_update_response_cb)

    def __software_update_response_cb(self, alert, response_id):
        children = self.get_children()
        if self._list_view in children:
            self._list_view.remove_alert()
        else:
            for i in range(get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self._favorites_boxes[i].remove_alert()

        if response_id != Gtk.ResponseType.REJECT:
            update_trigger_file = os.path.expanduser('~/.sugar-update')
            try:
                os.unlink(update_trigger_file)
            except OSError:
                logging.error('Software-update: Can not remove file %s',
                              update_trigger_file)

        if response_id == Gtk.ResponseType.OK:
            from jarabe.controlpanel.gui import ControlPanel
            panel = ControlPanel()
            panel.set_transient_for(self.get_toplevel())
            panel.show()
            panel.show_section_view('updater')
            panel.set_section_view_auto_close()

    def __toolbar_query_changed_cb(self, toolbar, query):
        self._query = normalize_string(query.decode('utf-8'))
        self._list_view.set_filter(self._query)
        for i in range(get_number_of_views()):
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
            for i in range(get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self._favorites_boxes[i].grab_focus()

    def _set_view(self, view):
        if view in _favorites_views:
            favorite = _favorites_views.index(view)

            children = self.get_children()
            if self._list_view in children:
                self.remove(self._list_view)
            else:
                for i in range(get_number_of_views()):
                    if i != favorite and self._favorites_boxes[i] in children:
                        self.remove(self._favorites_boxes[i])

            if self._favorites_boxes[favorite] not in children:
                self.add(self._favorites_boxes[favorite])
                self._favorites_boxes[favorite].show()
                self._favorites_boxes[favorite].grab_focus()
        elif view == _list_view:
            children = self.get_children()
            for i in range(get_number_of_views()):
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
            for i in range(get_number_of_views()):
                self._favorites_boxes[i].set_filter(self._query)
