# Copyright (C) 2006-2007, Red Hat, Inc.
# Copyright (C) 2009 Simon Schampijer
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

import os
import logging
import importlib
import types

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
#from gi.repository import SugarExt

try:
    from sugar4.test import uitree
except ImportError:
    uitree = None

from jarabe.model.sound import sound
from jarabe.model import shell
from jarabe.model import session
from jarabe.view.tabbinghandler import TabbingHandler
from jarabe.model.shell import ShellModel
from jarabe import config
from jarabe.journal import journalactivity
from jarabe.controlpanel.gui import ControlPanel

_VOLUME_STEP = sound.VOLUME_STEP
_VOLUME_MAX = 100
_TABBING_MODIFIER = getattr(Gdk.ModifierType, 'ALT_MASK', getattr(Gdk.ModifierType, 'MOD1_MASK', 0))

_actions_table = {
    'F1': 'zoom_mesh',
    'F2': 'zoom_group',
    'F3': 'zoom_home',
    'F4': 'zoom_activity',
    'F5': 'open_search',
    'F6': 'frame',
    'XF86AudioMute': 'volume_mute',
    'F11': 'volume_down',
    'XF86AudioLowerVolume': 'volume_down',
    'F12': 'volume_up',
    'XF86AudioRaiseVolume': 'volume_up',
    '<alt>F11': 'volume_min',
    '<alt>F12': 'volume_max',
    'XF86MenuKB': 'frame',
    '<alt>Tab': 'next_window',
    '<alt><shift>Tab': 'previous_window',
    '<alt>Escape': 'close_window',
    'XF86WebCam': 'open_search',
    '<alt><shift>f': 'frame',
    'XF86Search': 'open_search',
    '<alt><shift>m': 'open_controlpanel',
    '<alt><shift>o': 'open_search',
    '<alt><shift>q': 'logout',
    '<alt><shift>d': 'dump_ui_tree'
}

# These keys will not be trigger a action if a modal dialog is opened
_non_modal_action_keys = ('F1', 'F2', 'F3', 'F4', 'F5', 'F6')

_instance = None


class KeyHandler(object):

    def __init__(self, frame):
        self._frame = frame
        self._key_pressed = None
        self._keycode_pressed = 0
        self._keystate_pressed = 0
        self._handled_windows = set()

        self._tabbing_handler = TabbingHandler(self._frame, _TABBING_MODIFIER)

        for f in os.listdir(os.path.join(config.ext_path, 'globalkey')):
            if f.endswith('.py') and not f.startswith('__'):
                module_name = f[:-3]
                try:
                    logging.debug('Loading module %r', module_name)
                    module = importlib.import_module('globalkey.' + module_name)
                    for key in module.BOUND_KEYS:
                        if key in _actions_table:
                            raise ValueError('Key %r is already bound' % key)
                        _actions_table[key] = module
                except Exception:
                    logging.exception('Exception while loading extension:')

        app = shell.get_model()
        if app is not None:
            main_window = getattr(app, '_main_window', None)
            if main_window is not None:
                self.add_window(main_window)
            app.connect('window-added', self._on_window_added)

    def _on_window_added(self, application, window):
        if isinstance(window, Gtk.Window):
            self.add_window(window)

    def add_window(self, window):
        if window in self._handled_windows:
            return
        self._handled_windows.add(window)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self._key_pressed_cb)
        key_controller.connect('key-released', self._key_released_cb)
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        window.add_controller(key_controller)


    def _change_volume(self, step=None, value=None):
        if step is not None:
            volume = sound.get_volume() + step
        elif value is not None:
            volume = value

        volume = min(max(0, volume), _VOLUME_MAX)

        sound.set_volume(volume)
        sound.set_muted(volume == 0)

    def handle_previous_window(self, event_time):
        self._tabbing_handler.previous_activity(event_time)

    def handle_next_window(self, event_time):
        self._tabbing_handler.next_activity(event_time)

    def handle_close_window(self, event_time):
        active_activity = shell.get_model().get_active_activity()
        if active_activity is None or active_activity.is_journal():
            return

        active_activity.stop()

    def handle_zoom_mesh(self, event_time):
        shell.get_model().set_zoom_level(ShellModel.ZOOM_MESH, event_time)

    def handle_zoom_group(self, event_time):
        shell.get_model().set_zoom_level(ShellModel.ZOOM_GROUP, event_time)

    def handle_zoom_home(self, event_time):
        shell.get_model().set_zoom_level(ShellModel.ZOOM_HOME, event_time)

    def handle_zoom_activity(self, event_time):
        model = shell.get_model()
        if model.get_active_activity() is None:
            # No activity open: show Journal instead of the empty compositor.
            # Use get_journal() so the journal is initialized if needed —
            # same pattern as handle_open_search (F5).
            journalactivity.get_journal().reveal()
        else:
            model.set_zoom_level(ShellModel.ZOOM_ACTIVITY, event_time)

    def handle_volume_max(self, event_time):
        self._change_volume(value=_VOLUME_MAX)

    def handle_volume_min(self, event_time):
        self._change_volume(value=0)

    def handle_volume_mute(self, event_time):
        if sound.get_muted() is True:
            sound.set_muted(False)
        else:
            sound.set_muted(True)

    def handle_volume_up(self, event_time):
        self._change_volume(step=_VOLUME_STEP)

    def handle_volume_down(self, event_time):
        self._change_volume(step=-_VOLUME_STEP)

    def handle_frame(self, event_time):
        self._frame.notify_key_press()

    def handle_logout(self, event_time):
        if "SUGAR_DEVELOPER" in os.environ:
            session_manager = session.get_session_manager()
            session_manager.logout()
            GLib.timeout_add_seconds(3, session_manager.shutdown_completed)

    def handle_open_search(self, event_time):
        try:
            journal = journalactivity.get_journal()
            journal.show_journal()
        except Exception as e:
            logging.exception('Error in handle_open_search')

    def handle_open_controlpanel(self, event_time):
        shell_model = shell.get_model()
        activity = shell_model.get_active_activity()
        if activity is not None and activity.has_shell_window():
            return

        bundle_path = activity.get_bundle_path() if activity is not None else None
        if bundle_path is None:
            window_id = ""
        else:
            window_id = activity.get_bundle_id()

        if shell.get_model().has_modal():
            return

        self._frame.hide()

        panel = ControlPanel(window_id)
        activity.push_shell_window(panel)
        panel.connect('hide', activity.pop_shell_window)
        panel.set_visible(True)

    def handle_dump_ui_tree(self, event_time):
        if uitree:
            print(uitree.get_root().dump())
        else:
            logging.warning("uitree module not available.")

    def _key_pressed_cb(self, controller, keyval, keycode, state):
        key = Gdk.keyval_name(keyval)
        if not key:
            return False

        # Add XF86 prefix back for media keys so they match _actions_table
        if key in ['AudioMute', 'AudioLowerVolume', 'AudioRaiseVolume', 'MenuKB', 'WebCam', 'Search']:
            key = 'XF86' + key

        # Handle Alt+ combinations
        if state & Gdk.ModifierType.ALT_MASK:
            if key == 'Tab':
                if state & Gdk.ModifierType.SHIFT_MASK:
                    key = '<alt><shift>Tab'
                else:
                    key = '<alt>Tab'
            elif key == 'Escape':
                key = '<alt>Escape'
            elif key in ['F11', 'F12']:
                key = '<alt>' + key
            elif key in ['f', 'm', 'o', 'q', 'd']:
                if state & Gdk.ModifierType.SHIFT_MASK:
                    key = '<alt><shift>' + key

        if key in _actions_table:
            action = _actions_table[key]

            if key in _non_modal_action_keys and shell.get_model().has_modal():
                logging.debug('Key %s action stopped due to modal dialog open', key)
                return True

            event = controller.get_current_event()
            event_time = event.get_time() if event else 0

            if self._tabbing_handler.is_tabbing():
                if action not in ['next_window', 'previous_window']:
                    self._tabbing_handler.stop(event_time)
                    return True

            if isinstance(action, types.ModuleType) and hasattr(action, 'handle_key_press'):
                action.handle_key_press(key)
            elif isinstance(action, str):
                method = getattr(self, 'handle_' + action)
                method(event_time)
            else:
                logging.error('Invalid action %r', action)

            return True

        if self._tabbing_handler.is_tabbing():
            is_modifier = keyval in [Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R, Gdk.KEY_Shift_L, Gdk.KEY_Shift_R]
            if not is_modifier:
                event = controller.get_current_event()
                self._tabbing_handler.stop(event.get_time() if event else 0)
            return True

        return False

    def _key_released_cb(self, controller, keyval, keycode, state):
        logging.debug('_key_released_cb: %i %i', keycode, state)
        if self._tabbing_handler.is_tabbing():
            # stop tabbing and switch window when the modifier is released
            if keyval in [Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R]:
                event = controller.get_current_event()
                self._tabbing_handler.stop(event.get_time() if event else 0)

            return True
        return False


def setup(frame):
    global _instance
    _instance = KeyHandler(frame)


def get_instance():
    return _instance
