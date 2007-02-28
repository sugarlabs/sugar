/*
 * Copyright (C) 2006, Red Hat, Inc.
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

#include <stdlib.h>
#include <gdk/gdkx.h>
#include <gdk/gdkscreen.h>
#include <gtk/gtksettings.h>

#include "sugar-utils.h"

/* Ported from mozilla nsDeviceContextGTK.cpp */

static gint
get_gtk_settings_dpi(void)
{
    GtkSettings *settings = gtk_settings_get_default();
    GParamSpec *spec;
    gint dpi = 0;

    spec = g_object_class_find_property(
        G_OBJECT_GET_CLASS(G_OBJECT(settings)), "gtk-xft-dpi");

    if (spec) {
        g_object_get(G_OBJECT(settings),
                     "gtk-xft-dpi", &dpi,
                     NULL);
    }

    return (int)(dpi / 1024.0 + 0.5);
}

static gint
get_xft_dpi(void)
{
    char *val = XGetDefault(GDK_DISPLAY(), "Xft", "dpi");
    if (val) {
        char *e;
        double d = strtod(val, &e);

        if (e != val)
            return (int)(d + 0.5);
    }

    return 0;
}

static int
get_dpi_from_physical_resolution(void)
{
    float screen_width_in;

    screen_width_in = (float)(gdk_screen_width_mm()) / 25.4f;

    return (int)((float)(gdk_screen_width()) / screen_width_in + 0.5);
}

gint
sugar_get_screen_dpi(void)
{
    int dpi;

    dpi = get_gtk_settings_dpi();

    if (dpi == 0) {
        dpi = get_xft_dpi();
    }

    if (dpi == 0) {
        dpi = get_dpi_from_physical_resolution();
    }

    return dpi;
}
