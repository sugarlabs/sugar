import ctypes
import unittest
from unittest import mock

from jarabe.model import keyboard


class _FakeModifierKeymap(ctypes.Structure):
    _fields_ = [
        ('max_keypermod', ctypes.c_int),
        ('modifiermap', ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _make_modmap(max_keypermod, mapping):
    arr_type = ctypes.c_ubyte * len(mapping)
    arr = arr_type(*mapping)
    km = _FakeModifierKeymap()
    km.max_keypermod = max_keypermod
    km.modifiermap = ctypes.cast(arr, ctypes.POINTER(ctypes.c_ubyte))
    ptr = ctypes.pointer(km)
    ptr._arr = arr  # prevent GC
    return ptr


class TestGetNumlockModMask(unittest.TestCase):

    def _lib(self, keycode, modmap_ptr):
        lib = mock.MagicMock()
        lib.XKeysymToKeycode = mock.MagicMock(return_value=keycode)
        lib.XGetModifierMapping = mock.MagicMock(return_value=modmap_ptr)
        lib.XFreeModifiermap = mock.MagicMock()
        return lib

    def test_no_numlock_key(self):
        # keycode 0 means no Num_Lock key on this keyboard
        lib = self._lib(keycode=0, modmap_ptr=None)
        self.assertEqual(keyboard._get_numlock_mod_mask(lib, 0), 0)
        lib.XGetModifierMapping.assert_not_called()

    def test_numlock_not_mapped(self):
        # key exists but is not assigned to any modifier slot
        mapping = [0] * 16  # 8 modifiers * 2 keycodes each
        ptr = _make_modmap(2, mapping)
        lib = self._lib(keycode=77, modmap_ptr=ptr)
        self.assertEqual(keyboard._get_numlock_mod_mask(lib, 0), 0)
        lib.XFreeModifiermap.assert_called_once()

    def test_numlock_on_mod2(self):
        # most common case: Num_Lock on Mod2 (index 4), mask = 0x10
        mapping = [0] * 16
        mapping[4 * 2] = 77
        ptr = _make_modmap(2, mapping)
        lib = self._lib(keycode=77, modmap_ptr=ptr)
        self.assertEqual(keyboard._get_numlock_mod_mask(lib, 0), 1 << 4)

    def test_numlock_on_mod5(self):
        # less common case: Num_Lock on Mod5 (index 7), mask = 0x80
        mapping = [0] * 32  # 8 modifiers * 4 keycodes each
        mapping[7 * 4 + 1] = 99
        ptr = _make_modmap(4, mapping)
        lib = self._lib(keycode=99, modmap_ptr=ptr)
        self.assertEqual(keyboard._get_numlock_mod_mask(lib, 0), 1 << 7)

    def test_null_modmap(self):
        # NULL modmap must not call XFreeModifiermap
        lib = self._lib(keycode=77, modmap_ptr=None)
        self.assertEqual(keyboard._get_numlock_mod_mask(lib, 0), 0)
        lib.XFreeModifiermap.assert_not_called()


class TestEnableNumlock(unittest.TestCase):

    @mock.patch('ctypes.util.find_library', return_value=None)
    def test_no_libX11(self, _):
        # libX11 not found, should return silently
        keyboard._enable_numlock()

    @mock.patch('ctypes.CDLL')
    @mock.patch('ctypes.util.find_library', return_value='libX11.so.6')
    def test_no_display(self, _find, mock_cdll):
        # XOpenDisplay returns NULL, should return silently
        fake = mock.MagicMock()
        fake.XOpenDisplay.return_value = None
        mock_cdll.return_value = fake
        keyboard._enable_numlock()
        fake.XOpenDisplay.assert_called_once()

    @mock.patch('ctypes.CDLL')
    @mock.patch('ctypes.util.find_library', return_value='libX11.so.6')
    def test_no_numlock_keycode(self, _find, mock_cdll):
        # no Num_Lock key on this keyboard, XkbLockModifiers must not be called
        fake = mock.MagicMock()
        fake.XOpenDisplay.return_value = 0x1
        fake.XKeysymToKeycode.return_value = 0
        mock_cdll.return_value = fake
        keyboard._enable_numlock()
        fake.XkbLockModifiers.assert_not_called()
        fake.XCloseDisplay.assert_called_once()

    @mock.patch('ctypes.CDLL')
    @mock.patch('ctypes.util.find_library', return_value='libX11.so.6')
    def test_numlock_enabled(self, _find, mock_cdll):
        # Num_Lock on Mod2: XkbLockModifiers must be called with mask 0x10
        mapping = [0] * 16
        mapping[4 * 2] = 77
        modmap_ptr = _make_modmap(2, mapping)

        fake = mock.MagicMock()
        fake.XOpenDisplay.return_value = 0x1
        fake.XKeysymToKeycode.return_value = 77
        fake.XGetModifierMapping.return_value = modmap_ptr
        mock_cdll.return_value = fake

        keyboard._enable_numlock()

        fake.XkbLockModifiers.assert_called_once_with(0x1, 0x100, 0x10, 0x10)
        fake.XFlush.assert_called_once()
        fake.XCloseDisplay.assert_called_once()


class TestSetupCallsEnableNumlock(unittest.TestCase):

    @mock.patch('jarabe.model.keyboard._enable_numlock')
    @mock.patch('gi.repository.GdkX11.x11_get_default_xdisplay',
                return_value=None)
    @mock.patch('gi.repository.Gio.Settings.new')
    def test_setup_calls_enable_numlock(self, mock_settings,
                                       _mock_display, mock_enable):
        # setup() must always call _enable_numlock(), even with no display
        mock_settings.return_value.get_strv.return_value = []
        mock_settings.return_value.get_string.return_value = ''
        keyboard.setup()
        mock_enable.assert_called_once()


if __name__ == '__main__':
    unittest.main()
