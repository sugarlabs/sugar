# Copyright (C) 2010 Software for Education, Entertainment and Training
# Activities
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
_logger = logging.getLogger('JournalWindow')

from gi.repository import Gtk, Gdk

from gettext import gettext as _

_journal_window = None

_css = b'''
.journal-window {
    background-color: #FFFFFF;
}
'''
_provider = Gtk.CssProvider()
_provider.load_from_data(_css)


class JournalWindow(Gtk.Box):

    def __init__(self):
        global _journal_window
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, _provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.add_css_class('journal-window')
        _journal_window = self

        self._toolbar_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._alert_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._canvas_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._canvas_area.set_vexpand(True)
        self._canvas_area.set_hexpand(True)

        self.append(self._toolbar_area)
        self.append(self._alert_area)
        self.append(self._canvas_area)

        self._canvas = None
        self._toolbar_box = None
        self._presenting = False

    @property
    def canvas(self):
        return self._canvas

    def set_canvas(self, widget):
        if self._canvas == widget:
            return
        if self._canvas is not None and self._canvas.get_parent() == self._canvas_area:
            self._canvas_area.remove(self._canvas)
        self._canvas = widget
        if widget is not None:
            if widget.get_parent() is not None:
                parent = widget.get_parent()
                if parent != self._canvas_area:
                    parent.remove(widget)
            if widget.get_parent() != self._canvas_area:
                self._canvas_area.append(widget)

    def set_toolbar_box(self, toolbar):
        if self._toolbar_box == toolbar:
            return
        if self._toolbar_box is not None and \
                self._toolbar_box.get_parent() == self._toolbar_area:
            self._toolbar_area.remove(self._toolbar_box)
        self._toolbar_box = toolbar
        if toolbar is not None:
            if toolbar.get_parent() is not None:
                parent = toolbar.get_parent()
                if parent != self._toolbar_area:
                    parent.remove(toolbar)
            if toolbar.get_parent() != self._toolbar_area:
                self._toolbar_area.append(toolbar)

    def get_toolbar_box(self):
        return self._toolbar_box

    def add_alert(self, alert):
        self._alert_area.append(alert)
        alert.set_visible(True)

    def remove_alert(self, alert):
        if alert.get_parent() == self._alert_area:
            self._alert_area.remove(alert)

    def minimize(self):
        pass

    def get_title(self):
        return _('Journal')

    def present(self):
        if self._presenting:
            return
        self._presenting = True
        try:
            _logger.debug('present() called')
            self.set_visible(True)
            
            from jarabe.model import shell
            shell_model = shell.get_model()
            if not shell_model:
                return

            for act in shell_model._activities:
                if act.is_journal():
                    if shell_model.get_active_activity() != act:
                        shell_model.activate_activity(act)
                    return
        finally:
            self._presenting = False

    def reveal(self):
        _logger.debug('reveal() called')
        self.set_visible(True)
        self.present()

    def close(self):
        self.set_visible(False)


def get_journal_window():
    return _journal_window
