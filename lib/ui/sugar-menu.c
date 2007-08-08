/*
 * Copyright (C) 2006-2007, Red Hat, Inc.
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

#include <gtk/gtkwindow.h>

#include "sugar-menu.h"

static void sugar_menu_class_init (SugarMenuClass *menu_class);
static void sugar_menu_init       (SugarMenu *menu);


G_DEFINE_TYPE(SugarMenu, sugar_menu, GTK_TYPE_MENU)

void
sugar_menu_set_active(SugarMenu *menu, gboolean active)
{
    GTK_MENU_SHELL(menu)->active = active;
}

void
sugar_menu_embed(SugarMenu *menu, GtkContainer *parent)
{
    GTK_MENU(menu)->toplevel = gtk_widget_get_toplevel(GTK_WIDGET(parent));
    gtk_widget_reparent(GTK_WIDGET(menu), GTK_WIDGET(parent));
}

static void
sugar_menu_class_init(SugarMenuClass *menu_class)
{
}

static void
sugar_menu_init(SugarMenu *menu)
{
}
