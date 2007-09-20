#!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
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

from ctypes import *

# XText Property
class _XTextProperty(Structure):
    pass

_XTextProperty._fields_ = [("value", c_char_p),\
                            ("encoding", c_ulong),\
                            ("format", c_int),\
                            ("nitems", c_ulong)]

# XResType Structure
class _XResTypeStruct(Structure):
    pass

_XResTypeStruct._fields_ = [("resource_type", c_ulong),\
                      ("count", c_uint)]

_ATOMNAMES = ["PIXMAP",\
            "WINDOW",\
            "GC",\
            "FONT",\
            "GLYPHSET",\
            "PICTURE",\
            "COLORMAP ENTRY",\
            "PASSIVE GRAB",\
            "CURSOR",\
            "_NET_CLIENT_LIST",\
            "_NET_WM_PID",\
            "_NET_WM_NAME",\
            "UTF8_STRING",\
            "WM_NAME", # FIXME!
            "CARDINAL" # FIXME!
            ]

_ATOM_PIXMAP = 0
_ATOM_WINDOW = 1
_ATOM_GC = 2
_ATOM_FONT = 3
_ATOM_GLYPHSET = 4
_ATOM_PICTURE = 5
_ATOM_COLORMAP_ENTRY = 6
_ATOM_PASSIVE_GRAB = 7
_ATOM_CURSOR = 8
_ATOM_NET_CLIENT_LIST = 9
_ATOM_NET_WM_PID = 10
_ATOM_NET_WM_NAME = 11
_ATOM_UTF8_STRING = 12
_ATOM_WM_NAME = 13
_ATOM_CARDINAL = 14

# XText Property
class _XTextProperty(Structure):
    pass

_XTextProperty._fields_ = [("value", c_char_p),\
                            ("encoding", c_ulong),\
                            ("format", c_int),\
                            ("nitems", c_ulong)]

class XRes(object):
    _XRESLIB = "libXRes.so"
    _XMULIB = "libXmu.so.6"

    def __init__(self):
        self._lib = CDLL(self._XRESLIB)
        self._lib_xmu = CDLL(self._XMULIB)

    def _set_atoms(self, display):
        self.atoms = []
        for atom in _ATOMNAMES:
            atom_value = self._lib.XInternAtom(display, atom, True)
            self.atoms.append(atom_value)

    def open_display(self, display=None):
        display = self._lib.XOpenDisplay(display)
        self._set_atoms(display)
        return display

    # Return an array with XRestTypes:
    #
    # XResType.resource_type (Atom_type)
    # XResTyoe.count
    def get_resources(self, display, resource_base):
        n_types = c_long()
        types = pointer(_XResTypeStruct())
        self._lib.XResQueryClientResources(display, resource_base, \
                                                byref(n_types), byref(types))

        pytypes = []
        for t in types[:n_types.value]:
            pytypes.append(t)

        return pytypes

    def get_windows(self, display):
        self._windows = []
        root = self._lib.XDefaultRootWindow(display)
        self._lookat(display, root)
        return self._windows

    def _lookat(self, display, win_root):
        wp = self._get_window_properties (display, win_root)
        
        if wp:
            self._windows.append(wp)

        w = None
        dummy = self._Window()
        children = self._Window()
        nchildren = c_uint()

        r = self._lib.XQueryTree(display, win_root, byref(dummy), \
                                byref(dummy), byref(children), byref(nchildren))

        for client in children[:nchildren.value]:
            cli = self._lib_xmu.XmuClientWindow (display, client)
            if client is not None:
                wp = self._get_window_properties (display, cli)
                if wp:
                    self._windows.append(wp)

    def _get_window_properties(self, display, w):
        cliargv = c_char_p()
        cliargc = c_long()
        machtp = pointer(_XTextProperty())
        nametp = _XTextProperty()
        w_name = None

        if not self._lib.XGetWMClientMachine (display, w, byref(machtp)):
            machtp.value = None
            machtp.encoding = None

        if not self._lib.XGetCommand(display, w, byref(cliargv), byref(cliargc)):
            return

        if self._lib.XGetWMName(display, w, byref(nametp)):
            w_name = nametp.value

        bytes = c_ulong()
        self._lib.XResQueryClientPixmapBytes(display, w, byref(bytes))
        w_pixmaps = bytes.value
        
        type = self._Atom()
        format = c_int()
        n_items = c_ulong()
        bytes_after = c_int()
        w_pid = pointer(c_long())
        wname = c_char_p()

        self._lib.XGetWindowProperty(display, w,\
                                        self.atoms[_ATOM_NET_WM_PID],
                                        0, 2L,\
                                        False, self.atoms[_ATOM_CARDINAL],\
                                        byref(type), byref(format), \
                                        byref(n_items), byref(bytes_after), \
                                        byref(w_pid))
        

        # Calc aditional X resources by window
        res = self.get_resources(display, w)

        n_windows = 0
        n_gcs = 0
        n_pictures = 0
        n_glyphsets = 0
        n_fonts = 0
        n_colormaps = 0
        n_passive_grabs = 0
        n_cursors = 0
        n_other = 0

        for r in res:
            if r.resource_type == self.atoms[_ATOM_WINDOW]:
                n_windows += r.count
            elif r.resource_type == self.atoms[_ATOM_GC]:
                n_gcs += r.count
            elif r.resource_type == self.atoms[_ATOM_PICTURE]:
                n_pictures += r.count
            elif r.resource_type == self.atoms[_ATOM_GLYPHSET]:
                n_glyphsets += r.count
            elif r.resource_type == self.atoms[_ATOM_FONT]:
                n_fonts += r.count
            elif r.resource_type == self.atoms[_ATOM_COLORMAP_ENTRY]:
                n_colormaps += r.count
            elif r.resource_type == self.atoms[_ATOM_PASSIVE_GRAB]:
                n_passive_grabs += r.count
            elif r.resource_type == self.atoms[_ATOM_CURSOR]:
                n_cursors += r.count
            else:
                n_other += r.count

        other_bytes = n_windows * 24
        other_bytes += n_gcs * 24
        other_bytes += n_pictures * 24
        other_bytes += n_glyphsets * 24
        other_bytes += n_fonts * 1024
        other_bytes += n_colormaps * 24
        other_bytes += n_passive_grabs * 24
        other_bytes += n_cursors * 24
        other_bytes += n_other * 24

        window = Window(w, w_pid.contents.value, w_pixmaps, \
            n_windows, n_gcs, n_fonts, n_glyphsets, n_pictures,\
            n_colormaps, n_passive_grabs, n_cursors, n_other,\
            other_bytes, w_name)
        
        return window

    # Data types
    def _Window(self):
        return pointer(c_ulong())

    def _Atom(self, data=0):
        return pointer(c_ulong(data))

class Window(object):
    def __init__(self, resource_base, pid, pixmap_bytes=0,\
            n_windows=0, n_gcs=0, n_fonts=0, n_glyphsets=0, n_pictures=0,\
            n_colormaps=0, n_passive_grabs=0, n_cursors=0, n_other=0,\
            other_bytes=0, wm_name=None):

        self.resource_base = resource_base
        self.pid = pid
        self.pixmap_bytes = pixmap_bytes
        
        self.n_windows = n_windows
        self.n_gcs = n_gcs
        self.n_fonts = n_fonts
        self.n_glyphsets = n_glyphsets
        self.n_pictures = n_pictures
        self.n_colormaps = n_colormaps
        self.n_passive_grabs = n_passive_grabs
        self.n_cursors = n_cursors
        self.n_other = n_other

        self.other_bytes = other_bytes
        self.wm_name = wm_name
