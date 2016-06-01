# Copyright (C) 2016, Abhijit Patel
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
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk

from jarabe.view.friendlistpopup import FriendListPopup
from jarabe.journal.expandedentry import TextView, BuddyList 
from jarabe.journal.listview import ListView

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton

class ProjectView(Gtk.VBox):

    def __init__(self, **kwargs):
    	self.project_metadata = None

    	Gtk.VBox.__init__(self)
        description_box, self._description = self._create_description()
        
        self.pack_start(description_box, False, True, 0)
        logging.debug('Project view setup')
        
        hbox = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)

        self._buddy_list = Gtk.VBox()
        hbox.pack_start(self._buddy_list, True, False, 0)
        self.pack_start(hbox, False, True, 0)
        hbox.show()

        

    def _add_buddy_button_clicked_cb(self, button):
        logging.debug('[GSoC]_add_buddy_button_clicked_cb')
        pop_up = FriendListPopup()
        pop_up.connect('friend-selected', self.__friend_selected_cb)

    def __friend_selected_cb(self, xyz, selected):
        logging.debug('[GSoC]__friend_selected_cb %r' %selected)
        buddies = []
        if not self.project_metadata.get('buddies'):
            self.project_metadata['buddies'] = []
        for buddy in selected:
            self.project_metadata['buddies'].append((buddy.nick, buddy.color))

        #datastore._update_ds_entry(self.project_metadata['uid'])
        #model.write(self.project_metadata['uid'])
        self._project_buddies(self.project_metadata)
        logging.debug('[GSoC]friend finally selected')

    def _project_buddies(self, metadata):
        logging.debug('[GSoC]_project_buddies')
        for child in self._buddy_list.get_children():
            self._buddy_list.remove(child)
            # FIXME: self._buddy_list.foreach(self._buddy_list.remove)
        self._buddy_list.pack_start(self._create_buddy_list(metadata), False, False,
                                    style.DEFAULT_SPACING)
        self._buddy_list.show_all()
        logging.debug('[GSoC]project_buddies ended')                

    def _create_buddy_list(self, metadata):
        self.project_metadata = metadata
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        add_buddy_button = ToolButton('list-add') # suggest icon for this
        add_buddy_button.set_tooltip(_('Add Buddy'))
        add_buddy_button.connect('clicked',self._add_buddy_button_clicked_cb)
        vbox.pack_start(add_buddy_button, False, False, style.DEFAULT_SPACING)
        add_buddy_button.show()

        text = Gtk.Label()
        text.set_markup('<span foreground="%s">%s</span>' % (
            style.COLOR_BUTTON_GREY.get_html(), _('Participants:')))
        halign = Gtk.Alignment.new(0, 0, 0, 0)
        halign.add(text)
        vbox.pack_start(halign, False, False, 0)

        if metadata.get('buddies'):
            #buddies = json.loads(metadata['buddies']).values()
            buddies = metadata['buddies']
            logging.debug('[GSoC]buddies are %r' %buddies)
            #for buddy in metadata['buddies']:
            #    buddies.append((buddy.nick, buddy.color))
            vbox.pack_start(BuddyList(buddies), False, False, 0)
            logging.debug('[GSoC]created_buddy_list ')
            vbox.show_all()
            return vbox
        else:
            vbox.show()
            return vbox

    
    def _create_description(self):
        widget = TextView()
        widget.connect('focus-out-event',
                       self._description_tags_focus_out_event_cb)
        return self._create_scrollable(widget, label=_('Description:')), widget

    def _description_tags_focus_out_event_cb(self, text_view, event):
        logging.debug('[GSoC]blah here')

    def _create_scrollable(self, widget, label=None):
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        if label is not None:
            logging.debug('[GSoC]create_scrollable')
            text = Gtk.Label()
            text.set_markup('<span foreground="%s">%s</span>' % (
                style.COLOR_BUTTON_GREY.get_html(), label))

            halign = Gtk.Alignment.new(0, 0, 0, 0)
            halign.add(text)
            vbox.pack_start(halign, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        scrolled_window.add(widget)
        vbox.pack_start(scrolled_window, True, True, 0)

        return vbox
         
