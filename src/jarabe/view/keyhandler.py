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

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import SugarExt

from sugar3.test import uitree

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
_TABBING_MODIFIER = Gdk.ModifierType.MOD1_MASK


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

        self._key_grabber = SugarExt.KeyGrabber()
        self._key_grabber.connect('key-pressed',
                                  self._key_pressed_cb)
        self._key_grabber.connect('key-released',
                                  self._key_released_cb)

        self._tabbing_handler = TabbingHandler(self._frame, _TABBING_MODIFIER)

        for f in os.listdir(os.path.join(config.ext_path, 'globalkey')):
            if f.endswith('.py') and not f.startswith('__'):
                module_name = f[:-3]
                try:
                    logging.debug('Loading module %r', module_name)
                    module = __import__('globalkey.' + module_name, globals(),
                                        locals(), [module_name])
                    for key in module.BOUND_KEYS:
                        if key in _actions_table:
                            raise ValueError('Key %r is already bound' % key)
                        _actions_table[key] = module
                except Exception:
                    logging.exception('Exception while loading extension:')

        self._key_grabber.grab_keys(_actions_table.keys())

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
        if active_activity.is_journal():
            return

        active_activity.stop()

    def handle_zoom_mesh(self, event_time):
        shell.get_model().set_zoom_level(ShellModel.ZOOM_MESH, event_time)

    def handle_zoom_group(self, event_time):
        shell.get_model().set_zoom_level(ShellModel.ZOOM_GROUP, event_time)

    def handle_zoom_home(self, event_time):
        shell.get_model().set_zoom_level(ShellModel.ZOOM_HOME, event_time)

    def handle_zoom_activity(self, event_time):
        shell.get_model().set_zoom_level(ShellModel.ZOOM_ACTIVITY, event_time)

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
            GObject.timeout_add_seconds(3, session_manager.shutdown_completed)

    def handle_open_search(self, event_time):
        journalactivity.get_journal().show_journal()

    def handle_open_controlpanel(self, event_time):
        shell_model = shell.get_model()
        activity = shell_model.get_active_activity()
        if activity.has_shell_window():
            return

        bundle_path = activity.get_bundle_path()
        if bundle_path is None:
            window_xid = 0
        else:
            # get activity name and window id
            window_xid = activity.get_xid()

        if shell.get_model().has_modal():
            return

        self._frame.hide()

        panel = ControlPanel(window_xid)
        activity.push_shell_window(panel)
        panel.connect('hide', activity.pop_shell_window)
        panel.show()

    def handle_dump_ui_tree(self, event_time):
        print uitree.get_root().dump()

    def _key_pressed_cb(self, grabber, keycode, state, event_time):
        key = grabber.get_key(keycode, state)
        logging.debug('_key_pressed_cb: %i %i %s', keycode, state, key)
        if key is not None:
            self._key_pressed = key
            self._keycode_pressed = keycode
            self._keystate_pressed = state

            # avoid switch to the Journal or change views if a modal dialog
            # is opened http://bugs.sugarlabs.org/ticket/4601
            if key in _non_modal_action_keys and \
                    shell.get_model().has_modal():
                logging.debug(
                    'Key %s action stopped due to modal dialog open', key)
                return

            action = _actions_table[key]
            if self._tabbing_handler.is_tabbing():
                # Only accept window tabbing events, everything else
                # cancels the tabbing operation.
                if action not in ['next_window', 'previous_window']:
                    self._tabbing_handler.stop(event_time)
                    return True

            if hasattr(action, 'handle_key_press'):
                action.handle_key_press(key)
            elif isinstance(action, basestring):
                method = getattr(self, 'handle_' + action)
                method(event_time)
            else:
                raise TypeError('Invalid action %r' % action)

            return True
        else:
            # If this is not a registered key, then cancel tabbing.
            if self._tabbing_handler.is_tabbing():
                if not grabber.is_modifier(keycode):
                    self._tabbing_handler.stop(event_time)
                return True

        return False

    def _key_released_cb(self, grabber, keycode, state, event_time):
        logging.debug('_key_released_cb: %i %i', keycode, state)
        if self._tabbing_handler.is_tabbing():
            # We stop tabbing and switch to the new window as soon as the
            # modifier key is raised again.
            if grabber.is_modifier(keycode, mask=_TABBING_MODIFIER):
                self._tabbing_handler.stop(event_time)

            return True
        return False


def setup(frame):
    global _instance
    _instance = KeyHandler(frame)
