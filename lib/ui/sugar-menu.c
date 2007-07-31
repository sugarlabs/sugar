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
sugar_menu_popup(SugarMenu *menu,
                 int         x,
                 int         y)
{
    GtkWidget *window;

    window = GTK_MENU(menu)->toplevel;
    g_return_if_fail(window != NULL);

    GTK_MENU_SHELL(menu)->active = TRUE;

    gtk_widget_show(GTK_WIDGET(menu));

    gtk_window_move(GTK_WINDOW(window), x, y);
    gtk_widget_show(window);
}

void
sugar_menu_popdown(SugarMenu *menu)
{
    GtkWidget *window;

    window = GTK_MENU(menu)->toplevel;
    g_return_if_fail(window != NULL);

    GTK_MENU_SHELL(menu)->active = FALSE;

    gtk_widget_hide(GTK_WIDGET(menu));
    gtk_widget_hide(window);
}

void
sugar_menu_set_min_width (SugarMenu *menu,
                          int        min_width)
{
    menu->min_width = min_width;
}

static void
sugar_menu_size_request (GtkWidget      *widget,
                         GtkRequisition *requisition)
{
    SugarMenu *menu = SUGAR_MENU(widget);

    (* GTK_WIDGET_CLASS (sugar_menu_parent_class)->size_request) (widget, requisition);

    requisition->width = MAX(requisition->width, menu->min_width);
}

static void
sugar_menu_class_init(SugarMenuClass *menu_class)
{
    GtkWidgetClass *widget_class = GTK_WIDGET_CLASS(menu_class);

    widget_class->size_request = sugar_menu_size_request;    
}

static void
sugar_menu_init(SugarMenu *menu)
{
}
