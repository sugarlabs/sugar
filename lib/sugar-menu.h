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

#ifndef __SUGAR_MENU_H__
#define __SUGAR_MENU_H__

#include <gtk/gtkmenu.h>

G_BEGIN_DECLS

typedef struct _SugarMenu SugarMenu;
typedef struct _SugarMenuClass SugarMenuClass;

#define SUGAR_TYPE_MENU			     (sugar_menu_get_type())
#define SUGAR_MENU(object)	         (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_MENU, SugarMenu))
#define SUGAR_MENU_CLASS(klass)	     (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_MENU, SugarMenuClass))
#define SUGAR_IS_MENU(object)	     (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_MENU))
#define SUGAR_IS_MENU_CLASS(klass)   (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_MENU))
#define SUGAR_MENU_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_MENU, SugarMenuClass))

struct _SugarMenu {
	GtkMenu base_instance;

    int min_width;
};

struct _SugarMenuClass {
	GtkMenuClass base_class;
};

GType	 sugar_menu_get_type      (void);
void     sugar_menu_popup         (SugarMenu *menu,
                                   int        x,
                                   int        y);
void     sugar_menu_set_min_width (SugarMenu *menu,
                                   int        min_width);
void     sugar_menu_popdown       (SugarMenu *menu);

G_END_DECLS

#endif /* __SUGAR_MENU_H__ */
