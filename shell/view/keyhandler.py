import dbus
import gobject

from sugar import env
from hardware import hardwaremanager
from model.ShellModel import ShellModel
from _sugar import KeyGrabber
import sugar

_actions_table = {
    'F1'            : 'zoom_mesh',
    'F2'            : 'zoom_friends',
    'F3'            : 'zoom_home',
    'F4'            : 'zoom_activity',
    'F5'            : 'brightness_1',
    'F6'            : 'brightness_2',
    'F7'            : 'brightness_3',
    'F8'            : 'brightness_4',
    'F9'            : 'volume_1',
    'F10'           : 'volume_2',
    'F11'           : 'volume_3',
    'F12'           : 'volume_4',
    '<alt>F5'       : 'color_mode',
    '<alt>F8'       : 'b_and_w_mode',
    '<alt>equal'    : 'console',
    '<alt>0'        : 'console',
    '<alt>f'        : 'frame',
    '0x93'          : 'frame',
    '<alt>o'        : 'overlay',
    '0xE0'          : 'overlay',
    '0xDC'          : 'camera',
    '0x7C'          : 'shutdown',
    '<alt><shift>s' : 'shutdown',
    '0xEB'          : 'rotate',
    '<alt>r'        : 'rotate',
    '0xEC'          : 'keyboard_brightness',
    '<alt>Tab'      : 'home'
}

class KeyHandler(object):
    def __init__(self, shell):
        self._shell = shell
        self._hw_manager = hardwaremanager.get_hardware_manager()
        self._audio_manager = hardwaremanager.get_audio_manager()
        self._screen_rotation = 0

        self._key_grabber = KeyGrabber()
        self._key_grabber.connect('key-pressed',
                                  self._key_pressed_cb)
        self._key_grabber.connect('key-released',
                                  self._key_released_cb)

        for key in _actions_table.keys():
            self._key_grabber.grab(key)            

    def handle_zoom_mesh(self):
        self._shell.set_zoom_level(sugar.ZOOM_MESH)

    def handle_zoom_friends(self):
        self._shell.set_zoom_level(sugar.ZOOM_FRIENDS)

    def handle_zoom_home(self):
        self._shell.set_zoom_level(sugar.ZOOM_HOME)

    def handle_zoom_activity(self):
        self._shell.set_zoom_level(sugar.ZOOM_ACTIVITY)

    def handle_brightness_1(self):
        self._hw_manager.set_display_brightness(0)

    def handle_brightness_2(self):
        self._hw_manager.set_display_brightness(5)

    def handle_brightness_3(self):
        self._hw_manager.set_display_brightness(9)

    def handle_brightness_4(self):
        self._hw_manager.set_display_brightness(15)

    def handle_volume_1(self):
        self._audio_manager.set_volume(0)

    def handle_volume_2(self):
        self._audio_manager.set_volume(50)

    def handle_volume_3(self):
        self._audio_manager.set_volume(80)

    def handle_volume_4(self):
        self._audio_manager.set_volume(100)

    def handle_color_mode(self):
        self._hw_manager.set_display_mode(hardwaremanager.COLOR_MODE)

    def handle_b_and_w_mode(self):
        self._hw_manager.set_display_mode(hardwaremanager.B_AND_W_MODE)

    def handle_console(self):
        gobject.idle_add(self._toggle_console_visibility_cb)

    def handle_frame(self):
        self._shell.get_frame().notify_key_press()

    def handle_overlay(self):
        self._shell.toggle_chat_visibility()

    def handle_camera(self):
        current_activity = self._shell.get_current_activity()
        if current_activity:
            if current_activity.execute('camera', []):
                return

        self._shell.start_activity('org.laptop.CameraActivity')

    def handle_shutdown(self):
        model = self._shell.get_model()
        model.props.state = ShellModel.STATE_SHUTDOWN

        if env.is_emulator():
            return

        bus = dbus.SystemBus()
        proxy = bus.get_object('org.freedesktop.Hal',
                               '/org/freedesktop/Hal/devices/computer')
        mgr = dbus.Interface(proxy, 'org.freedesktop.Hal.Device.SystemPowerManagement')
        mgr.Shutdown()

    def handle_keyboard_brightness(self):
        self._hw_manager.toggle_keyboard_brightness()

    def handle_rotate(self):
        states = [ 'normal', 'left', 'inverted', 'right']

        self._screen_rotation += 1
        if self._screen_rotation == len(states):
            self._screen_rotation = 0

        gobject.spawn_async(['xrandr', '-o', states[self._screen_rotation]],
                            flags=gobject.SPAWN_SEARCH_PATH)

    def handle_home(self):
        # FIXME: finish alt+tab support
        pass

    def _key_pressed_cb(self, grabber, key):
        action = _actions_table[key]
        method = getattr(self, 'handle_' + action)
        method()

    def _key_released_cb(self, grabber, key):
        if key == '<shft><alt>F9':
            self._frame.notify_key_release()
        elif key == '0x93':
            self._frame.notify_key_release()

    def _toggle_console_visibility_cb(self):
        bus = dbus.SessionBus()
        proxy = bus.get_object('org.laptop.sugar.Console',
                               '/org/laptop/sugar/Console')
        console = dbus.Interface(proxy, 'org.laptop.sugar.Console')
        console.toggle_visibility()
