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

#include "sugar-utils.h"

gint
sugar_get_screen_dpi(void)
{
    char *val = XGetDefault (GDK_DISPLAY(), "Xft", "dpi");
    if (val) {
        char *e;
        double d = strtod(val, &e);
        if (d > 0.0)
            return (int)(d+0.5);
    }

    return 96;
}
