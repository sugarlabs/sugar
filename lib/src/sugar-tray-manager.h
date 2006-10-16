/* -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*- */
/* na-tray-manager.h
 * Copyright (C) 2002 Anders Carlsson <andersca@gnu.org>
 * Copyright (C) 2003-2006 Vincent Untz
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
 *
 * Used to be: eggtraymanager.h
 */

#ifndef __SUGAR_TRAY_MANAGER_H__
#define __SUGAR_TRAY_MANAGER_H__

#include <gtk/gtkwidget.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif

G_BEGIN_DECLS

#define SUGAR_TYPE_TRAY_MANAGER			(sugar_tray_manager_get_type ())
#define SUGAR_TRAY_MANAGER(obj)			(G_TYPE_CHECK_INSTANCE_CAST ((obj), SUGAR_TYPE_TRAY_MANAGER, SugarTrayManager))
#define SUGAR_TRAY_MANAGER_CLASS(klass)		(G_TYPE_CHECK_CLASS_CAST ((klass), SUGAR_TYPE_TRAY_MANAGER, SugarTrayManagerClass))
#define SUGAR_IS_TRAY_MANAGER(obj)		(G_TYPE_CHECK_INSTANCE_TYPE ((obj), SUGAR_TYPE_TRAY_MANAGER))
#define SUGAR_IS_TRAY_MANAGER_CLASS(klass)	(G_TYPE_CHECK_CLASS_TYPE ((klass), SUGAR_TYPE_TRAY_MANAGER))
#define SUGAR_TRAY_MANAGER_GET_CLASS(obj)	(G_TYPE_INSTANCE_GET_CLASS ((obj), SUGAR_TYPE_TRAY_MANAGER, SugarTrayManagerClass))
	
typedef struct _SugarTrayManager	    SugarTrayManager;
typedef struct _SugarTrayManagerClass  SugarTrayManagerClass;
typedef struct _SugarTrayManagerChild  SugarTrayManagerChild;

struct _SugarTrayManager
{
  GObject parent_instance;

#ifdef GDK_WINDOWING_X11
  GdkAtom selection_atom;
  Atom    opcode_atom;
#endif
  
  GtkWidget *invisible;
  GdkScreen *screen;
  GtkOrientation orientation;

  GList *messages;
  GHashTable *socket_table;
};

struct _SugarTrayManagerClass
{
  GObjectClass parent_class;

  void (* tray_icon_added)   (SugarTrayManager      *manager,
			      SugarTrayManagerChild *child);
  void (* tray_icon_removed) (SugarTrayManager      *manager,
			      SugarTrayManagerChild *child);

  void (* message_sent)      (SugarTrayManager      *manager,
			      SugarTrayManagerChild *child,
			      const gchar        *message,
			      glong               id,
			      glong               timeout);
  
  void (* message_cancelled) (SugarTrayManager      *manager,
			      SugarTrayManagerChild *child,
			      glong               id);

  void (* lost_selection)    (SugarTrayManager      *manager);
};

GType           sugar_tray_manager_get_type        (void);

gboolean        sugar_tray_manager_check_running   (GdkScreen          *screen);
SugarTrayManager  *sugar_tray_manager_new             (void);
gboolean        sugar_tray_manager_manage_screen   (SugarTrayManager      *manager,
						 GdkScreen          *screen);
char           *sugar_tray_manager_get_child_title (SugarTrayManager      *manager,
						 SugarTrayManagerChild *child);
void            sugar_tray_manager_set_orientation (SugarTrayManager      *manager,
						 GtkOrientation      orientation);
GtkOrientation  sugar_tray_manager_get_orientation (SugarTrayManager      *manager);

G_END_DECLS

#endif /* __SUGAR_TRAY_MANAGER_H__ */
