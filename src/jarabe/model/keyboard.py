# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2009, One Laptop Per Child Association Inc
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

import ctypes
import ctypes.util
import logging

import gi
gi.require_version('Xkl', '1.0')
from gi.repository import Gio
from gi.repository import GdkX11
from gi.repository import Xkl

# Xkb constant for "use core keyboard device"
_XKB_USE_CORE_KBD = 0x0100


def _get_numlock_mod_mask(libX11, display):
    """Return the X modifier mask for Num_Lock, or 0 if not found.

    Walks the X modifier map to discover which modifier bit
    (Mod1 through Mod5) is bound to the Num_Lock keysym.
    """
    XK_Num_Lock = 0xFF7F
    numlock_keycode = libX11.XKeysymToKeycode(display, XK_Num_Lock)
    if numlock_keycode == 0:
        return 0

    modmap_p = libX11.XGetModifierMapping(display)
    if not modmap_p:
        return 0

    max_kpm = modmap_p.contents.max_keypermod
    numlock_mask = 0
    for mod_index in range(8):
        for j in range(max_kpm):
            if modmap_p.contents.modifiermap[mod_index * max_kpm + j] == \
                    numlock_keycode:
                numlock_mask = 1 << mod_index
                break
        if numlock_mask:
            break

    libX11.XFreeModifiermap(modmap_p)
    return numlock_mask


def _enable_numlock():
    """Enable NumLock at startup if the keyboard has a Num_Lock key.
    """
    try:
        libx11_path = ctypes.util.find_library('X11')
        if not libx11_path:
            logging.debug('_enable_numlock: libX11 not found')
            return

        libX11 = ctypes.CDLL(libx11_path)

        # XModifierKeymap struct used by XGetModifierMapping
        class XModifierKeymap(ctypes.Structure):
            _fields_ = [
                ('max_keypermod', ctypes.c_int),
                ('modifiermap', ctypes.POINTER(ctypes.c_ubyte)),
            ]

        libX11.XOpenDisplay.restype = ctypes.c_void_p
        libX11.XKeysymToKeycode.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong]
        libX11.XKeysymToKeycode.restype = ctypes.c_ubyte
        libX11.XGetModifierMapping.argtypes = [ctypes.c_void_p]
        libX11.XGetModifierMapping.restype = ctypes.POINTER(
            XModifierKeymap)
        libX11.XFreeModifiermap.argtypes = [
            ctypes.POINTER(XModifierKeymap)]
        libX11.XkbLockModifiers.argtypes = [
            ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_uint, ctypes.c_uint]
        libX11.XkbLockModifiers.restype = ctypes.c_int
        libX11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        libX11.XFlush.argtypes = [ctypes.c_void_p]

        display = libX11.XOpenDisplay(None)
        if not display:
            logging.debug('_enable_numlock: cannot open X display')
            return

        try:
            mask = _get_numlock_mod_mask(libX11, display)
            if mask == 0:
                logging.debug('_enable_numlock: Num_Lock not in '
                              'modifier map; no-op')
                return

            libX11.XkbLockModifiers(
                display, _XKB_USE_CORE_KBD, mask, mask)
            libX11.XFlush(display)
            logging.debug('_enable_numlock: NumLock enabled '
                          '(mask=0x%02x)', mask)
        finally:
            libX11.XCloseDisplay(display)
    except Exception:
        logging.exception('Error enabling NumLock')


def setup():
    settings = Gio.Settings.new('org.sugarlabs.peripherals.keyboard')
    have_config = False

    try:
        display = GdkX11.x11_get_default_xdisplay()
        if display is None:
            logging.debug('setup_keyboard_cb: Could not get default display.')
        else:
            engine = Xkl.Engine.get_instance(display)

            configrec = Xkl.ConfigRec()
            configrec.get_from_server(engine)

            layouts = settings.get_strv('layouts')
            layouts_list = []
            variants_list = []
            if layouts:
                for layout in layouts:
                    layouts_list.append(layout.split('(')[0])
                    variants_list.append(layout.split('(')[1][:-1])

                if layouts_list and variants_list:
                    have_config = True
                    configrec.set_layouts(layouts_list)
                    configrec.set_variants(variants_list)

            model = settings.get_string('model')
            if model:
                have_config = True
                configrec.set_model(model)

            options = settings.get_strv('options')
            if options:
                have_config = True
                configrec.set_options(options)

            if have_config:
                configrec.activate(engine)
    except Exception:
        logging.exception('Error during keyboard configuration')

    _enable_numlock()
