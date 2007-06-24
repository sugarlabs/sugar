/*
 * Copyright (C) 2006-2007 Red Hat, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#include <gdk/gdkproperty.h>
#include <X11/Xatom.h>
#include <glib/gstrfuncs.h>
#include <string.h>

#include "sugar-x11-util.h"

void
sugar_x11_util_set_string_property(GdkWindow  *window,
                                   const char *property,
                                   const char *value)
{
    Atom prop_atom;
    Atom string_atom;
    GdkDisplay *display;
    char *prop_text;

    display = gdk_drawable_get_display(window);
    prop_atom = gdk_x11_get_xatom_by_name_for_display(display, property);
    string_atom = gdk_x11_get_xatom_by_name_for_display(display, "STRING");
    prop_text = gdk_utf8_to_string_target(value);

    XChangeProperty(GDK_DISPLAY_XDISPLAY(display),
                    GDK_WINDOW_XID(window),
                    prop_atom,
                    string_atom, 8,
                    PropModeReplace, prop_text,
                    strlen(prop_text));

    g_free(prop_text);
}

char *
sugar_x11_util_get_string_property(GdkWindow  *window,
                                   const char *property)
{
    Atom type;    
    Atom prop_atom;
    Atom string_atom;
    int format;
    int result;
    unsigned long bytes_after, n_items;
    unsigned char *str = NULL;
    char *value = NULL;
    GdkDisplay *display;

    display = gdk_drawable_get_display(window);
    prop_atom = gdk_x11_get_xatom_by_name_for_display(display, property);
    string_atom = gdk_x11_get_xatom_by_name_for_display(display, "STRING");

    result = XGetWindowProperty(GDK_DISPLAY_XDISPLAY(display),
                                GDK_WINDOW_XID(window),
                                prop_atom,
                                0, 1024L,
                                False, string_atom,
                                &type, &format, &n_items,
                                &bytes_after, (unsigned char **)&str);

    if (result == Success && str != NULL && type == string_atom &&
        format == 8 && n_items > 0) {
        value = g_strdup(str);
    }

    if (str) {
        XFree(str);
    }

    return value;
}
