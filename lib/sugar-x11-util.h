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

#ifndef __SUGAR_X11_UTIL_H__
#define __SUGAR_X11_UTIL_H__

#include <gdk/gdkx.h>

G_BEGIN_DECLS

void    sugar_x11_util_set_string_property(GdkWindow  *window,
                                           const char *property,
                                           const char *value);

char   *sugar_x11_util_get_string_property(GdkWindow  *window,
                                           const char *property);

G_END_DECLS

#endif /* __SUGAR_ADDRESS_ENTRY_H__ */
