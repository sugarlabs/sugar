# Copyright (C) 2026, Sugar Labs (Shubham Sharma)
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

"""Jo in the Frame: the trigger for in-activity reflection.

A device icon that opens the moment card over the running activity.
The card itself lives in jarabe.journal.momentcard and is imported
lazily on tap, never at setup() time - devicestray swallows setup()
exceptions, so a heavy import here could silently drop the whole icon.
"""

import logging
from gettext import gettext as _

from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.tray import TrayIcon

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import shell
import jarabe.frame


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 600

    def __init__(self):
        TrayIcon.__init__(self, icon_name='reflectjo')
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.connect('button-release-event', self.__button_release_event_cb)
        self._panel = None
        self._pending = False

    def create_palette(self):
        palette = Palette(_('Reflect with Jo'))
        palette.props.secondary_text = _('Talk about your work')
        box = PaletteMenuBox()
        item = PaletteMenuItem(_('Open my Journal'), 'activity-journal')
        item.connect('activate', self.__open_journal_cb)
        box.append_item(item)
        box.show_all()
        palette.set_content(box)
        palette.set_group_id('frame')
        return palette

    def __open_journal_cb(self, item):
        jarabe.frame.get_view().hide()
        self.__reveal_journal()

    def __button_release_event_cb(self, widget, event):
        if self._pending:
            # A tap is already in flight; a fast second tap must not
            # queue a second present.
            return True
        active = self.__active_activity()
        if active is None or active.is_journal():
            jarabe.frame.get_view().hide()
            self.__reveal_journal()
            return True
        try:
            from jarabe.journal.momentcard import MomentCard
        except Exception:
            logging.exception('reflectjo: could not open the moment card')
            return True
        if self._panel is None:
            self._panel = MomentCard()
        self._pending = True
        event_time = event.time
        # The card appears once the Frame has finished retracting, or
        # the Frame would be frozen into the dimmed backdrop.
        jarabe.frame.get_view().hide(
            lambda: self.__present_cb(event_time))
        return True

    def __reveal_journal(self):
        try:
            from jarabe.journal import journalactivity
            journal = journalactivity.get_journal()
        except Exception:
            logging.exception('reflectjo: could not open the Journal')
            return
        if journal is not None:
            journal.reveal()

    def __present_cb(self, event_time):
        self._pending = False
        active = self.__active_activity()
        activity_id = active.get_activity_id() if active is not None \
            else None
        self._panel.present_over_activity(event_time, activity_id)

    def __active_activity(self):
        try:
            return shell.get_model().get_active_activity()
        except Exception:
            logging.exception('reflectjo: could not read active activity')
        return None


def setup(tray):
    tray.add_device(DeviceView())
